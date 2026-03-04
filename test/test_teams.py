def test_create_team_and_get(client):
    team = client.post("/teams", json={"name": "Team A"}).json()
    assert "id" in team
    assert team["name"] == "Team A"

    got = client.get(f"/teams/{team['id']}").json()
    assert got["id"] == team["id"]
    assert got["name"] == "Team A"


def test_list_teams(client):
    client.post("/teams", json={"name": "Team A"})
    client.post("/teams", json={"name": "Team B"})

    teams = client.get("/teams").json()
    assert len(teams) >= 2


def test_duplicate_team_name_rejected(client):
    client.post("/teams", json={"name": "Team A"})
    r = client.post("/teams", json={"name": "Team A"})
    assert r.status_code == 400