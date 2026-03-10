export interface MatchRead {
  id: number;
  status: string;
  team_a_id: number;
  team_b_id: number;
  sets_to_win: number;
}
export interface SetRead {
  id: number;
  set_number: number;
  score_team_a: number;
  score_team_b: number;
  status: string;
  serving_team_id?: number | null;
}

export interface TeamRead {
  id: number;
  name: string;
  created_at: string;
}

export interface CourtCell {
  x: number;
  y: number;
  position: number;
  label: string;
  jersey_number: number;
}

export interface CourtView {
  team_id: number;
  set_id: number;
  cells: CourtCell[];
  constraints: {
    left_right: Array<{ a_pos: number; b_pos: number; rule: string }>;
    front_back: Array<{ front_pos: number; back_pos: number; rule: string }>;
  };
}

export interface LineupPlayer {
  position: number;
  jersey_number: number;
}