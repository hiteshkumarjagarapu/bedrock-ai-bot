SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def _split(text: str, size: int, seps: list[str]) -> list[str]:
    """Recursively split text on the coarsest separator that keeps pieces <= size."""
    if len(text) <= size:
        return [text]
    sep, rest = seps[0], seps[1:]
    pieces = list(text) if sep == "" else text.split(sep)
    out: list[str] = []
    current = ""
    for i, piece in enumerate(pieces):
        piece_s = piece + (sep if sep and i < len(pieces) - 1 else "")
        if len(piece_s) > size and rest:
            if current:
                out.append(current)
                current = ""
            out.extend(_split(piece_s, size, rest))
        elif len(current) + len(piece_s) > size:
            if current:
                out.append(current)
            current = piece_s
        else:
            current += piece_s
    if current:
        out.append(current)
    return out


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> list[str]:
    """Recursive character splitter: chunks of at most chunk_size chars, overlap chars shared."""
    text = text.strip()
    if not text:
        return []
    base = _split(text, chunk_size - overlap - 1, SEPARATORS)
    chunks: list[str] = []
    prev_tail = ""
    for piece in base:
        piece = piece.strip()
        if not piece:
            continue
        chunks.append((prev_tail + " " + piece).strip() if prev_tail else piece)
        prev_tail = piece[-overlap:] if overlap else ""
    return chunks


def chunk_pages(pages: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Chunk each page separately, keeping page numbers. Returns (page_number, chunk)."""
    result: list[tuple[int, str]] = []
    for page, text in pages:
        result.extend((page, c) for c in chunk_text(text))
    return result
