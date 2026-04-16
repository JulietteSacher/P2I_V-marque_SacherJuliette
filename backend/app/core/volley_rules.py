def target_points_for_set(set_number: int, sets_to_win: int) -> int:
    deciding_set_number = 2 * sets_to_win - 1
    return 15 if set_number == deciding_set_number else 25


def is_set_won(
    score_team_a: int,
    score_team_b: int,
    set_number: int,
    sets_to_win: int,
) -> bool:
    target = target_points_for_set(set_number, sets_to_win)
    return max(score_team_a, score_team_b) >= target and abs(score_team_a - score_team_b) >= 2