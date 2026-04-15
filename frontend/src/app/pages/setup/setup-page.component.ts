import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { forkJoin, map, switchMap } from 'rxjs';
import { Component, NgZone, inject } from '@angular/core';

import { TeamsService } from '../../api/teams.service';
import { PlayersService } from '../../api/players.service';
import { MatchesService } from '../../api/matches.service';

type SetupPlayer = {
  first_name: string;
  last_name: string;
  jersey_number: number;
  role: string;
};

@Component({
  selector: 'app-match-setup-page',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './setup-page.component.html',
  styleUrl: './setup-page.component.scss',
})
export class MatchSetupPageComponent {
  private teamsService = inject(TeamsService);
  private playersService = inject(PlayersService);
  private matchesService = inject(MatchesService);
  private router = inject(Router);

  loading = false;
  error = '';
  success = '';

  teamAName = '';
  teamBName = '';
  setsToWin = 2;
  servingSide: 'A' | 'B' = 'A';

  teamAColor = '#ef4444';
  teamBColor = '#22c55e';

  roles = ['PASSEUR', 'POINTU', 'R4', 'CENTRAL', 'LIBERO'];

  teamAPlayers: SetupPlayer[] = this.createEmptyPlayers();
  teamBPlayers: SetupPlayer[] = this.createEmptyPlayers();

  lineupA = { p1: 1, p2: 2, p3: 3, p4: 4, p5: 5, p6: 6 };
  lineupB = { p1: 1, p2: 2, p3: 3, p4: 4, p5: 5, p6: 6 };

  private createEmptyPlayers(): SetupPlayer[] {
    return Array.from({ length: 8 }, (_, i) => ({
      first_name: '',
      last_name: '',
      jersey_number: i + 1,
      role: 'R4',
    }));
  }

  private zone = inject(NgZone);

  private runInZone(fn: () => void): void {
    if (NgZone.isInAngularZone()) {
      fn();
      return;
    }
    this.zone.run(fn);
  }

  private resetForm(): void {
    this.teamAName = '';
    this.teamBName = '';
    this.setsToWin = 2;
    this.servingSide = 'A';
    this.teamAColor = '#ef4444';
    this.teamBColor = '#22c55e';
    this.teamAPlayers = this.createEmptyPlayers();
    this.teamBPlayers = this.createEmptyPlayers();
    this.lineupA = { p1: 1, p2: 2, p3: 3, p4: 4, p5: 5, p6: 6 };
    this.lineupB = { p1: 1, p2: 2, p3: 3, p4: 4, p5: 5, p6: 6 };
  }

  private clearLocalMatchState(): void {
    localStorage.removeItem('currentMatchId');
    localStorage.removeItem('teamAId');
    localStorage.removeItem('teamBId');
    localStorage.removeItem('teamAColor');
    localStorage.removeItem('teamBColor');
  }

  private normalizeColor(value: string | null | undefined, fallback: string): string {
    return /^#[0-9a-fA-F]{6}$/.test(value ?? '') ? String(value) : fallback;
  }

  private isPlayerFilled(player: SetupPlayer): boolean {
    return (
      player.first_name.trim() !== '' &&
      player.last_name.trim() !== '' &&
      player.role.trim() !== '' &&
      Number(player.jersey_number) > 0
    );
  }

  private getFilledPlayers(teamPlayers: SetupPlayer[]): SetupPlayer[] {
    return teamPlayers.filter((player) => this.isPlayerFilled(player));
  }

  private hasDuplicateJersey(teamPlayers: SetupPlayer[]): boolean {
    const numbers = teamPlayers.map((p) => Number(p.jersey_number));
    return new Set(numbers).size !== numbers.length;
  }

  private buildHttpErrorMessage(err: HttpErrorResponse): string {
    const detail = err?.error?.detail;

    if (err.status === 0) {
      return 'Backend inaccessible : vérifie que FastAPI est lancé sur http://127.0.0.1:8000';
    }

    if (
      err.status === 400 &&
      typeof detail === 'string' &&
      detail.includes('existe déjà')
    ) {
      return 'Une équipe avec ce nom existe déjà. La base n’a peut-être pas été vidée correctement.';
    }

    if (Array.isArray(detail)) {
      return detail.map((e: { msg?: string }) => e.msg || 'Erreur').join(' | ');
    }

    if (typeof detail === 'string' && detail.trim() !== '') {
      return detail;
    }

    if (err.message) {
      return err.message;
    }

    return 'Erreur lors de la requête.';
  }

