import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, forkJoin } from 'rxjs';

import {
  ActionCreatePayload,
  CourtView,
  LineupCreatePayload,
  LineupPlayer,
  MatchCreatePayload,
  MatchLiveRead,
  MatchRead,
  ServeStartPayload,
  SetRead,
  SwapPlayerPayload,
} from '../models/match.model';
import { PlayerStats, TeamStats } from '../models/stats.model';

@Injectable({ providedIn: 'root' })
export class MatchesService {
  private baseUrl = 'http://127.0.0.1:8000';

  constructor(private http: HttpClient) {}

  createMatch(payload: MatchCreatePayload): Observable<MatchRead> {
    return this.http.post<MatchRead>(`${this.baseUrl}/matches`, payload);
  }

  startMatch(matchId: number): Observable<MatchRead> {
    return this.http.post<MatchRead>(`${this.baseUrl}/matches/${matchId}/start`, {});
  }

  setInitialLineup(matchId: number, teamId: number, payload: LineupCreatePayload): Observable<any> {
    return this.http.post(`${this.baseUrl}/lineup/matches/${matchId}/teams/${teamId}`, payload);
  }

  setServingTeam(matchId: number, payload: ServeStartPayload): Observable<any> {
    return this.http.post(`${this.baseUrl}/matches/${matchId}/serve`, payload);
  }

  swapPlayers(matchId: number, teamId: number, payload: SwapPlayerPayload): Observable<any> {
    return this.http.post(`${this.baseUrl}/lineup/matches/${matchId}/teams/${teamId}/swap`, payload);
  }

  addAction(matchId: number, payload: ActionCreatePayload): Observable<any> {
    return this.http.post(`${this.baseUrl}/matches/${matchId}/actions`, payload);
  }

  getMatch(matchId: number): Observable<MatchRead> {
    return this.http.get<MatchRead>(`${this.baseUrl}/matches/${matchId}`);
  }

  getMatchLive(matchId: number): Observable<MatchLiveRead> {
    return this.http.get<MatchLiveRead>(`${this.baseUrl}/matches/${matchId}/live`);
  }

  getCurrentSet(matchId: number): Observable<SetRead> {
    return this.http.get<SetRead>(`${this.baseUrl}/matches/${matchId}/current-set`);
  }

  getCourtView(matchId: number, teamId: number): Observable<CourtView> {
    return this.http.get<CourtView>(`${this.baseUrl}/matches/${matchId}/teams/${teamId}/court-view`);
  }

  getLineup(matchId: number, teamId: number): Observable<LineupPlayer[]> {
    return this.http.get<LineupPlayer[]>(`${this.baseUrl}/matches/${matchId}/teams/${teamId}/lineup`);
  }

  getTeamStats(matchId: number, teamId: number): Observable<TeamStats> {
    return this.http.get<TeamStats>(`${this.baseUrl}/matches/${matchId}/teams/${teamId}/stats`);
  }

  getPlayerStats(matchId: number, playerId: number): Observable<PlayerStats> {
    return this.http.get<PlayerStats>(`${this.baseUrl}/matches/${matchId}/players/${playerId}/stats`);
  }

  deleteMatch(matchId: number) {
    return this.http.delete(`${this.baseUrl}/matches/${matchId}`);
  }

  getMatchLiveData(matchId: number, teamAId: number, teamBId: number) {
    return forkJoin({
      currentSet: this.getCurrentSet(matchId),
      courtA: this.getCourtView(matchId, teamAId),
      courtB: this.getCourtView(matchId, teamBId),
      lineupA: this.getLineup(matchId, teamAId),
      lineupB: this.getLineup(matchId, teamBId),
    });
  }
}

