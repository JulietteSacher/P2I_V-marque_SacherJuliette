def test_health(client):
    # Essaie /health (si tu l'as), sinon fallback sur /
    r = client.get("/health")
    if r.status_code == 404:
        r = client.get("/")
    assert r.status_code == 200