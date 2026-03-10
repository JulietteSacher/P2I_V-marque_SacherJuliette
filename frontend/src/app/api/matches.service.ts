import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { forkJoin, Observable } from 'rxjs';
import { CourtView, LineupPlayer, SetRead } from '../models/match.model';
import { TeamStats, PlayerStats } from '../models/stats.model';
import { MatchRead } from '../models/match.model';

@Injectable({ providedIn: 'root' })
export class MatchesService {
  private baseUrl = 'http://localhost:8000';

  constructor(private http: HttpClient) {}

  getMatch(matchId: number): Observable<MatchRead> {
    return this.http.get<MatchRead>(`${this.baseUrl}/matches/${matchId}`);
  }
  
  getCurrentSet(matchId: number): Observable<SetRead> {
    return this.http.get<SetRead>(`${this.baseUrl}/matches/${matchId}/current-set`);
  }

  getCourtView(matchId: number, teamId: number): Observable<CourtView> {
    return this.http.get<CourtView>(
      `${this.baseUrl}/matches/${matchId}/teams/${teamId}/court-view`
    );
  }

  getLineup(matchId: number, teamId: number): Observable<LineupPlayer[]> {
    return this.http.get<LineupPlayer[]>(
      `${this.baseUrl}/matches/${matchId}/teams/${teamId}/lineup`
    );
  }

  getTeamStats(matchId: number, teamId: number): Observable<TeamStats> {
    return this.http.get<TeamStats>(
      `${this.baseUrl}/matches/${matchId}/teams/${teamId}/stats`
    );
  }

  getPlayerStats(matchId: number, playerId: number): Observable<PlayerStats> {
    return this.http.get<PlayerStats>(
      `${this.baseUrl}/matches/${matchId}/players/${playerId}/stats`
    );
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