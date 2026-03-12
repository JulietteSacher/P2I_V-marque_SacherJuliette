import { Component, Input } from '@angular/core';
import { CourtCell } from '../../models/match.model';

@Component({
  selector: 'app-court',
  standalone: true,
  templateUrl: './court.component.html',
  styleUrl: './court.component.scss',
})
export class CourtComponent {
  @Input() teamAName = 'Locaux';
  @Input() teamBName = 'Visiteurs';
  @Input() cellsA: CourtCell[] = [];
  @Input() cellsB: CourtCell[] = [];

  getCell(cells: CourtCell[], position: number): CourtCell | undefined {
    return cells.find((c) => c.position === position);
  }

  leftTopPositions = [4, 3, 2];
  leftBottomPositions = [5, 6, 1];

  rightTopPositions = [2, 3, 4];
  rightBottomPositions = [1, 6, 5];
}