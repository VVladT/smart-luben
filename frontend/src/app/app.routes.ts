import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/dashboard',
    pathMatch: 'full',
  },
  {
    path: 'dashboard',
    loadComponent: () => import('./features/dashboard/dashboard.page').then((m) => m.DashboardPageComponent),
  },
  {
    path: 'mostrador',
    loadComponent: () => import('./features/mostrador/mostrador.page').then((m) => m.MostradorPageComponent),
  },
  {
    path: 'productos',
    loadComponent: () => import('./features/productos/productos.page').then((m) => m.ProductosPageComponent),
  },
  {
    path: 'movimientos',
    loadComponent: () => import('./features/movimientos/movimientos.page').then((m) => m.MovimientosPageComponent),
  },
  {
    path: '**',
    redirectTo: '/dashboard',
  },
];