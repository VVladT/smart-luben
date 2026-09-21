import { Component, input, output, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { LoadingSpinnerComponent } from '../../shared/loading-spinner.component';

@Component({
  selector: 'sl-modal-confirmar',
  standalone: true,
  imports: [CommonModule, LoadingSpinnerComponent],
  template: `
    @if (isOpen()) {
      <div class="fixed inset-0 z-50 overflow-y-auto" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
        <div class="flex min-h-full items-center justify-center p-4">
          <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true" (click)="cancel.emit()"></div>
          <div class="relative bg-white rounded-xl shadow-xl max-w-md w-full transform transition-all">
            <div class="px-6 py-4 border-b border-gray-200">
              <h2 id="confirm-title" class="text-lg font-semibold text-gray-900">{{ titulo() }}</h2>
            </div>
            <div class="px-6 py-4">
              <p class="text-gray-600">{{ mensaje() }}</p>
              @if (detalle()) {
                <p class="mt-2 text-sm font-medium text-gray-900">{{ detalle() }}</p>
              }
            </div>
            <div class="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
              <button
                (click)="cancel.emit()"
                class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500"
              >
                Cancelar
              </button>
              <button
                (click)="confirm.emit()"
                [disabled]="loading()"
                [class]="confirmButtonClasses()"
              >
                @if (loading()) {
                  <sl-loading-spinner size="16" />
                } @else {
                  {{ textoConfirmar() }}
                }
              </button>
            </div>
          </div>
        </div>
      </div>
    }
  `,
  styles: ``,
})
export class ModalConfirmarComponent {
  readonly isOpen = input<boolean>(false);
  readonly titulo = input<string>('Confirmar acción');
  readonly mensaje = input<string>('¿Estás seguro de realizar esta acción?');
  readonly detalle = input<string>('');
  readonly textoConfirmar = input<string>('Confirmar');
  readonly variante = input<'danger' | 'primary'>('danger');
  readonly loading = input<boolean>(false);

  readonly confirm = output<void>();
  readonly cancel = output<void>();

  readonly confirmButtonClasses = computed(() => {
    const base = 'px-4 py-2 text-sm font-medium text-white border border-transparent rounded-lg focus:outline-none focus:ring-2 disabled:opacity-50 disabled:cursor-not-allowed';
    const variante = this.variante();
    return variante === 'danger'
      ? `${base} bg-red-600 hover:bg-red-700 focus:ring-red-500`
      : `${base} bg-indigo-600 hover:bg-indigo-700 focus:ring-indigo-500`;
  });
}