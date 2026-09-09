from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def extract_notebook_code(
    path: Path, max_bytes: int = 30_000
) -> tuple[str, str, int, int]:
    """
    Safely parse a Jupyter Notebook (.ipynb) and extract pure executable code cells.

    Ignores output blobs, base64 images, execution counts, and irrelevant metadata.
    Preserves cell ordering and formats cell boundaries so reviewers and static analyzers
    can reference exact cell numbers.

    Returns:
        (extracted_code, detected_language, code_cell_count, total_cell_count)
    """
    try:
        raw_text = path.read_text(encoding="utf-8", errors="replace")
        data: dict[str, Any] = json.loads(raw_text)
    except Exception as exc:
        # Fallback if notebook JSON is corrupt
        return f"# Error reading notebook JSON: {exc}", "python", 0, 0

    metadata = data.get("metadata", {})
    language = (
        metadata.get("language_info", {}).get("name")
        or metadata.get("kernelspec", {}).get("language")
        or "python"
    ).lower()

    cells = data.get("cells", [])
    if not isinstance(cells, list):
        return "# Notebook contains no valid cells array.", language, 0, 0

    comment_prefix = "#" if language in {"python", "r", "julia", "ruby", "shell", "bash"} else "//"

    total_cell_count = len(cells)
    code_cell_count = 0
    formatted_chunks: list[str] = []
    current_bytes = 0

    for idx, cell in enumerate(cells, start=1):
        cell_type = cell.get("cell_type", "")
        source_raw = cell.get("source", "")
        if isinstance(source_raw, list):
            source_text = "".join(source_raw)
        else:
            source_text = str(source_raw)

        source_clean = source_text.strip()
        if not source_clean:
            continue

        if cell_type == "code":
            code_cell_count += 1
            cell_header = (
                f"\n{comment_prefix} ==========================================\n"
                f"{comment_prefix} [Cell {code_cell_count}: Code]\n"
                f"{comment_prefix} ==========================================\n"
            )
            chunk = cell_header + source_clean + "\n"

            chunk_bytes = len(chunk.encode("utf-8"))
            if current_bytes + chunk_bytes > max_bytes and formatted_chunks:
                # Add a truncation note and stop adding more cells
                formatted_chunks.append(
                    f"\n{comment_prefix} ... [Remaining {total_cell_count - idx + 1} cells truncated due to size limit] ...\n"
                )
                break

            formatted_chunks.append(chunk)
            current_bytes += chunk_bytes

        elif cell_type == "markdown":
            # Include concise markdown cells as commented context so models know intent
            # but preserve pure language syntax
            first_line = source_clean.splitlines()[0] if source_clean else ""
            if len(first_line) > 100:
                first_line = first_line[:97] + "..."
            chunk = f"\n{comment_prefix} [Notebook Context]: {first_line}\n"
            chunk_bytes = len(chunk.encode("utf-8"))
            if current_bytes + chunk_bytes <= max_bytes:
                formatted_chunks.append(chunk)
                current_bytes += chunk_bytes

    extracted = "".join(formatted_chunks).strip()
    if not extracted:
        extracted = f"{comment_prefix} Empty Jupyter Notebook (no executable code cells found)"

    return extracted, language, code_cell_count, total_cell_count


def map_line_to_cell(line_number: int, extracted_code: str) -> tuple[int | None, int]:
    """
    Given a 1-based line number in extracted notebook code, determine which
    code cell it belongs to and the line offset within that cell.

    Returns:
        (cell_number, line_within_cell)
    """
    lines = extracted_code.splitlines()
    current_cell: int | None = None
    cell_start_line = 1

    for idx, line in enumerate(lines, start=1):
        clean = line.strip()
        if "[Cell " in clean and ": Code]" in clean:
            try:
                # Parse e.g. "# [Cell 3: Code]"
                part = clean.split("[Cell ")[1].split(":")[0].strip()
                current_cell = int(part)
                cell_start_line = idx + 1
            except Exception:
                pass
        if idx == line_number:
            line_offset = max(1, line_number - cell_start_line + 1)
            return current_cell, line_offset

    return current_cell, 1

