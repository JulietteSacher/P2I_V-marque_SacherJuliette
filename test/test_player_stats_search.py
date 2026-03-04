def _create_6_players(client, team_id: int, prefix: str):
    players = {}
    for j in range(1, 7):
        p = client.post(
            f"/teams/{team_id}/players",
            json={
                "first_name": prefix,
                "last_name": f"{prefix}{j}",
                "jersey_number": j,
                "role": "PASSEUR",
                "license_number": f"LIC-{prefix}{j}",
            },
        ).json()
        players[j] = p["id"]
    return players


def test_player_stats_search_by_jersey(client):
    team_a = client.post("/teams", json={"name": "Team A"}).json()
    team_b = client.post("/teams", json={"name": "Team B"}).json()

    players_a = _create_6_players(client, team_a["id"], "A")
    _create_6_players(client, team_b["id"], "B")

    match = client.post(
        "/matches",
        json={"team_a_id": team_a["id"], "team_b_id": team_b["id"], "sets_to_win": 2},
    ).json()
    client.post(f"/matches/{match['id']}/start")

    client.post(f"/lineup/matches/{match['id']}/teams/{team_a['id']}",
                json={"p1": 1, "p2": 2, "p3": 3, "p4": 4, "p5": 5, "p6": 6})
    client.post(f"/lineup/matches/{match['id']}/teams/{team_b['id']}",
                json={"p1": 1, "p2": 2, "p3": 3, "p4": 4, "p5": 5, "p6": 6})

    client.post(f"/matches/{match['id']}/serve", json={"team_id": team_a["id"]})

    client.post(f"/matches/{match['id']}/actions", json={
        "player_id": players_a[1],
        "action_type": "SERVICE_ACE"
    })

    stats = client.get(f"/matches/{match['id']}/players/stats/search?jersey_number=1").json()
    assert stats["service_points"] == 1