import { Component, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { rxResource } from '@angular/core/rxjs-interop';
import { DashboardService } from '../../core/services/dashboard.service';
import { DashboardResumen } from '../../core/api/generated/types';
import { ErrorMessageComponent } from '../../shared/error-message.component';
import { NavbarComponent } from '../../shared/navbar.component';

@Component({
  selector: 'sl-dashboard-page',
  standalone: true,
  imports: [CommonModule, ErrorMessageComponent, NavbarComponent],
  template: `
    <div class="min-h-screen bg-gray-50">
      <sl-navbar />
      <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div class="mb-8">
          <h1 class="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p class="text-gray-500 mt-1">Resumen del estado del mostrador</p>
        </div>

        @if (errorMessage()) {
          <sl-error-message [message]="errorMessage()" />
        }

        @if (dashboardResource.isLoading()) {
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            @for (i of [1,2,3,4]; track i) {
              <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 animate-pulse">
                <div class="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
                <div class="h-12 bg-gray-200 rounded w-3/4"></div>
              </div>
            }
          </div>
        } @else {
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm font-medium text-gray-500">Total Espacios</p>
                  <p class="text-3xl font-bold text-gray-900 mt-1">{{ dashboard()?.total_espacios ?? 0 }}</p>
                </div>
                <div class="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
                  <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                  </svg>
                </div>
              </div>
            </div>

            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm font-medium text-gray-500">Espacios Libres</p>
                  <p class="text-3xl font-bold text-gray-900 mt-1">{{ dashboard()?.espacios_libres ?? 0 }}</p>
                </div>
                <div class="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center">
                  <svg class="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                  </svg>
                </div>
              </div>
            </div>

            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm font-medium text-gray-500">Espacios Ocupados</p>
                  <p class="text-3xl font-bold text-gray-900 mt-1">{{ dashboard()?.espacios_ocupados ?? 0 }}</p>
                </div>
                <div class="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
                  <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              </div>
            </div>

            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-sm font-medium text-gray-500">Productos Activos</p>
                  <p class="text-3xl font-bold text-gray-900 mt-1">{{ dashboard()?.productos_activos ?? 0 }}</p>
                </div>
                <div class="w-12 h-12 bg-indigo-100 rounded-xl flex items-center justify-center">
                  <svg class="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                  </svg>
                </div>
              </div>
            </div>
          </div>

          <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div class="flex items-center justify-between mb-4">
              <h2 class="text-lg font-semibold text-gray-900">Accesos rápidos</h2>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <a
                routerLink="/mostrador"
                class="block p-6 bg-gray-50 border border-gray-200 rounded-xl hover:border-indigo-300 hover:bg-indigo-50 transition-colors"
              >
                <div class="flex items-center space-x-4">
                  <div class="w-12 h-12 bg-indigo-100 rounded-xl flex items-center justify-center">
                    <svg class="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                    </svg>
                  </div>
                  <div>
                    <h3 class="font-medium text-gray-900">Ver Mostrador</h3>
                    <p class="text-sm text-gray-500">Gestionar espacios y reposiciones</p>
                  </div>
                </div>
              </a>
              <a
                routerLink="/productos"
                class="block p-6 bg-gray-50 border border-gray-200 rounded-xl hover:border-indigo-300 hover:bg-indigo-50 transition-colors"
              >
                <div class="flex items-center space-x-4">
                  <div class="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
                    <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                    </svg>
                  </div>
                  <div>
                    <h3 class="font-medium text-gray-900">Gestionar Productos</h3>
                    <p class="text-sm text-gray-500">Crear, editar y activar/desactivar productos</p>
                  </div>
                </div>
              </a>
              <a
                routerLink="/movimientos"
                class="block p-6 bg-gray-50 border border-gray-200 rounded-xl hover:border-indigo-300 hover:bg-indigo-50 transition-colors"
              >
                <div class="flex items-center space-x-4">
                  <div class="w-12 h-12 bg-orange-100 rounded-xl flex items-center justify-center">
                    <svg class="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                    </svg>
                  </div>
                  <div>
                    <h3 class="font-medium text-gray-900">Ver Historial</h3>
                    <p class="text-sm text-gray-500">Movimientos de reposición y salida</p>
                  </div>
                </div>
              </a>
            </div>
          </div>
        }
      </main>
    </div>
  `,
  styles: ``,
})
export class DashboardPageComponent {
  private dashboardService = inject(DashboardService);

  readonly dashboardResource = rxResource({
    params: () => ({}),
    stream: () => this.dashboardService.getResumen(),
  });

  readonly dashboard = computed(() => {
    return this.dashboardResource.hasValue() ? this.dashboardResource.value() : null;
  });
  readonly errorMessage = signal<string | null>(null);

  getErrorMessage(error: unknown): string {
    if (error && typeof error === 'object' && 'error' in error) {
      const err = error as { error?: { detail?: string | { msg: string }[] } };
      if (err.error?.detail) {
        if (Array.isArray(err.error.detail)) {
          return err.error.detail.map((d) => d.msg).join(', ');
        }
        return err.error.detail;
      }
    }
    return 'Error al comunicarse con el servidor';
  }
}