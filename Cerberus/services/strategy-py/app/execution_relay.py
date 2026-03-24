from __future__ import annotations


def filter_new_executions(
    items: list[dict[str, object]], last_execution_id: int
) -> list[tuple[int, dict[str, object]]]:
    buffered: list[tuple[int, dict[str, object]]] = []
    for item in items:
        execution_id = to_execution_id(item.get("execution_id"))
        if execution_id <= last_execution_id:
            continue
        buffered.append((execution_id, item))
    buffered.sort(key=lambda row: row[0])
    return buffered


def to_execution_id(raw: object) -> int:
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        try:
            return int(raw)
        except ValueError:
            return 0
    return 0
