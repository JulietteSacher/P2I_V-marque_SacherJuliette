def test_player_stats(client):
    team_a = client.post("/teams", json={"name": "Team A"}).json()
    team_b = client.post("/teams", json={"name": "Team B"}).json()

    player = client.post(
        f"/teams/{team_a['id']}/players",
        json={
            "first_name": "Julie",
            "last_name": "Dupont",
            "jersey_number": 7,
            "role": "R4"
        }
    ).json()

    match = client.post(
        "/matches",
        json={"team_a_id": team_a["id"], "team_b_id": team_b["id"]}
    ).json()

    client.post(f"/matches/{match['id']}/start")

    # Actions
    client.post(f"/matches/{match['id']}/actions", json={
        "player_id": player["id"],
        "action_type": "ATTACK_KILL"
    })
    client.post(f"/matches/{match['id']}/actions", json={
        "player_id": player["id"],
        "action_type": "SERVICE_ERROR"
    })

    stats = client.get(
        f"/matches/{match['id']}/players/{player['id']}/stats"
    ).json()

    assert stats["attack_points"] == 1
    assert stats["service_faults"] == 1
    assert stats["total_points"] == 1
    assert stats["total_faults"] == 1
