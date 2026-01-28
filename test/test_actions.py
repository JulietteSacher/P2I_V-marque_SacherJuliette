def test_add_action_updates_score(client):
    # Créer équipes
    team_a = client.post("/teams", json={"name": "Team A"}).json()
    team_b = client.post("/teams", json={"name": "Team B"}).json()

    # Ajouter joueurs
    player = client.post(
        f"/teams/{team_a['id']}/players",
        json={
            "first_name": "Julie",
            "last_name": "Dupont",
            "jersey_number": 7,
            "role": "R4"
        }
    ).json()

    # Créer match
    match = client.post(
        "/matches",
        json={"team_a_id": team_a["id"], "team_b_id": team_b["id"]}
    ).json()

    # Démarrer match
    client.post(f"/matches/{match['id']}/start")

    # Ajouter action donnant un point
    response = client.post(
        f"/matches/{match['id']}/actions",
        json={
            "player_id": player["id"],
            "action_type": "ATTACK_KILL"
        }
    )

    assert response.status_code == 201
    action = response.json()
    assert action["point_won"] is True
