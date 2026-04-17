def _create_6_players(client, team_id: int, prefix: str):
    players = {}
    for j in range(1, 7):
        response = client.post(
            f"/teams/{team_id}/players",
            json={
                "first_name": prefix,
                "last_name": f"{prefix}{j}",
                "jersey_number": j,
                "role": "PASSEUR",
                "license_number": f"LIC-{prefix}{j}",
            },
        )
        assert response.status_code == 201, response.text
        players[j] = response.json()["id"]
    return players


def test_set_serving_team_starts_set(client):
    team_a = client.post("/teams", json={"name": "Team A"}).json()
    team_b = client.post("/teams", json={"name": "Team B"}).json()

    _create_6_players(client, team_a["id"], "A")
    _create_6_players(client, team_b["id"], "B")

    match = client.post(
        "/matches",
        json={"team_a_id": team_a["id"], "team_b_id": team_b["id"], "sets_to_win": 2},
    ).json()

    r = client.post(f"/matches/{match['id']}/start")
    assert r.status_code == 200, r.text

    r = client.post(
        f"/lineup/matches/{match['id']}/teams/{team_a['id']}",
        json={"p1": 1, "p2": 2, "p3": 3, "p4": 4, "p5": 5, "p6": 6},
    )
    assert r.status_code == 200, r.text

    r = client.post(
        f"/lineup/matches/{match['id']}/teams/{team_b['id']}",
        json={"p1": 1, "p2": 2, "p3": 3, "p4": 4, "p5": 5, "p6": 6},
    )
    assert r.status_code == 200, r.text

    r = client.post(f"/matches/{match['id']}/serve", json={"team_id": team_a["id"]})
    assert r.status_code == 200, r.text

    payload = r.json()
    assert payload["serving_team_id"] == team_a["id"]
    assert payload["starting_team_id"] == team_a["id"]
    assert payload["set_status"] == "running"

    current_set = client.get(f"/matches/{match['id']}/current-set")
    assert current_set.status_code == 200, current_set.text
    current_set = current_set.json()
    assert current_set["status"] == "running"
    assert current_set["serving_team_id"] == team_a["id"]
    assert current_set["starting_team_id"] == team_a["id"]


def test_serve_requires_lineups(client):
    team_a = client.post("/teams", json={"name": "Team A"}).json()
    team_b = client.post("/teams", json={"name": "Team B"}).json()

    _create_6_players(client, team_a["id"], "A")
    _create_6_players(client, team_b["id"], "B")

    match = client.post(
        "/matches",
        json={"team_a_id": team_a["id"], "team_b_id": team_b["id"], "sets_to_win": 2},
    ).json()

    r = client.post(f"/matches/{match['id']}/start")
    assert r.status_code == 200, r.text

    r = client.post(f"/matches/{match['id']}/serve", json={"team_id": team_a["id"]})
    assert r.status_code == 400, r.text
    assert "Lineup incomplet" in r.text