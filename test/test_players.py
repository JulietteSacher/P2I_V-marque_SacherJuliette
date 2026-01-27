def test_create_player_in_team(client):
    team = client.post("/teams", json={"name": "Team A"}).json()
    team_id = team["id"]

    r = client.post(
        f"/teams/{team_id}/players",
        json={
            "first_name": "Julie",
            "last_name": "Martin",
            "jersey_number": 7,
            "role": "PASSEUR",
            "license_number": "FFVB123",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["team_id"] == team_id
    assert data["jersey_number"] == 7
    assert data["role"] == "PASSEUR"


def test_list_players_in_team(client):
    team = client.post("/teams", json={"name": "Team A"}).json()
    team_id = team["id"]

    client.post(
        f"/teams/{team_id}/players",
        json={"first_name": "A", "last_name": "A", "jersey_number": 1, "role": "R4", "license_number": None},
    )
    client.post(
        f"/teams/{team_id}/players",
        json={"first_name": "B", "last_name": "B", "jersey_number": 2, "role": "CENTRAL", "license_number": None},
    )

    r = client.get(f"/teams/{team_id}/players")
    assert r.status_code == 200
    players = r.json()
    assert len(players) == 2
    assert players[0]["jersey_number"] == 1
    assert players[1]["jersey_number"] == 2


def test_duplicate_jersey_number_same_team(client):
    team = client.post("/teams", json={"name": "Team A"}).json()
    team_id = team["id"]

    client.post(
        f"/teams/{team_id}/players",
        json={"first_name": "Julie", "last_name": "Martin", "jersey_number": 7, "role": "PASSEUR", "license_number": None},
    )

    r = client.post(
        f"/teams/{team_id}/players",
        json={"first_name": "Lina", "last_name": "Durand", "jersey_number": 7, "role": "POINTU", "license_number": None},
    )

    assert r.status_code == 400
