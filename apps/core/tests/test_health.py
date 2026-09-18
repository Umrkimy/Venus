from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_chat():
    response = client.post("/chat", json={"message": "hello"})

    assert response.status_code == 200
    assert response.json() == {
        "reply": "Fake Venus: hello",
        "provider": "fake",
    }

def test_chat_rejects_blank_message():
    response = client.post("/chat", json={"message": "   "})

    assert response.status_code == 422