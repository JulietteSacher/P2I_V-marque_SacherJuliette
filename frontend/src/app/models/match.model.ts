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
  starting_team_id?: number | null;
}

export interface FinishedSetRead {
  set_number: number;
  score_team_a: number;
  score_team_b: number;
  winner_team_id?: number | null;
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

export interface MatchLiveRead {
  match: MatchRead;
  current_set: SetRead;
  team_a: TeamRead;
  team_b: TeamRead;
  court_a: CourtView;
  court_b: CourtView;
  team_a_sets_won: number;
  team_b_sets_won: number;
  finished_sets: FinishedSetRead[];
}

export interface MatchCreatePayload {
  team_a_id: number;
  team_b_id: number;
  sets_to_win: number;
}

export interface TeamCreatePayload {
  name: string;
}

export interface PlayerCreatePayload {
  first_name: string;
  last_name: string;
  jersey_number: number;
  role: string;
  license_number?: string | null;
}

export interface LineupCreatePayload {
  p1: number;
  p2: number;
  p3: number;
  p4: number;
  p5: number;
  p6: number;
}

export interface ServeStartPayload {
  team_id: number;
}

export interface SwapPlayerPayload {
  player_out_id: number;
  player_in_id: number;
}

export interface ActionCreatePayload {
  player_id: number;
  action_type: string;
}