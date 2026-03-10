# test/test_team_stats.py

def _create_6_players(client, team_id: int, prefix: str):
    for j in range(1, 7):
        client.post(
            f"/teams/{team_id}/players",
            json={
                "first_name": prefix,
                "last_name": f"{prefix}{j}",
                "jersey_number": j,
                "role": "PASSEUR",
                "license_number": f"LIC-{prefix}{j}",
            },
        )


def test_team_stats(client):
    team_a = client.post("/teams", json={"name": "Team A"}).json()
    team_b = client.post("/teams", json={"name": "Team B"}).json()

    _create_6_players(client, team_a["id"], "A")
    _create_6_players(client, team_b["id"], "B")

    match = client.post(
        "/matches",
        json={"team_a_id": team_a["id"], "team_b_id": team_b["id"], "sets_to_win": 2},
    ).json()

    client.post(f"/matches/{match['id']}/start")

    # lineups A + B
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

    # IMPORTANT : chez toi ça met le set en "running"
    r = client.post(f"/matches/{match['id']}/serve", json={"team_id": team_a["id"]})
    assert r.status_code == 200, r.text

    # joueur maillot 4
    players_a = client.get(f"/teams/{team_a['id']}/players").json()
    p4 = next(p for p in players_a if p["jersey_number"] == 4)

    # action
    r = client.post(
        f"/matches/{match['id']}/actions",
        json={"player_id": p4["id"], "action_type": "ATTACK_KILL"},
    )
    assert r.status_code == 201, r.text

    stats = client.get(f"/matches/{match['id']}/teams/{team_a['id']}/stats").json()
    assert stats["attack_points"] == 1