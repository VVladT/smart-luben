import { Component, input, output, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { EspacioConProductoResponse, EstadoEspacio } from '../../core/api/generated/types';

@Component({
  selector: 'sl-espacio-card',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div
      class="rounded-xl p-4 transition-all duration-200 border-2"
      [class]="cardClasses()"
      role="button"
      tabindex="0"
    >
      <div class="flex items-start justify-between mb-3">
        <div>
          <span class="text-xs font-mono text-gray-500 uppercase tracking-wide">
            {{ espacio().codigo }}
          </span>
          <p class="text-xs text-gray-400 mt-1">{{ espacio().ubicacion }}</p>
        </div>
        <span
          class="px-2 py-1 text-xs font-semibold rounded-full"
          [class]="badgeClasses()"
        >
          {{ estadoLabel() }}
        </span>
      </div>

      @if (espacio().estado === 'ocupado' && espacio().producto_actual) {
        <div class="mb-3">
          @if (espacio().producto_actual!.imagen_url) {
            <img
              [src]="espacio().producto_actual!.imagen_url"
              [alt]="espacio().producto_actual!.nombre"
              class="w-full h-32 object-cover rounded-lg mb-2"
              loading="lazy"
            />
          }
          <h3 class="font-medium text-gray-900 truncate">{{ espacio().producto_actual!.nombre }}</h3>
          <p class="text-xs text-gray-500">{{ espacio().producto_actual!.categoria }}</p>
        </div>
      } @else {
        <div class="h-32 flex items-center justify-center bg-gray-50 rounded-lg mb-3">
          <svg
            class="w-12 h-12 text-gray-300"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.5"
              d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
            />
          </svg>
        </div>
        <p class="text-center text-gray-400 text-sm mb-3">Espacio libre</p>
      }

      <div class="flex space-x-2">
        @if (espacio().estado === 'libre') {
          <button
            (click)="reponer.emit(espacio())"
            class="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white py-2 px-3 rounded-lg text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
          >
            Reponer
          </button>
        } @else {
          <button
            (click)="liberar.emit(espacio())"
            class="flex-1 bg-red-600 hover:bg-red-700 text-white py-2 px-3 rounded-lg text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
          >
            Liberar
          </button>
        }
      </div>
    </div>
  `,
  styles: ``,
})
export class EspacioCardComponent {
  readonly espacio = input.required<EspacioConProductoResponse>();
  readonly reponer = output<EspacioConProductoResponse>();
  readonly liberar = output<EspacioConProductoResponse>();

  readonly estadoLabel = computed(() => {
    return this.espacio().estado === 'libre' ? 'LIBRE' : 'OCUPADO';
  });

  readonly cardClasses = computed(() => {
    const estado = this.espacio().estado;
    return estado === 'libre'
      ? 'bg-gray-50 border-gray-200 hover:border-gray-300'
      : 'bg-green-50 border-green-200 hover:border-green-300';
  });

  readonly badgeClasses = computed(() => {
    const estado = this.espacio().estado;
    return estado === 'libre' ? 'bg-gray-100 text-gray-700' : 'bg-green-100 text-green-700';
  });
}