export interface PlayerRead {
  id: number;
  team_id: number;
  first_name: string;
  last_name: string;
  jersey_number: number;
  role: string;
  license_number?: string | null;
}