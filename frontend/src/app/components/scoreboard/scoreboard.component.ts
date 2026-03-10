import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-scoreboard',
  standalone: true,
  templateUrl: './scoreboard.component.html',
  styleUrl: './scoreboard.component.scss',
})
export class ScoreboardComponent {
  @Input() teamAName = 'Équipe A';
  @Input() teamBName = 'Équipe B';
  @Input() scoreA = 0;
  @Input() scoreB = 0;
  @Input() setNumber = 1;
  @Input() servingTeamId?: number | null = null;
  @Input() teamAId?: number;
  @Input() teamBId?: number;
}