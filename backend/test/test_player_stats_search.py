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


def test_player_stats_lookup_from_jersey_via_roster(client):
    team_a = client.post("/teams", json={"name": "Team A"}).json()
    team_b = client.post("/teams", json={"name": "Team B"}).json()

    _create_6_players(client, team_a["id"], "A")
    _create_6_players(client, team_b["id"], "B")

    match = client.post(
        "/matches",
        json={"team_a_id": team_a["id"], "team_b_id": team_b["id"], "sets_to_win": 2},
    ).json()

    client.post(f"/matches/{match['id']}/start")

    client.post(
        f"/lineup/matches/{match['id']}/teams/{team_a['id']}",
        json={"p1": 1, "p2": 2, "p3": 3, "p4": 4, "p5": 5, "p6": 6},
    )
    client.post(
        f"/lineup/matches/{match['id']}/teams/{team_b['id']}",
        json={"p1": 1, "p2": 2, "p3": 3, "p4": 4, "p5": 5, "p6": 6},
    )

    client.post(f"/matches/{match['id']}/serve", json={"team_id": team_a["id"]})

    roster = client.get(f"/teams/{team_a['id']}/players")
    assert roster.status_code == 200, roster.text
    roster = roster.json()

    player_jersey_1 = next(player for player in roster if player["jersey_number"] == 1)

    r = client.post(
        f"/matches/{match['id']}/actions",
        json={
            "player_id": player_jersey_1["id"],
            "action_type": "SERVICE_ACE",
        },
    )
    assert r.status_code == 201, r.text

    stats = client.get(
        f"/matches/{match['id']}/players/{player_jersey_1['id']}/stats"
    )
    assert stats.status_code == 200, stats.text
    stats = stats.json()

    assert stats["player_id"] == player_jersey_1["id"]
    assert stats["service_points"] == 1
    assert stats["total_points"] == 1