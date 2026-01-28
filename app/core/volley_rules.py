def points_to_win_set(set_number: int) -> int:
    # règles standard volley indoor : 25, sauf tie-break (5e set) à 15
    return 15 if set_number == 5 else 25


def is_set_won(score_a: int, score_b: int, set_number: int) -> bool:
    target = points_to_win_set(set_number)
    # il faut atteindre target ET avoir 2 points d’écart
    if score_a >= target or score_b >= target:
        return abs(score_a - score_b) >= 2
    return False
