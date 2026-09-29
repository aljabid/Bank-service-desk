from __future__ import annotations


def table(headers: list[str], rows: list[list], align: str | None = None) -> str:
    cells = [[str(c) for c in row] for row in rows]
    widths = [max(len(h), *(len(r[i]) for r in cells)) if cells else len(h) for i, h in enumerate(headers)]
    align = align or "l" * len(headers)

    def fmt(row: list[str]) -> str:
        return " | ".join(c.rjust(w) if a == "r" else c.ljust(w) for c, w, a in zip(row, widths, align))

    line = "-+-".join("-" * w for w in widths)
    return "\n".join([fmt(headers), line, *(fmt(r) for r in cells)])


def title(text: str) -> str:
    return f"\n{'=' * 78}\n {text}\n{'=' * 78}"


def minutes(hours: float) -> str:
    return f"{hours * 60:.0f} min"


def hours(value: float) -> str:
    return f"{value:.2f} h"
