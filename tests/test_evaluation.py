import pytest

from mathcraft.evaluation import EvaluationKind, EvaluationSample, evaluate_samples


def test_formula_evaluation_ignores_whitespace_only() -> None:
    report = evaluate_samples(
        [
            EvaluationSample(
                id="formula-1",
                kind=EvaluationKind.FORMULA,
                reference=r"x^2 + 1",
                prediction=r"x^2+1",
            )
        ]
    )

    assert report.results[0].exact_match
    assert report.summaries[0].exact_match_rate == 1


def test_text_evaluation_reports_character_error_rate() -> None:
    report = evaluate_samples(
        [
            EvaluationSample(
                id="text-1",
                kind=EvaluationKind.TEXT,
                reference="矩阵",
                prediction="矩陈",
            )
        ]
    )

    assert report.results[0].edit_distance == 1
    assert report.results[0].error_rate == pytest.approx(0.5)
