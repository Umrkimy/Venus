from fastapi import HTTPException, Request, status


async def read_body(request: Request, max_bytes: int, too_large: str) -> bytes:
    """The raw body, refused as soon as it passes max_bytes.

    request.body() would hold the whole upload in memory before any size
    check, so a huge file could fill RAM first. A Content-Length over the
    limit is refused before reading anything.
    """
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > max_bytes:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=too_large)

    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > max_bytes:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=too_large)
        chunks.append(chunk)
    return b"".join(chunks)
