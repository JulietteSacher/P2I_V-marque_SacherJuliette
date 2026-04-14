import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { forkJoin } from 'rxjs';

import { MatchesService } from '../../api/matches.service';
import { PlayersService } from '../../api/players.service';
import { TeamsService } from '../../api/teams.service';
import { CourtComponent } from '../../components/court/court.component';
import { PlayerRead } from '../../models/player.model';
import {
  CourtView,
  MatchRead,
  SetRead,
  TeamRead,
} from '../../models/match.model';

@Component({
  selector: 'app-match-live-page',
  standalone: true,
  imports: [CommonModule, FormsModule, CourtComponent],
  templateUrl: './match-page.component.html',
  styleUrl: './match-page.component.scss',
})
export class MatchLivePageComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private matchesService = inject(MatchesService);
  private playersService = inject(PlayersService);
  private teamsService = inject(TeamsService);

  matchId = 1;

  match?: MatchRead;
  currentSet?: SetRead;
  teamA?: TeamRead;
  teamB?: TeamRead;
  courtA?: CourtView;
  courtB?: CourtView;

  allPlayersA: PlayerRead[] = [];
  allPlayersB: PlayerRead[] = [];
  benchA: PlayerRead[] = [];
  benchB: PlayerRead[] = [];

  selectedOutA?: number;
  selectedInA?: number;
  selectedOutB?: number;
  selectedInB?: number;

  loading = true;
  error = '';

  ngOnInit(): void {
    this.route.paramMap.subscribe((params) => {
      this.matchId = Number(params.get('matchId')) || Number(localStorage.getItem('currentMatchId')) || 1;
      this.loadPage();
    });
  }

  loadPage(retryCount = 0): void {
    this.loading = true;
    this.error = '';

    this.matchesService.getMatch(this.matchId).subscribe({
      next: (match) => {
        this.match = match;

        forkJoin({
          currentSet: this.matchesService.getCurrentSet(this.matchId),
          teamA: this.teamsService.getTeam(match.team_a_id),
          teamB: this.teamsService.getTeam(match.team_b_id),
          courtA: this.matchesService.getCourtView(this.matchId, match.team_a_id),
          courtB: this.matchesService.getCourtView(this.matchId, match.team_b_id),
          playersA: this.playersService.getPlayersByTeam(match.team_a_id),
          playersB: this.playersService.getPlayersByTeam(match.team_b_id),
        }).subscribe({
          next: (data) => {
            this.currentSet = data.currentSet;
            this.teamA = data.teamA;
            this.teamB = data.teamB;
            this.courtA = data.courtA;
            this.courtB = data.courtB;
            this.allPlayersA = data.playersA;
            this.allPlayersB = data.playersB;
            this.computeBench();
            this.loading = false;
          },
          error: (err) => {
            console.error(err);

            if (retryCount < 5) {
              setTimeout(() => this.loadPage(retryCount + 1), 400);
              return;
            }

            this.error =
              err?.error?.detail || 'Impossible de charger les données du match.';
            this.loading = false;
          },
        });
      },
      error: (err) => {
        console.error(err);

        if (retryCount < 5) {
          setTimeout(() => this.loadPage(retryCount + 1), 400);
          return;
        }

        this.error = err?.error?.detail || 'Match introuvable.';
        this.loading = false;
      },
    });
  }

  computeBench(): void {
    const onCourtA = new Set((this.courtA?.cells || []).map((c) => c.jersey_number));
    const onCourtB = new Set((this.courtB?.cells || []).map((c) => c.jersey_number));

    this.benchA = this.allPlayersA.filter((p) => !onCourtA.has(p.jersey_number));
    this.benchB = this.allPlayersB.filter((p) => !onCourtB.has(p.jersey_number));
  }

  swapA(): void {
    if (!this.teamA || !this.selectedOutA || !this.selectedInA) return;

    this.matchesService.swapPlayers(this.matchId, this.teamA.id, {
      player_out_id: this.selectedOutA,
      player_in_id: this.selectedInA,
    }).subscribe({
      next: () => this.loadPage(),
      error: (err) => {
        console.error(err);
        this.error = err?.error?.detail || 'Erreur lors du changement de joueur.';
      },
    });
  }

  swapB(): void {
    if (!this.teamB || !this.selectedOutB || !this.selectedInB) return;

    this.matchesService.swapPlayers(this.matchId, this.teamB.id, {
      player_out_id: this.selectedOutB,
      player_in_id: this.selectedInB,
    }).subscribe({
      next: () => this.loadPage(),
      error: (err) => {
        console.error(err);
        this.error = err?.error?.detail || 'Erreur lors du changement de joueur.';
      },
    });
  }

  addAction(playerId: number, actionType: string): void {
    this.matchesService.addAction(this.matchId, {
      player_id: playerId,
      action_type: actionType,
    }).subscribe({
      next: () => this.loadPage(),
      error: (err) => {
        console.error(err);
        this.error = err?.error?.detail || 'Erreur lors de l’ajout de l’action.';
      },
    });
  }

  getPlayerByJersey(team: 'A' | 'B', jersey: number): PlayerRead | undefined {
    const source = team === 'A' ? this.allPlayersA : this.allPlayersB;
    return source.find((p) => p.jersey_number === jersey);
  }

  refresh(): void {
    this.loadPage();
  }
}