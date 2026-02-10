def rotate_positions_map(pos_to_player: dict[int, int]) -> dict[int, int]:
    
    return {
        1: pos_to_player[2],
        2: pos_to_player[3],
        3: pos_to_player[4],
        4: pos_to_player[5],
        5: pos_to_player[6],
        6: pos_to_player[1],
    }
