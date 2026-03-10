# test/test_actions.py

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


def test_add_action_updates_score(client):
    # Créer équipes
    team_a = client.post("/teams", json={"name": "Team A"}).json()
    team_b = client.post("/teams", json={"name": "Team B"}).json()

    # Créer 6 joueurs dans chaque équipe (maillots 1..6)
    players_a = _create_6_players(client, team_a["id"], "A")
    _create_6_players(client, team_b["id"], "B")

    # Créer match + démarrer
    match = client.post(
        "/matches",
        json={"team_a_id": team_a["id"], "team_b_id": team_b["id"], "sets_to_win": 2},
    ).json()
    client.post(f"/matches/{match['id']}/start")

    # Définir lineups A + B (obligatoire dans ta logique)
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

    # Définir l'équipe au service (chez toi ça déclenche le set "running")
    r = client.post(f"/matches/{match['id']}/serve", json={"team_id": team_a["id"]})
    assert r.status_code == 200, r.text

    # Score initial
    s0 = client.get(f"/matches/{match['id']}/current-set")
    assert s0.status_code == 200, s0.text
    s0 = s0.json()
    a0, b0 = s0["score_team_a"], s0["score_team_b"]

    # Ajouter action donnant un point
    response = client.post(
        f"/matches/{match['id']}/actions",
        json={"player_id": players_a[4], "action_type": "ATTACK_KILL"},
    )
    assert response.status_code == 201, response.text
    action = response.json()
    assert action["point_won"] is True

    # Vérifier score mis à jour
    s1 = client.get(f"/matches/{match['id']}/current-set")
    assert s1.status_code == 200, s1.text
    s1 = s1.json()
    assert s1["score_team_a"] == a0 + 1
    assert s1["score_team_b"] == b0