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
import { forkJoin } from 'rxjs';

import { MatchesService } from '../../api/matches.service';
import { PlayersService } from '../../api/players.service';
import { CourtComponent } from '../../components/court/court.component';
import { ScoreboardComponent } from '../../components/scoreboard/scoreboard.component';
import { PlayerRead } from '../../models/player.model';
import {
  CourtCell,
  CourtView,
  FinishedSetRead,
  MatchRead,
  SetRead,
  TeamRead,
} from '../../models/match.model';

@Component({
  selector: 'app-match-live-page',
  standalone: true,
  imports: [CommonModule, FormsModule, CourtComponent, ScoreboardComponent],
  templateUrl: './match-page.component.html',
  styleUrl: './match-page.component.scss',
})
export class MatchLivePageComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private matchesService = inject(MatchesService);
  private playersService = inject(PlayersService);
  private zone = inject(NgZone);
  private cdr = inject(ChangeDetectorRef);
  private destroyRef = inject(DestroyRef);

  private loadRequestId = 0;

  matchId = 0;

  match?: MatchRead;
  currentSet?: SetRead;
  teamA?: TeamRead;
  teamB?: TeamRead;
  courtA?: CourtView;
  courtB?: CourtView;

  teamASetsWon = 0;
  teamBSetsWon = 0;
  finishedSets: FinishedSetRead[] = [];

  orderedCourtA: CourtCell[] = [];
  orderedCourtB: CourtCell[] = [];

  allPlayersA: PlayerRead[] = [];
  allPlayersB: PlayerRead[] = [];
  benchA: PlayerRead[] = [];
  benchB: PlayerRead[] = [];
  playersLoaded = false;

  selectedOutA?: number;
  selectedInA?: number;
  selectedOutB?: number;
  selectedInB?: number;

  teamAColor = '#ef4444';
  teamBColor = '#22c55e';

  loading = true;
  refreshing = false;
  hasLoadedOnce = false;
  actionPending = false;

  fatalError = '';
  inlineError = '';
  loadingMessage = 'Chargement du match...';

  nextSetPending = false;
  showNextSetPrompt = false;
  dismissedNextSetForSetNumber?: number;
  startingNextSet = false;

  ngOnInit(): void {
    this.route.paramMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      const routeId = Number(params.get('matchId'));
      const localId = Number(localStorage.getItem('currentMatchId') || 0);
      const nextMatchId = routeId || localId;

      if (nextMatchId !== this.matchId) {
        this.resetForMatchChange();
      }

      this.matchId = nextMatchId;
      this.teamAColor = this.normalizeColor(localStorage.getItem('teamAColor'), '#ef4444');
      this.teamBColor = this.normalizeColor(localStorage.getItem('teamBColor'), '#22c55e');

      if (!this.matchId) {
        this.loading = false;
        this.fatalError = 'Aucun match en cours. Crée d’abord un match depuis la feuille de match.';
        this.pushUi();
        return;
      }

      this.loadPage(true);
    });
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

  private normalizeColor(value: string | null | undefined, fallback: string): string {
    return /^#[0-9a-fA-F]{6}$/.test(value ?? '') ? String(value) : fallback;
  }

  private resetForMatchChange(): void {
    this.match = undefined;
    this.currentSet = undefined;
    this.teamA = undefined;
    this.teamB = undefined;
    this.courtA = undefined;
    this.courtB = undefined;

    this.teamASetsWon = 0;
    this.teamBSetsWon = 0;
    this.finishedSets = [];

    this.orderedCourtA = [];
    this.orderedCourtB = [];

    this.allPlayersA = [];
    this.allPlayersB = [];
    this.benchA = [];
    this.benchB = [];
    this.playersLoaded = false;

    this.selectedOutA = undefined;
    this.selectedInA = undefined;
    this.selectedOutB = undefined;
    this.selectedInB = undefined;

    this.loading = true;
    this.refreshing = false;
    this.hasLoadedOnce = false;
    this.actionPending = false;

    this.fatalError = '';
    this.inlineError = '';
    this.loadingMessage = 'Chargement du match...';

    this.nextSetPending = false;
    this.showNextSetPrompt = false;
    this.dismissedNextSetForSetNumber = undefined;
    this.startingNextSet = false;
  }

  private updateNextSetState(): void {
    this.nextSetPending =
      this.match?.status === 'running' &&
      this.currentSet?.status === 'not_started' &&
      (this.finishedSets?.length ?? 0) > 0;

    if (!this.nextSetPending || !this.currentSet) {
      this.showNextSetPrompt = false;
      this.dismissedNextSetForSetNumber = undefined;
      return;
    }

    this.showNextSetPrompt =
      this.dismissedNextSetForSetNumber !== this.currentSet.set_number;
  }

  get lastFinishedSet(): FinishedSetRead | undefined {
    return this.finishedSets.length ? this.finishedSets[this.finishedSets.length - 1] : undefined;
  }

  get lastWinnerName(): string {
    if (!this.lastFinishedSet || !this.teamA || !this.teamB) {
      return 'Une équipe';
    }

    if (this.lastFinishedSet.winner_team_id === this.teamA.id) {
      return this.teamA.name;
    }

    if (this.lastFinishedSet.winner_team_id === this.teamB.id) {
      return this.teamB.name;
    }

    return 'Une équipe';
  }

  private sortCourtCells(cells: CourtCell[]): CourtCell[] {
    return [...cells].sort((a, b) => a.position - b.position);
  }

  private computeBench(): void {
    const onCourtA = new Set((this.courtA?.cells || []).map((c) => c.jersey_number));
    const onCourtB = new Set((this.courtB?.cells || []).map((c) => c.jersey_number));

    this.benchA = this.allPlayersA.filter((player) => !onCourtA.has(player.jersey_number));
    this.benchB = this.allPlayersB.filter((player) => !onCourtB.has(player.jersey_number));
  }

  private applyLiveData(): void {
    this.orderedCourtA = this.sortCourtCells(this.courtA?.cells || []);
    this.orderedCourtB = this.sortCourtCells(this.courtB?.cells || []);
    this.computeBench();
    this.updateNextSetState();
  }

  private finishSuccessfulLoad(): void {
    this.loading = false;
    this.refreshing = false;
    this.actionPending = false;
    this.startingNextSet = false;
    this.hasLoadedOnce = true;
    this.fatalError = '';
    this.inlineError = '';
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

  private handleLoadError(err: any, initial: boolean): void {
    const message = this.buildErrorMessage(err, 'Impossible de charger les données du match.');

    this.loading = false;
    this.refreshing = false;
    this.actionPending = false;
    this.startingNextSet = false;

    if (!this.hasLoadedOnce || initial) {
      this.fatalError = message;
    } else {
      this.inlineError = message;
    }
  }

  loadPage(initial = false): void {
    if (!this.matchId) {
      this.loading = false;
      this.fatalError = 'Aucun match en cours.';
      this.pushUi();
      return;
    }

    const requestId = ++this.loadRequestId;

    if (!this.hasLoadedOnce || initial) {
      this.loading = true;
      this.loadingMessage = 'Chargement du match...';
      this.fatalError = '';
    } else {
      this.refreshing = true;
    }

    this.matchesService
      .getMatchLive(this.matchId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (live) =>
          this.runInUi(() => {
            if (requestId !== this.loadRequestId) {
              return;
            }

            const previousTeamAId = this.teamA?.id;
            const previousTeamBId = this.teamB?.id;

            this.match = live.match;
            this.currentSet = live.current_set;
            this.teamA = live.team_a;
            this.teamB = live.team_b;
            this.courtA = live.court_a;
            this.courtB = live.court_b;
            this.teamASetsWon = live.team_a_sets_won ?? 0;
            this.teamBSetsWon = live.team_b_sets_won ?? 0;
            this.finishedSets = live.finished_sets ?? [];

            localStorage.setItem('currentMatchId', String(this.match.id));
            localStorage.setItem('teamAId', String(this.teamA.id));
            localStorage.setItem('teamBId', String(this.teamB.id));

            const mustReloadPlayers =
              !this.playersLoaded ||
              previousTeamAId !== this.teamA.id ||
              previousTeamBId !== this.teamB.id;

            if (!mustReloadPlayers) {
              this.applyLiveData();
              this.finishSuccessfulLoad();
              return;
            }

            forkJoin({
              playersA: this.playersService.getPlayersByTeam(this.teamA.id),
              playersB: this.playersService.getPlayersByTeam(this.teamB.id),
            })
              .pipe(takeUntilDestroyed(this.destroyRef))
              .subscribe({
                next: ({ playersA, playersB }) =>
                  this.runInUi(() => {
                    if (requestId !== this.loadRequestId) {
                      return;
                    }

                    this.allPlayersA = playersA;
                    this.allPlayersB = playersB;
                    this.playersLoaded = true;

                    this.applyLiveData();
                    this.finishSuccessfulLoad();
                  }),
                error: (err) =>
                  this.runInUi(() => {
                    if (requestId !== this.loadRequestId) {
                      return;
                    }
                    this.handleLoadError(err, initial);
                  }),
              });
          }),
        error: (err) =>
          this.runInUi(() => {
            if (requestId !== this.loadRequestId) {
              return;
            }
            this.handleLoadError(err, initial);
          }),
      });
  }

  hideNextSetPrompt(): void {
    if (this.currentSet) {
      this.dismissedNextSetForSetNumber = this.currentSet.set_number;
    }
    this.showNextSetPrompt = false;
    this.inlineError = '';
    this.pushUi();
  }

  startNextSet(): void {
    if (!this.matchId || this.actionPending || this.startingNextSet || !this.nextSetPending) {
      return;
    }

    this.actionPending = true;
    this.startingNextSet = true;
    this.inlineError = '';

    this.matchesService
      .startNextSet(this.matchId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () =>
          this.runInUi(() => {
            this.nextSetPending = false;
            this.showNextSetPrompt = false;
            this.dismissedNextSetForSetNumber = undefined;
            this.loadPage(false);
          }),
        error: (err) =>
          this.runInUi(() => {
            this.actionPending = false;
            this.startingNextSet = false;
            this.inlineError = this.buildErrorMessage(
              err,
              'Impossible de lancer le set suivant.'
            );
          }),
      });
  }

  swapA(): void {
    if (!this.teamA || !this.selectedOutA || !this.selectedInA || this.actionPending) {
      return;
    }

    this.actionPending = true;
    this.inlineError = '';

    this.matchesService
      .swapPlayers(this.matchId, this.teamA.id, {
        player_out_id: this.selectedOutA,
        player_in_id: this.selectedInA,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () =>
          this.runInUi(() => {
            this.selectedOutA = undefined;
            this.selectedInA = undefined;
            this.loadPage(false);
          }),
        error: (err) =>
          this.runInUi(() => {
            this.actionPending = false;
            this.inlineError = this.buildErrorMessage(
              err,
              'Erreur lors du changement de joueur.'
            );
          }),
      });
  }

  swapB(): void {
    if (!this.teamB || !this.selectedOutB || !this.selectedInB || this.actionPending) {
      return;
    }

    this.actionPending = true;
    this.inlineError = '';

    this.matchesService
      .swapPlayers(this.matchId, this.teamB.id, {
        player_out_id: this.selectedOutB,
        player_in_id: this.selectedInB,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () =>
          this.runInUi(() => {
            this.selectedOutB = undefined;
            this.selectedInB = undefined;
            this.loadPage(false);
          }),
        error: (err) =>
          this.runInUi(() => {
            this.actionPending = false;
            this.inlineError = this.buildErrorMessage(
              err,
              'Erreur lors du changement de joueur.'
            );
          }),
      });
  }

  addAction(playerId: number, actionType: string): void {
    if (!this.matchId) {
      return;
    }

    if (this.loading || this.refreshing || this.actionPending || this.startingNextSet) {
      return;
    }

    if (!this.currentSet) {
      this.inlineError = 'Aucun set courant disponible.';
      this.pushUi();
      return;
    }

    if (this.currentSet.status !== 'running') {
      this.inlineError = 'Le set n’est pas en cours.';
      this.pushUi();
      return;
    }

    if (!this.currentSet.serving_team_id) {
      this.inlineError = 'Le service n’est pas initialisé pour ce set.';
      this.pushUi();
      return;
    }

    if (this.nextSetPending) {
      this.inlineError = 'Le set est terminé. Lance d’abord le set suivant.';
      this.pushUi();
      return;
    }

    this.actionPending = true;
    this.inlineError = '';

    this.matchesService
      .addAction(this.matchId, {
        player_id: playerId,
        action_type: actionType,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () =>
          this.runInUi(() => {
            this.loadPage(false);
          }),
        error: (err) =>
          this.runInUi(() => {
            this.actionPending = false;
            this.inlineError = this.buildErrorMessage(
              err,
              'Erreur lors de l’ajout de l’action.'
            );
          }),
      });
  }

  getPlayerByJersey(team: 'A' | 'B', jersey: number): PlayerRead | undefined {
    const source = team === 'A' ? this.allPlayersA : this.allPlayersB;
    return source.find((player) => player.jersey_number === jersey);
  }

  get isMatchFinished(): boolean {
  return this.match?.status === 'finished';
}

  get matchWinnerName(): string {
    if (!this.teamA || !this.teamB) {
      return 'Une équipe';
    }

    if (this.teamASetsWon > this.teamBSetsWon) {
      return this.teamA.name;
    }

    if (this.teamBSetsWon > this.teamASetsWon) {
      return this.teamB.name;
    }

    return 'Égalité impossible';
  }

  get matchScoreSummary(): string {
    return `${this.teamASetsWon} - ${this.teamBSetsWon}`;
  }

  get isDecidingSet(): boolean {
    if (!this.match || !this.currentSet) {
      return false;
    }

    return this.currentSet.set_number === 2 * this.match.sets_to_win - 1;
  }

  get currentSetTargetPoints(): number {
    return this.isDecidingSet ? 15 : 25;
  }

  refresh(): void {
    if (this.actionPending || this.startingNextSet) {
      return;
    }

    this.inlineError = '';
    this.loadPage(false);
  }
}