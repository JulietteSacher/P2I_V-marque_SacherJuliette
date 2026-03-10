import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { PlayerRead } from '../models/stats.model';

@Injectable({ providedIn: 'root' })
export class PlayersService {
  private baseUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  getPlayersByTeam(teamId: number): Observable<PlayerRead[]> {
    return this.http.get<PlayerRead[]>(`${this.baseUrl}/players?team_id=${teamId}`);
  }
}