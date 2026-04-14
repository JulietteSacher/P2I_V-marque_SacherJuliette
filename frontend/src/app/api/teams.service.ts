import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { TeamRead, TeamCreatePayload } from '../models/match.model';

@Injectable({ providedIn: 'root' })
export class TeamsService {
  private baseUrl = 'http://127.0.0.1:8000';

  constructor(private http: HttpClient) {}

  getTeam(teamId: number): Observable<TeamRead> {
    return this.http.get<TeamRead>(`${this.baseUrl}/teams/${teamId}`);
  }

  createTeam(payload: TeamCreatePayload): Observable<TeamRead> {
    return this.http.post<TeamRead>(`${this.baseUrl}/teams`, payload);
  }
}