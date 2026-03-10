import { Component, Input } from '@angular/core';
import { CourtCell } from '../../models/match.model';

@Component({
  selector: 'app-court',
  standalone: true,
  templateUrl: './court.component.html',
  styleUrl: './court.component.scss',
})
export class CourtComponent {
  @Input() teamName = '';
  @Input() cells: CourtCell[] = [];

  getCell(x: number, y: number): CourtCell | undefined {
    return this.cells.find((c) => c.x === x && c.y === y);
  }
}