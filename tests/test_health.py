from src.api.health import ping

def test_ping():
    assert ping() == {"status": "ok"}
