import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { TeamRead } from '../models/match.model';

@Injectable({ providedIn: 'root' })
export class TeamsService {
  private baseUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  getTeam(teamId: number): Observable<TeamRead> {
    return this.http.get<TeamRead>(`${this.baseUrl}/teams/${teamId}`);
  }
}