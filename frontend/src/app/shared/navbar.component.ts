import { Component, input } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'sl-navbar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  template: `
    <nav class="bg-indigo-600 text-white shadow-lg">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
          <div class="flex items-center">
            <a routerLink="/dashboard" class="text-xl font-bold">
              SmartLuben
            </a>
          </div>
          <div class="hidden md:flex items-center space-x-4">
            <a
              routerLink="/dashboard"
              routerLinkActive="bg-indigo-700"
              class="px-3 py-2 rounded-md text-sm font-medium transition-colors"
            >
              Dashboard
            </a>
            <a
              routerLink="/mostrador"
              routerLinkActive="bg-indigo-700"
              class="px-3 py-2 rounded-md text-sm font-medium transition-colors"
            >
              Mostrador
            </a>
            <a
              routerLink="/productos"
              routerLinkActive="bg-indigo-700"
              class="px-3 py-2 rounded-md text-sm font-medium transition-colors"
            >
              Productos
            </a>
            <a
              routerLink="/movimientos"
              routerLinkActive="bg-indigo-700"
              class="px-3 py-2 rounded-md text-sm font-medium transition-colors"
            >
              Historial
            </a>
          </div>
        </div>
      </div>
    </nav>
  `,
  styles: ``,
})
export class NavbarComponent {
  readonly title = input('SmartLuben');
}