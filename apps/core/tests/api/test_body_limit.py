from fastapi import FastAPI, Request, status
from fastapi.testclient import TestClient

from api.body_limit import read_body

LIMIT = 10

app = FastAPI()


@app.post("/upload")
async def upload(request: Request):
    data = await read_body(request, LIMIT, "Too big")
    return {"size": len(data)}


client = TestClient(app)


def test_read_body_returns_a_body_at_the_limit():
    response = client.post("/upload", content=b"x" * LIMIT)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"size": LIMIT}


def test_read_body_refuses_a_big_declared_length():
    response = client.post("/upload", content=b"x" * (LIMIT + 1))

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
    assert response.json() == {"detail": "Too big"}


def test_read_body_stops_a_stream_without_a_length():
    # A chunked upload has no Content-Length, so the size is counted while reading.
    def chunks():
        for _ in range(5):
            yield b"xxx"

    response = client.post("/upload", content=chunks())

    assert response.status_code == status.HTTP_413_CONTENT_TOO_LARGE
