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
  @Input() teamAColor = '#ef4444';
  @Input() teamBColor = '#22c55e';

  leftBackColumn = [5, 6, 1];
  leftFrontColumn = [4, 3, 2];

  rightFrontColumn = [2, 3, 4];
  rightBackColumn = [1, 6, 5];

  getCell(cells: CourtCell[], position: number): CourtCell | undefined {
    return cells.find((cell) => cell.position === position);
  }

  textColor(hexColor: string): string {
    const hex = hexColor.replace('#', '');
    const normalized = hex.length === 3
      ? hex.split('').map((char) => char + char).join('')
      : hex;

    const r = parseInt(normalized.slice(0, 2), 16);
    const g = parseInt(normalized.slice(2, 4), 16);
    const b = parseInt(normalized.slice(4, 6), 16);
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

    return luminance > 0.65 ? '#0f172a' : '#ffffff';
  }
}
