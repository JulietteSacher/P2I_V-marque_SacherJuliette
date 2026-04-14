import { Routes } from '@angular/router';
import { MatchSetupPageComponent } from './pages/setup/setup-page.component';
import { MatchLivePageComponent } from './pages/match/match-page.component';
import { MatchStatsPageComponent } from './pages/stats/stats-page.component';

export const routes: Routes = [
  { path: '', component: MatchSetupPageComponent },
  { path: 'match/:matchId', component: MatchLivePageComponent },
  { path: 'match/:matchId/stats', component: MatchStatsPageComponent },
];