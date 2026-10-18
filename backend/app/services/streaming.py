"""HTTP Range request handling for audio streaming.

Pure, dependency-free range parsing so it can be unit-tested without
FastAPI, plus a chunked file iterator for :class:`~fastapi.responses.StreamingResponse`.
"""

from __future__ import annotations

from pathlib import Path

CHUNK_SIZE = 1024 * 1024  # 1 MiB


class RangeError(ValueError):
    """Raised when a ``Range`` header is unsatisfiable (HTTP 416)."""


def parse_range(range_header: str | None, file_size: int) -> tuple[int, int | None]:
    """Parse a ``Range: bytes=start-end`` header.

    Returns ``(start, end)`` with ``end`` inclusive, or ``None`` for an
    open-ended range (``bytes=start-``).

    Raises ``RangeError`` when the range cannot be satisfied.
    """
    if range_header is None:
        return 0, None

    header = range_header.strip()
    if not header.lower().startswith("bytes="):
        raise RangeError("Only byte ranges are supported")

    spec = header[len("bytes=") :].strip()
    if not spec:
        raise RangeError("Empty range specification")

    parts = spec.split("-")
    if len(parts) != 2:
        raise RangeError("Only a single byte range is supported")

    start_str, end_str = parts

    if start_str == "":
        # Suffix-range (bytes=-N) is not supported.
        raise RangeError("Suffix ranges are not supported")

    try:
        start = int(start_str)
    except ValueError:
        raise RangeError("Invalid range start")

    if start < 0:
        raise RangeError("Range start must be non-negative")

    if end_str == "":
        # Open-ended: bytes=start-
        if start >= file_size:
            raise RangeError("Range start beyond file size")
        return start, None

    try:
        end = int(end_str)
    except ValueError:
        raise RangeError("Invalid range end")

    if end < start:
        raise RangeError("Range end must be greater than or equal to start")

    if start >= file_size:
        raise RangeError("Range start beyond file size")

    return start, min(end, file_size - 1)


def iter_file(
    path: Path | str,
    start: int,
    end: int | None,
    chunk_size: int = CHUNK_SIZE,
):
    """Yield ``chunk_size`` byte chunks of ``path`` from ``start`` to ``end`` (inclusive)."""
    path = Path(path)
    with path.open("rb") as f:
        f.seek(start)
        remaining = None if end is None else (end - start + 1)
        while True:
            if remaining is not None:
                to_read = min(chunk_size, remaining)
                if to_read <= 0:
                    break
            else:
                to_read = chunk_size
            chunk = f.read(to_read)
            if not chunk:
                break
            yield chunk
            if remaining is not None:
                remaining -= len(chunk)
                if remaining <= 0:
                    break
