import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { forkJoin } from 'rxjs';

import { MatchesService } from '../../api/matches.service';
import { PlayersService } from '../../api/players.service';
import { TeamsService } from '../../api/teams.service';
import { PlayerRead } from '../../models/player.model';
import { TeamRead } from '../../models/match.model';

@Component({
  selector: 'app-match-stats-page',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './stats-page.component.html',
  styleUrl: './stats-page.component.scss',
})
export class MatchStatsPageComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private matchesService = inject(MatchesService);
  private playersService = inject(PlayersService);
  private teamsService = inject(TeamsService);

  matchId = 1;
  teamAId = Number(localStorage.getItem('teamAId') || 0);
  teamBId = Number(localStorage.getItem('teamBId') || 0);

  teamA?: TeamRead;
  teamB?: TeamRead;

  statsA: any;
  statsB: any;

  playersA: PlayerRead[] = [];
  playersB: PlayerRead[] = [];
  filteredPlayers: PlayerRead[] = [];

  selectedPlayer?: PlayerRead;
  selectedPlayerStats: any;

  searchTerm = '';
  loading = true;
  error = '';

  ngOnInit(): void {
    this.matchId = Number(this.route.snapshot.paramMap.get('matchId')) || 1;
    this.loadStats();
  }

  loadStats(): void {
    this.loading = true;
    this.error = '';

    forkJoin({
      teamA: this.teamsService.getTeam(this.teamAId),
      teamB: this.teamsService.getTeam(this.teamBId),
      statsA: this.matchesService.getTeamStats(this.matchId, this.teamAId),
      statsB: this.matchesService.getTeamStats(this.matchId, this.teamBId),
      playersA: this.playersService.getPlayersByTeam(this.teamAId),
      playersB: this.playersService.getPlayersByTeam(this.teamBId),
    }).subscribe({
      next: (data) => {
        this.teamA = data.teamA;
        this.teamB = data.teamB;
        this.statsA = data.statsA;
        this.statsB = data.statsB;
        this.playersA = data.playersA;
        this.playersB = data.playersB;
        this.filteredPlayers = [...this.playersA, ...this.playersB];
        this.loading = false;
      },
      error: (err) => {
        console.error(err);
        this.error = err?.error?.detail || 'Impossible de charger les statistiques.';
        this.loading = false;
      },
    });
  }

  searchPlayer(): void {
    const term = this.searchTerm.trim().toLowerCase();

    this.filteredPlayers = [...this.playersA, ...this.playersB].filter((p) =>
      p.first_name.toLowerCase().includes(term) ||
      p.last_name.toLowerCase().includes(term) ||
      String(p.jersey_number).includes(term)
    );
  }

  loadPlayerStats(player: PlayerRead): void {
    this.selectedPlayer = player;

    this.matchesService.getPlayerStats(this.matchId, player.id).subscribe({
      next: (stats) => {
        this.selectedPlayerStats = stats;
      },
      error: (err) => {
        console.error(err);
        this.error = err?.error?.detail || 'Impossible de charger les stats du joueur.';
      },
    });
  }

  statValue(stats: any, keys: string[], fallback = 0): number {
    for (const key of keys) {
      if (stats && stats[key] !== undefined && stats[key] !== null) {
        return Number(stats[key]);
      }
    }
    return fallback;
  }
}