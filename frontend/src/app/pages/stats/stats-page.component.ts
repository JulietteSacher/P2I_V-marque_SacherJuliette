import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { forkJoin } from 'rxjs';
import { MatchesService } from '../../api/matches.service';
import { TeamsService } from '../../api/teams.service';
import { TeamStats } from '../../models/stats.model';
import { TeamRead } from '../../models/match.model';

@Component({
  selector: 'app-match-stats-page',
  standalone: true,
  templateUrl: './stats-page.component.html',
  styleUrl: './stats-page.component.scss',
})
export class MatchStatsPageComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private matchesService = inject(MatchesService);
  private teamsService = inject(TeamsService);

  matchId = 1;
  teamAId = 1;
  teamBId = 2;

  teamA?: TeamRead;
  teamB?: TeamRead;
  statsA?: TeamStats;
  statsB?: TeamStats;

  loading = true;
  error = '';

  ngOnInit(): void {
    this.matchId = Number(this.route.snapshot.paramMap.get('matchId')) || 1;
    this.loadStats();
  }

  loadStats(): void {
    forkJoin({
      teamA: this.teamsService.getTeam(this.teamAId),
      teamB: this.teamsService.getTeam(this.teamBId),
      statsA: this.matchesService.getTeamStats(this.matchId, this.teamAId),
      statsB: this.matchesService.getTeamStats(this.matchId, this.teamBId),
    }).subscribe({
      next: (data) => {
        this.teamA = data.teamA;
        this.teamB = data.teamB;
        this.statsA = data.statsA;
        this.statsB = data.statsB;
        this.loading = false;
      },
      error: () => {
        this.error = 'Impossible de charger les statistiques.';
        this.loading = false;
      },
    });
  }
}