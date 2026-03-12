import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { MatchesService } from '../../api/matches.service';
import { TeamsService } from '../../api/teams.service';
import { CourtComponent } from '../../components/court/court.component';
import {
  CourtView,
  MatchRead,
  SetRead,
  TeamRead,
} from '../../models/match.model';

@Component({
  selector: 'app-match-live-page',
  standalone: true,
  imports: [CourtComponent, RouterLink],
  templateUrl: './match-page.component.html',
  styleUrl: './match-page.component.scss',
})
export class MatchLivePageComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private matchesService = inject(MatchesService);
  private teamsService = inject(TeamsService);

  matchId = 1;

  match?: MatchRead;
  currentSet?: SetRead;
  teamA?: TeamRead;
  teamB?: TeamRead;
  courtA?: CourtView;
  courtB?: CourtView;

  loading = true;
  error = '';

  ngOnInit(): void {
    this.matchId = Number(this.route.snapshot.paramMap.get('matchId')) || 1;
    this.loadPage();
  }

  loadPage(): void {
    this.loading = true;
    this.error = '';

    this.matchesService.getMatch(this.matchId).subscribe({
      next: (match) => {
        this.match = match;

        const teamAId = match.team_a_id;
        const teamBId = match.team_b_id;

        forkJoin({
          currentSet: this.matchesService.getCurrentSet(this.matchId),
          teamA: this.teamsService.getTeam(teamAId),
          teamB: this.teamsService.getTeam(teamBId),
          courtA: this.matchesService.getCourtView(this.matchId, teamAId),
          courtB: this.matchesService.getCourtView(this.matchId, teamBId),
        }).subscribe({
          next: (data) => {
            this.currentSet = data.currentSet;
            this.teamA = data.teamA;
            this.teamB = data.teamB;
            this.courtA = data.courtA;
            this.courtB = data.courtB;
            this.loading = false;
          },
          error: (err) => {
            console.error('Erreur chargement détails match :', err);
            this.error = 'Impossible de charger les données du match.';
            this.loading = false;
          },
        });
      },
      error: (err) => {
        console.error('Erreur chargement match :', err);
        this.error = 'Impossible de charger les informations du match.';
        this.loading = false;
      },
    });
  }

  refresh(): void {
    this.loadPage();
  }
}