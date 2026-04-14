import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { PlayerRead } from '../models/player.model';
import { PlayerCreatePayload } from '../models/match.model';

@Injectable({ providedIn: 'root' })
export class PlayersService {
  private baseUrl = 'http://127.0.0.1:8000';

  constructor(private http: HttpClient) {}

  getPlayersByTeam(teamId: number): Observable<PlayerRead[]> {
    return this.http.get<PlayerRead[]>(`${this.baseUrl}/teams/${teamId}/players`);
  }

  createPlayer(teamId: number, payload: PlayerCreatePayload): Observable<PlayerRead> {
    return this.http.post<PlayerRead>(`${this.baseUrl}/teams/${teamId}/players`, payload);
  }
}