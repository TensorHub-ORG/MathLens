from collections import defaultdict
from collections.abc import Iterable

from mathlens.evaluation.metrics import edit_distance, normalize_formula
from mathlens.evaluation.models import (
    EvaluationKind,
    EvaluationReport,
    EvaluationResult,
    EvaluationSample,
    EvaluationSummary,
)


def _normalize(sample: EvaluationSample) -> tuple[str, str]:
    reference = sample.reference.replace("\r\n", "\n")
    prediction = sample.prediction.replace("\r\n", "\n")
    if sample.kind is EvaluationKind.FORMULA:
        reference = normalize_formula(reference)
        prediction = normalize_formula(prediction)
    return reference, prediction


def evaluate_samples(samples: Iterable[EvaluationSample]) -> EvaluationReport:
    results = []
    by_kind: dict[EvaluationKind, list[EvaluationResult]] = defaultdict(list)
    for sample in samples:
        reference, prediction = _normalize(sample)
        distance = edit_distance(reference, prediction)
        result = EvaluationResult(
            sample_id=sample.id,
            kind=sample.kind,
            exact_match=reference == prediction,
            edit_distance=distance,
            error_rate=distance / max(len(reference), 1),
        )
        results.append(result)
        by_kind[sample.kind].append(result)

    summaries = []
    for kind in EvaluationKind:
        kind_results = by_kind.get(kind, [])
        if not kind_results:
            continue
        summaries.append(
            EvaluationSummary(
                kind=kind,
                samples=len(kind_results),
                exact_match_rate=sum(result.exact_match for result in kind_results)
                / len(kind_results),
                mean_error_rate=sum(result.error_rate for result in kind_results)
                / len(kind_results),
            )
        )

    return EvaluationReport(results=tuple(results), summaries=tuple(summaries))
