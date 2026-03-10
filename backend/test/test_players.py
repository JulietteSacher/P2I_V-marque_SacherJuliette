def test_create_player_and_list(client):
    team = client.post("/teams", json={"name": "Team A"}).json()

    p = client.post(
        f"/teams/{team['id']}/players",
        json={
            "first_name": "Julie",
            "last_name": "Dupont",
            "jersey_number": 7,
            "role": "PASSEUR",
            "license_number": "LIC-7",
        },
    ).json()

    assert p["team_id"] == team["id"]
    assert p["jersey_number"] == 7

    players = client.get(f"/teams/{team['id']}/players").json()
    assert any(x["id"] == p["id"] for x in players)


def test_get_player(client):
    team = client.post("/teams", json={"name": "Team A"}).json()
    p = client.post(
        f"/teams/{team['id']}/players",
        json={
            "first_name": "Julie",
            "last_name": "Dupont",
            "jersey_number": 7,
            "role": "PASSEUR",
            "license_number": "LIC-7",
        },
    ).json()

    got = client.get(f"/teams/{team['id']}/players/{p['id']}").json()
    assert got["id"] == p["id"]
    assert got["jersey_number"] == 7


def test_duplicate_jersey_in_team_rejected(client):
    team = client.post("/teams", json={"name": "Team A"}).json()

    client.post(
        f"/teams/{team['id']}/players",
        json={
            "first_name": "A",
            "last_name": "A1",
            "jersey_number": 7,
            "role": "PASSEUR",
            "license_number": "LIC-7A",
        },
    )

    r = client.post(
        f"/teams/{team['id']}/players",
        json={
            "first_name": "B",
            "last_name": "B1",
            "jersey_number": 7,
            "role": "PASSEUR",
            "license_number": "LIC-7B",
        },
    )

    assert r.status_code == 400