  validateForm(): boolean {
    this.error = '';
    this.success = '';

    if (!this.teamAName.trim() || !this.teamBName.trim()) {
      this.error = 'Tu dois renseigner le nom des deux équipes.';
      return false;
    }

    const filledA = this.getFilledPlayers(this.teamAPlayers);
    const filledB = this.getFilledPlayers(this.teamBPlayers);

    if (filledA.length < 6 || filledB.length < 6) {
      this.error = 'Chaque équipe doit avoir au moins 6 joueurs remplis.';
      return false;
    }

    if (this.hasDuplicateJersey(filledA)) {
      this.error = 'L’équipe A contient des numéros de maillot en doublon.';
      return false;
    }

    if (this.hasDuplicateJersey(filledB)) {
      this.error = 'L’équipe B contient des numéros de maillot en doublon.';
      return false;
    }

    const lineupAValues = [
      Number(this.lineupA.p1),
      Number(this.lineupA.p2),
      Number(this.lineupA.p3),
      Number(this.lineupA.p4),
      Number(this.lineupA.p5),
      Number(this.lineupA.p6),
    ];

    const lineupBValues = [
      Number(this.lineupB.p1),
      Number(this.lineupB.p2),
      Number(this.lineupB.p3),
      Number(this.lineupB.p4),
      Number(this.lineupB.p5),
      Number(this.lineupB.p6),
    ];

    if (lineupAValues.some((n) => !n || n <= 0) || lineupBValues.some((n) => !n || n <= 0)) {
      this.error = 'Les positions initiales doivent toutes être renseignées avec des numéros valides.';
      return false;
    }

    if (new Set(lineupAValues).size !== 6) {
      this.error = 'Le lineup de l’équipe A contient des doublons.';
      return false;
    }

    if (new Set(lineupBValues).size !== 6) {
      this.error = 'Le lineup de l’équipe B contient des doublons.';
      return false;
    }

    const jerseyA = filledA.map((p) => Number(p.jersey_number));
    const jerseyB = filledB.map((p) => Number(p.jersey_number));

    const lineupAValid = lineupAValues.every((n) => jerseyA.includes(n));
    const lineupBValid = lineupBValues.every((n) => jerseyB.includes(n));

    if (!lineupAValid) {
      this.error =
        'Le lineup de l’équipe A contient un numéro qui n’existe pas dans les joueurs saisis.';
      return false;
    }

    if (!lineupBValid) {
      this.error =
        'Le lineup de l’équipe B contient un numéro qui n’existe pas dans les joueurs saisis.';
      return false;
    }

    return true;
  }

  createMatchFlow(): void {
    if (!this.validateForm()) {
      return;
    }

    this.loading = true;
    this.error = '';
    this.success = '';
    this.clearLocalMatchState();

    this.teamAColor = this.normalizeColor(this.teamAColor, '#ef4444');
    this.teamBColor = this.normalizeColor(this.teamBColor, '#22c55e');

    const filledA = this.getFilledPlayers(this.teamAPlayers);
    const filledB = this.getFilledPlayers(this.teamBPlayers);

    this.matchesService
      .resetAll()
      .pipe(
        switchMap(() => this.teamsService.createTeam({ name: this.teamAName.trim() })),
        switchMap((teamA) =>
          this.teamsService.createTeam({ name: this.teamBName.trim() }).pipe(
            map((teamB) => ({ teamA, teamB }))
          )
        ),
        switchMap(({ teamA, teamB }) =>
          forkJoin([
            ...filledA.map((p) => this.playersService.createPlayer(teamA.id, p)),
            ...filledB.map((p) => this.playersService.createPlayer(teamB.id, p)),
          ]).pipe(map(() => ({ teamA, teamB })))
        ),
        switchMap(({ teamA, teamB }) =>
          this.matchesService.createMatch({
            team_a_id: teamA.id,
            team_b_id: teamB.id,
            sets_to_win: this.setsToWin,
          }).pipe(map((match) => ({ teamA, teamB, match })))
        ),
        switchMap(({ teamA, teamB, match }) =>
          this.matchesService.startMatch(match.id).pipe(map(() => ({ teamA, teamB, match })))
        ),
        switchMap(({ teamA, teamB, match }) =>
          forkJoin([
            this.matchesService.setInitialLineup(match.id, teamA.id, this.lineupA),
            this.matchesService.setInitialLineup(match.id, teamB.id, this.lineupB),
          ]).pipe(map(() => ({ teamA, teamB, match })))
        ),
        switchMap(({ teamA, teamB, match }) =>
          this.matchesService.setServingTeam(match.id, {
            team_id: this.servingSide === 'A' ? teamA.id : teamB.id,
          }).pipe(map(() => ({ teamA, teamB, match })))
        )
      )
      .subscribe({
        next: ({ teamA, teamB, match }) =>
          this.runInZone(() => {
            localStorage.setItem('currentMatchId', String(match.id));
            localStorage.setItem('teamAId', String(teamA.id));
            localStorage.setItem('teamBId', String(teamB.id));
            localStorage.setItem('teamAColor', this.teamAColor);
            localStorage.setItem('teamBColor', this.teamBColor);

            this.loading = false;
            this.success = 'Match créé avec succès.';
            void this.router.navigate(['/match', match.id], { replaceUrl: true });
          }),
        error: (err: HttpErrorResponse) =>
          this.runInZone(() => {
            console.error(err);
            this.error = this.buildHttpErrorMessage(err);
            this.loading = false;
          }),
      });
  }

  newMatch(): void {
    this.loading = true;
    this.error = '';
    this.success = '';

    this.matchesService.resetAll().subscribe({
      next: () =>
        this.runInZone(() => {
          this.clearLocalMatchState();
          this.resetForm();
          this.success = 'Toutes les données ont été supprimées. Tu peux créer un nouveau match.';
          this.loading = false;
        }),
      error: (err: HttpErrorResponse) =>
        this.runInZone(() => {
          console.error(err);
          this.error = this.buildHttpErrorMessage(err);
          this.loading = false;
        }),
    });
  }
}