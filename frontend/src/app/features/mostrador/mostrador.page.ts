import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NavbarComponent } from '../../shared/navbar.component';
import { MostradorGridComponent } from './mostrador-grid.component';

@Component({
  selector: 'sl-mostrador-page',
  standalone: true,
  imports: [
    CommonModule,
    NavbarComponent,
    MostradorGridComponent,
  ],
  template: `
    <div class="min-h-screen bg-gray-50">
      <sl-navbar />
      <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div class="mb-8">
          <h1 class="text-3xl font-bold text-gray-900">Mostrador</h1>
          <p class="text-gray-500 mt-1">Gestión de espacios de exhibición</p>
        </div>

        <sl-mostrador-grid />
      </main>
    </div>
  `,
  styles: ``,
})
export class MostradorPageComponent {}
