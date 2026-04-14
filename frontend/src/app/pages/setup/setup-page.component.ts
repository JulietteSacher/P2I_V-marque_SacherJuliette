import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { forkJoin, switchMap } from 'rxjs';

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

  teamAPlayers: SetupPlayer[] = Array.from({ length: 8 }, (_, i) => ({
    first_name: '',
    last_name: '',
    jersey_number: i + 1,
    role: 'R4',
  }));

  teamBPlayers: SetupPlayer[] = Array.from({ length: 8 }, (_, i) => ({
    first_name: '',
    last_name: '',
    jersey_number: i + 1,
    role: 'R4',
  }));

  lineupA = { p1: 1, p2: 2, p3: 3, p4: 4, p5: 5, p6: 6 };
  lineupB = { p1: 1, p2: 2, p3: 3, p4: 4, p5: 5, p6: 6 };

  private isPlayerFilled(player: SetupPlayer): boolean {
    return (
      player.first_name.trim() !== '' &&
      player.last_name.trim() !== '' &&
      player.role.trim() !== ''
    );
  }

  private getFilledPlayers(teamPlayers: SetupPlayer[]): SetupPlayer[] {
    return teamPlayers.filter((player) => this.isPlayerFilled(player));
  }

  private hasDuplicateJersey(teamPlayers: SetupPlayer[]): boolean {
    const numbers = teamPlayers.map((p) => Number(p.jersey_number));
    return new Set(numbers).size !== numbers.length;
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
      this.lineupA.p1,
      this.lineupA.p2,
      this.lineupA.p3,
      this.lineupA.p4,
      this.lineupA.p5,
      this.lineupA.p6,
    ];

    const lineupBValues = [
      this.lineupB.p1,
      this.lineupB.p2,
      this.lineupB.p3,
      this.lineupB.p4,
      this.lineupB.p5,
      this.lineupB.p6,
    ];

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

    const lineupAValid = lineupAValues.every((n) => jerseyA.includes(Number(n)));
    const lineupBValid = lineupBValues.every((n) => jerseyB.includes(Number(n)));

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

    const filledA = this.getFilledPlayers(this.teamAPlayers);
    const filledB = this.getFilledPlayers(this.teamBPlayers);

    this.teamsService.createTeam({ name: this.teamAName.trim() }).pipe(
      switchMap((teamA) =>
        this.teamsService.createTeam({ name: this.teamBName.trim() }).pipe(
          switchMap((teamB) =>
            forkJoin([
              ...filledA.map((p: SetupPlayer) =>
                this.playersService.createPlayer(teamA.id, p)
              ),
              ...filledB.map((p: SetupPlayer) =>
                this.playersService.createPlayer(teamB.id, p)
              ),
            ]).pipe(
              switchMap(() =>
                this.matchesService.createMatch({
                  team_a_id: teamA.id,
                  team_b_id: teamB.id,
                  sets_to_win: this.setsToWin,
                })
              ),
              switchMap((match) =>
                this.matchesService.startMatch(match.id).pipe(
                  switchMap(() =>
                    forkJoin([
                      this.matchesService.setInitialLineup(match.id, teamA.id, this.lineupA),
                      this.matchesService.setInitialLineup(match.id, teamB.id, this.lineupB),
                    ]).pipe(
                      switchMap(() =>
                        this.matchesService.setServingTeam(match.id, {
                          team_id: this.servingSide === 'A' ? teamA.id : teamB.id,
                        })
                      ),
                      switchMap(() => {
                        localStorage.setItem('currentMatchId', String(match.id));
                        localStorage.setItem('teamAId', String(teamA.id));
                        localStorage.setItem('teamBId', String(teamB.id));
                        return this.matchesService.getMatch(match.id);
                      })
                    )
                  )
                )
              )
            )
          )
        )
      )
    ).subscribe({
      next: (match) => {
        this.loading = false;
        this.success = 'Match créé avec succès.';
        this.router.navigate(['/match', match.id]);
      },
      error: (err) => {
        console.error(err);

        if (err?.error?.detail) {
          if (Array.isArray(err.error.detail)) {
            this.error = err.error.detail.map((e: { msg: string }) => e.msg).join(' | ');
          } else {
            this.error = String(err.error.detail);
          }
        } else if (err?.message) {
          this.error = err.message;
        } else {
          this.error = 'Erreur lors de la création du match.';
        }

        this.loading = false;
      },
    });
  }
  newMatch(): void {
    const currentMatchId = Number(localStorage.getItem('currentMatchId') || 0);

    this.error = '';
    this.success = '';

    if (!currentMatchId) {
      localStorage.removeItem('currentMatchId');
      localStorage.removeItem('teamAId');
      localStorage.removeItem('teamBId');
      this.success = 'Nouveau match prêt.';
      return;
    }

    this.matchesService.deleteMatch(currentMatchId).subscribe({
      next: () => {
        localStorage.removeItem('currentMatchId');
        localStorage.removeItem('teamAId');
        localStorage.removeItem('teamBId');

        this.teamAName = '';
        this.teamBName = '';
        this.setsToWin = 2;
        this.servingSide = 'A';

        this.teamAPlayers = Array.from({ length: 8 }, (_, i) => ({
          first_name: '',
          last_name: '',
          jersey_number: i + 1,
          role: 'R4',
        }));

        this.teamBPlayers = Array.from({ length: 8 }, (_, i) => ({
          first_name: '',
          last_name: '',
          jersey_number: i + 1,
          role: 'R4',
        }));

        this.lineupA = { p1: 1, p2: 2, p3: 3, p4: 4, p5: 5, p6: 6 };
        this.lineupB = { p1: 1, p2: 2, p3: 3, p4: 4, p5: 5, p6: 6 };

        this.success = 'Le match en cours a été supprimé. Tu peux en créer un nouveau.';
      },
      error: (err) => {
        console.error(err);
        this.error = err?.error?.detail || 'Impossible de supprimer le match en cours.';
      },
    });
  }
}