export interface TeamStats {
  team_id: number;
  service_points: number;
  attack_points: number;
  block_points: number;
  service_faults: number;
  attack_faults: number;
  block_faults: number;
  total_points: number;
  total_faults: number;
}

export interface PlayerStats {
  player_id: number;
  service_points: number;
  attack_points: number;
  block_points: number;
  service_faults: number;
  attack_faults: number;
  block_faults: number;
  total_points: number;
  total_faults: number;
}

export interface PlayerRead {
  id: number;
  team_id: number;
  first_name: string;
  last_name: string;
  jersey_number: number;
  role: string;
  license_number?: string | null;
}