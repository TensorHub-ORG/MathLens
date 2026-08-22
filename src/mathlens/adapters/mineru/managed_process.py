from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
from collections.abc import Mapping
from typing import Any, TextIO

_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_WINDOWS_WRAPPER = """
import json
import subprocess
import sys

sys.stdin.buffer.read(1)
raise SystemExit(subprocess.call(json.loads(sys.argv[1])))
"""


class _JobObjectBasicLimitInformation(ctypes.Structure):
    _fields_ = [
        ("per_process_user_time_limit", ctypes.c_longlong),
        ("per_job_user_time_limit", ctypes.c_longlong),
        ("limit_flags", ctypes.c_uint32),
        ("minimum_working_set_size", ctypes.c_size_t),
        ("maximum_working_set_size", ctypes.c_size_t),
        ("active_process_limit", ctypes.c_uint32),
        ("affinity", ctypes.c_size_t),
        ("priority_class", ctypes.c_uint32),
        ("scheduling_class", ctypes.c_uint32),
    ]


class _IoCounters(ctypes.Structure):
    _fields_ = [
        ("read_operation_count", ctypes.c_uint64),
        ("write_operation_count", ctypes.c_uint64),
        ("other_operation_count", ctypes.c_uint64),
        ("read_transfer_count", ctypes.c_uint64),
        ("write_transfer_count", ctypes.c_uint64),
        ("other_transfer_count", ctypes.c_uint64),
    ]


class _JobObjectExtendedLimitInformation(ctypes.Structure):
    _fields_ = [
        ("basic_limit_information", _JobObjectBasicLimitInformation),
        ("io_info", _IoCounters),
        ("process_memory_limit", ctypes.c_size_t),
        ("job_memory_limit", ctypes.c_size_t),
        ("peak_process_memory_used", ctypes.c_size_t),
        ("peak_job_memory_used", ctypes.c_size_t),
    ]


def _windows_job() -> tuple[Any, int]:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    information = _JobObjectExtendedLimitInformation()
    information.basic_limit_information.limit_flags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    configured = kernel32.SetInformationJobObject(
        job,
        _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
        ctypes.byref(information),
        ctypes.sizeof(information),
    )
    if not configured:
        error = ctypes.WinError(ctypes.get_last_error())
        kernel32.CloseHandle(job)
        raise error
    return kernel32, job


def run_managed_process(
    command: list[str],
    *,
    stdout: TextIO,
    timeout: int,
    environment: Mapping[str, str],
) -> subprocess.CompletedProcess[str]:
    """Run a CLI and reclaim its descendant processes when the command exits."""
    if os.name != "nt":
        return subprocess.run(
            command,
            check=False,
            stdout=stdout,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            env=environment,
        )

    kernel32, job = _windows_job()
    process: subprocess.Popen[bytes] | None = None
    try:
        process = subprocess.Popen(
            [sys.executable, "-c", _WINDOWS_WRAPPER, json.dumps(command)],
            stdin=subprocess.PIPE,
            stdout=stdout,
            stderr=subprocess.STDOUT,
            env=environment,
        )
        process_handle = getattr(process, "_handle", None)
        if process_handle is None or not kernel32.AssignProcessToJobObject(job, process_handle):
            process.terminate()
            process.wait(timeout=30)
            raise ctypes.WinError(ctypes.get_last_error())
        if process.stdin is None:
            raise RuntimeError("managed process handshake pipe was not created")
        process.stdin.write(b"1")
        process.stdin.close()
        try:
            return_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            kernel32.CloseHandle(job)
            job = 0
            process.wait(timeout=30)
            raise
        return subprocess.CompletedProcess(command, return_code)
    finally:
        if job:
            kernel32.CloseHandle(job)
