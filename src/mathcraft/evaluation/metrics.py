from __future__ import annotations


def edit_distance(reference: str, prediction: str) -> int:
    previous = list(range(len(prediction) + 1))
    for row_index, reference_character in enumerate(reference, start=1):
        current = [row_index]
        for column_index, prediction_character in enumerate(prediction, start=1):
            substitution_cost = int(reference_character != prediction_character)
            current.append(
                min(
                    current[-1] + 1,
                    previous[column_index] + 1,
                    previous[column_index - 1] + substitution_cost,
                )
            )
        previous = current
    return previous[-1]


def text_error_rate(reference: str, prediction: str) -> float:
    return edit_distance(reference, prediction) / max(len(reference), 1)


def normalize_formula(value: str) -> str:
    return "".join(value.split())
