from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryTurn:
    question: str
    sql: str


def trim_memory(turns: list[MemoryTurn], max_turns: int) -> list[MemoryTurn]:
    if max_turns <= 0:
        return []
    return turns[-max_turns:]
