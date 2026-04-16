import { Component, Input } from '@angular/core';
import { FinishedSetRead } from '../../models/match.model';
import { NgStyle } from '@angular/common';

@Component({
  selector: 'app-scoreboard',
  standalone: true,
  imports: [NgStyle],
  templateUrl: './scoreboard.component.html',
  styleUrl: './scoreboard.component.scss',
})
export class ScoreboardComponent {
  @Input() teamAName = 'Équipe A';
  @Input() teamBName = 'Équipe B';
  @Input() scoreA = 0;
  @Input() scoreB = 0;
  @Input() setNumber = 1;
  @Input() teamASetsWon = 0;
  @Input() teamBSetsWon = 0;
  @Input() finishedSets: FinishedSetRead[] = [];
  @Input() matchStatus = 'En cours';
  @Input() servingTeamId?: number | null = null;
  @Input() teamAId?: number;
  @Input() teamBId?: number;
  @Input() teamAColor = '#ef4444';
  @Input() teamBColor = '#22c55e';

  isServing(side: 'A' | 'B'): boolean {
    if (side === 'A') {
      return this.servingTeamId === this.teamAId;
    }
    return this.servingTeamId === this.teamBId;
  }

  teamColor(side: 'A' | 'B'): string {
    return side === 'A' ? this.teamAColor : this.teamBColor;
  }

  teamTextColor(side: 'A' | 'B'): string {
    const hex = this.teamColor(side).replace('#', '');
    const normalized =
      hex.length === 3 ? hex.split('').map((char) => char + char).join('') : hex;

    const r = parseInt(normalized.slice(0, 2), 16);
    const g = parseInt(normalized.slice(2, 4), 16);
    const b = parseInt(normalized.slice(4, 6), 16);
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

    return luminance > 0.65 ? '#0f172a' : '#ffffff';
  }

  isSetWonByTeamA(setItem: FinishedSetRead): boolean {
    return !!this.teamAId && setItem.winner_team_id === this.teamAId;
  }

  isSetWonByTeamB(setItem: FinishedSetRead): boolean {
    return !!this.teamBId && setItem.winner_team_id === this.teamBId;
  }

  getSetChipStyle(setItem: FinishedSetRead): Record<string, string> {
    if (this.isSetWonByTeamA(setItem)) {
      return {
        background: `${this.teamAColor}22`,
        border: `1px solid ${this.teamAColor}66`,
        color: this.teamTextColor('A'),
      };
    }

    if (this.isSetWonByTeamB(setItem)) {
      return {
        background: `${this.teamBColor}22`,
        border: `1px solid ${this.teamBColor}66`,
        color: this.teamTextColor('B'),
      };
    }

    return {
      background: 'rgba(148, 163, 184, 0.18)',
      border: '1px solid rgba(148, 163, 184, 0.28)',
      color: '#f8fafc',
    };
  }
}