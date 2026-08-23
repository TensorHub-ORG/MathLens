from __future__ import annotations

import ctypes
import os
import sys
import tempfile
from pathlib import Path

import pytest

from mathcraft.adapters.mineru.managed_process import run_managed_process


def _process_is_active(process_id: int) -> bool:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.OpenProcess(0x1000, False, process_id)
    if not handle:
        return False
    try:
        exit_code = ctypes.c_uint32()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            raise ctypes.WinError(ctypes.get_last_error())
        return exit_code.value == 259
    finally:
        kernel32.CloseHandle(handle)


@pytest.mark.skipif(os.name != "nt", reason="Windows Job Object contract")
def test_managed_process_reclaims_descendants(tmp_path: Path) -> None:
    process_id_path = tmp_path / "child.pid"
    child_program = "import time; time.sleep(60)"
    parent_program = (
        "import pathlib,subprocess,sys; "
        f"child=subprocess.Popen([sys.executable,'-c',{child_program!r}]); "
        f"pathlib.Path({str(process_id_path)!r}).write_text(str(child.pid))"
    )

    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as output:
        completed = run_managed_process(
            [sys.executable, "-c", parent_program],
            stdout=output,
            timeout=30,
            environment=os.environ,
        )

    assert completed.returncode == 0
    child_process_id = int(process_id_path.read_text(encoding="utf-8"))
    assert not _process_is_active(child_process_id)
