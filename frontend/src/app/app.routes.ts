import { Routes } from '@angular/router';
import { MatchLivePageComponent } from './pages/match/match-page.component';
import { MatchStatsPageComponent } from './pages/stats/stats-page.component';

export const routes: Routes = [
  { path: '', redirectTo: 'match/1', pathMatch: 'full' },
  { path: 'match/:matchId', component: MatchLivePageComponent },
  { path: 'match/:matchId/stats', component: MatchStatsPageComponent },
];
