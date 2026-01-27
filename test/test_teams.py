def test_create_team(client):
    r = client.post("/teams", json={"name": "Team A"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Team A"
    assert "id" in data


def test_list_teams(client):
    client.post("/teams", json={"name": "Team A"})
    client.post("/teams", json={"name": "Team B"})

    r = client.get("/teams")
    assert r.status_code == 200
    teams = r.json()
    assert len(teams) == 2
    assert teams[0]["name"] == "Team A"
    assert teams[1]["name"] == "Team B"


def test_duplicate_team_name(client):
    client.post("/teams", json={"name": "Team A"})
    r = client.post("/teams", json={"name": "Team A"})
    assert r.status_code == 400
