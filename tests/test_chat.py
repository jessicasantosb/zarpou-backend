import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_chat_hotel_fallback_actions():
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Quais os melhores hotéis e resorts disponíveis?",
            "sessionId": "test-session-chat",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert "suggestedActions" in data
    actions = data["suggestedActions"]
    assert len(actions) > 0

    urls = [a["url"] for a in actions]
    # Certificar que nenhuma URL aponta para rotas inexistentes /hoteis ou /voos
    for u in urls:
        assert not u.startswith("/hoteis"), f"URL inválida encontrada: {u}"
        assert not u.startswith("/voos"), f"URL inválida encontrada: {u}"
    # Deve conter /hospedagens
    assert any("/hospedagens" in u for u in urls)


def test_chat_flight_fallback_actions():
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Gostaria de ver voos e passagens para Miami",
            "sessionId": "test-session-chat",
        },
    )
    assert response.status_code == 200
    data = response.json()
    urls = [a["url"] for a in data.get("suggestedActions", [])]
    for u in urls:
        assert not u.startswith("/voos"), f"URL inválida de voo: {u}"
    assert any("/passagens" in u for u in urls)


def test_chat_package_destinos_actions():
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Tem promoções de pacotes?",
            "sessionId": "test-session-chat",
        },
    )
    assert response.status_code == 200
    data = response.json()
    urls = [a["url"] for a in data.get("suggestedActions", [])]
    # /destinos sem âncora era rota 404, deve ser /#destinos ou /pacotes
    assert "/destinos" not in urls
    assert any("/#destinos" in u or "/pacotes" in u for u in urls)


def test_chat_history_endpoint():
    response = client.get("/api/v1/chat/history?sessionId=test-session-chat")
    assert response.status_code == 200
    logs = response.json()
    assert isinstance(logs, list)
    assert len(logs) >= 2
