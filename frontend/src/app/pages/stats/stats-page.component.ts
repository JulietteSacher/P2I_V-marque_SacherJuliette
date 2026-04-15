import {
  ChangeDetectorRef,
  Component,
  DestroyRef,
  NgZone,
  OnInit,
  inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { forkJoin, switchMap } from 'rxjs';

import { MatchesService } from '../../api/matches.service';
import { PlayersService } from '../../api/players.service';
import { TeamsService } from '../../api/teams.service';
import { PlayerRead } from '../../models/player.model';
import { MatchRead, TeamRead } from '../../models/match.model';
import { PlayerStats, TeamStats } from '../../models/stats.model';

type StatsLike = TeamStats | PlayerStats | null | undefined;

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
  private zone = inject(NgZone);
  private cdr = inject(ChangeDetectorRef);
  private destroyRef = inject(DestroyRef);

  matchId = 1;
  match?: MatchRead;

  teamAId = 0;
  teamBId = 0;

  teamA?: TeamRead;
  teamB?: TeamRead;

  statsA?: TeamStats;
  statsB?: TeamStats;

  playersA: PlayerRead[] = [];
  playersB: PlayerRead[] = [];
  filteredPlayers: PlayerRead[] = [];

  selectedPlayer?: PlayerRead;
  selectedPlayerStats?: PlayerStats;

  searchTerm = '';
  loading = true;
  pageError = '';
  playerError = '';
  playerStatsLoading = false;

  ngOnInit(): void {
    this.matchId = Number(this.route.snapshot.paramMap.get('matchId')) || 1;
    this.loadStats();
  }

  private runInUi(fn: () => void): void {
    this.zone.run(() => {
      fn();
      this.pushUi();
    });
  }

  private pushUi(): void {
    try {
      this.cdr.detectChanges();
    } catch {
      this.cdr.markForCheck();
    }
  }

  private buildErrorMessage(err: any, fallback: string): string {
    if (err?.status === 0) {
      return 'Backend inaccessible : vérifie que FastAPI est lancé sur http://127.0.0.1:8000';
    }

    if (typeof err?.error?.detail === 'string' && err.error.detail.trim() !== '') {
      return err.error.detail;
    }

    if (typeof err?.message === 'string' && err.message.trim() !== '') {
      return err.message;
    }

    return fallback;
  }

  private normalizeSearchValue(value: unknown): string {
    return String(value ?? '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .trim();
  }

  private allPlayers(): PlayerRead[] {
    return [...this.playersA, ...this.playersB];
  }

  private applySearch(): void {
    const term = this.normalizeSearchValue(this.searchTerm);

    if (!term) {
      this.filteredPlayers = this.allPlayers();
      return;
    }

    this.filteredPlayers = this.allPlayers().filter((player) => {
      const fullName = this.normalizeSearchValue(`${player.first_name} ${player.last_name}`);
      const reversedName = this.normalizeSearchValue(`${player.last_name} ${player.first_name}`);
      const jersey = this.normalizeSearchValue(player.jersey_number);
      const role = this.normalizeSearchValue(player.role);
      const teamName = this.normalizeSearchValue(this.getPlayerTeamName(player));

      return (
        fullName.includes(term) ||
        reversedName.includes(term) ||
        jersey.includes(term) ||
        role.includes(term) ||
        teamName.includes(term)
      );
    });
  }

  loadStats(): void {
    this.loading = true;
    this.pageError = '';
    this.playerError = '';

    this.matchesService
      .getMatch(this.matchId)
      .pipe(
        switchMap((match) => {
          this.match = match;
          this.teamAId = match.team_a_id;
          this.teamBId = match.team_b_id;

          localStorage.setItem('teamAId', String(this.teamAId));
          localStorage.setItem('teamBId', String(this.teamBId));

          return forkJoin({
            teamA: this.teamsService.getTeam(this.teamAId),
            teamB: this.teamsService.getTeam(this.teamBId),
            statsA: this.matchesService.getTeamStats(this.matchId, this.teamAId),
            statsB: this.matchesService.getTeamStats(this.matchId, this.teamBId),
            playersA: this.playersService.getPlayersByTeam(this.teamAId),
            playersB: this.playersService.getPlayersByTeam(this.teamBId),
          });
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (data) =>
          this.runInUi(() => {
            this.teamA = data.teamA;
            this.teamB = data.teamB;
            this.statsA = data.statsA;
            this.statsB = data.statsB;
            this.playersA = data.playersA;
            this.playersB = data.playersB;

            this.applySearch();

            if (this.selectedPlayer) {
              const refreshedSelectedPlayer = this.allPlayers().find(
                (player) => player.id === this.selectedPlayer?.id
              );

              if (refreshedSelectedPlayer) {
                this.selectedPlayer = refreshedSelectedPlayer;
              } else {
                this.selectedPlayer = undefined;
                this.selectedPlayerStats = undefined;
                this.playerError = '';
                this.playerStatsLoading = false;
              }
            }

            this.loading = false;
          }),
        error: (err) =>
          this.runInUi(() => {
            this.pageError = this.buildErrorMessage(
              err,
              'Impossible de charger les statistiques.'
            );
            this.loading = false;
          }),
      });
  }

  searchPlayer(): void {
    this.applySearch();
    this.pushUi();
  }

  loadPlayerStats(player: PlayerRead): void {
    this.selectedPlayer = player;
    this.selectedPlayerStats = undefined;
    this.playerError = '';
    this.playerStatsLoading = true;

    this.matchesService
      .getPlayerStats(this.matchId, player.id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (stats) =>
          this.runInUi(() => {
            this.selectedPlayerStats = stats;
            this.playerStatsLoading = false;
          }),
        error: (err) =>
          this.runInUi(() => {
            this.playerStatsLoading = false;
            this.playerError = this.buildErrorMessage(
              err,
              'Impossible de charger les stats du joueur.'
            );
          }),
      });
  }

  clearSelectedPlayer(): void {
    this.selectedPlayer = undefined;
    this.selectedPlayerStats = undefined;
    this.playerError = '';
    this.playerStatsLoading = false;
    this.pushUi();
  }

  isPlayerFromTeamA(player?: PlayerRead): boolean {
    if (!player) {
      return false;
    }

    if (this.teamA) {
      return player.team_id === this.teamA.id;
    }

    return this.playersA.some((p) => p.id === player.id);
  }

  isSelectedPlayer(player?: PlayerRead): boolean {
    return !!player && !!this.selectedPlayer && player.id === this.selectedPlayer.id;
  }

  getPlayerTeamLabel(player?: PlayerRead): string {
    return this.isPlayerFromTeamA(player) ? 'Équipe A' : 'Équipe B';
  }

  getPlayerTeamName(player?: PlayerRead): string {
    return this.isPlayerFromTeamA(player)
      ? this.teamA?.name || 'Équipe A'
      : this.teamB?.name || 'Équipe B';
  }

  statValue(stats: StatsLike, keys: string[], fallback = 0): number {
    if (!stats) {
      return fallback;
    }

    const source = stats as unknown as Record<string, unknown>;

    for (const key of keys) {
      const value = source[key];
      if (value !== undefined && value !== null) {
        return Number(value);
      }
    }

    return fallback;
  }
}