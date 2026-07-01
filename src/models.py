from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ScriptRow:
    sheet_row: int
    대본: str = ""
    장면: str = ""
    사이즈: str = ""
    자막: str = ""
    코멘트: str = ""

    def to_values(self) -> list[str]:
        return [self.대본, self.장면, self.사이즈, self.자막, self.코멘트]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ScriptPart:
    name: str
    start_row: int
    end_row: int
    rows: list[ScriptRow] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "start_row": self.start_row,
            "end_row": self.end_row,
            "row_count": len(self.rows),
            "rows": [row.to_dict() for row in self.rows],
        }
