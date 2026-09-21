import { Component, input, output, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ProductoSimpleResponse } from '../../core/api/generated/types';
import { LoadingSpinnerComponent } from '../../shared/loading-spinner.component';

@Component({
  selector: 'sl-modal-reponer',
  standalone: true,
  imports: [CommonModule, LoadingSpinnerComponent],
  template: `
    @if (isOpen()) {
      <div class="fixed inset-0 z-50 overflow-y-auto" role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <div class="flex min-h-full items-center justify-center p-4">
          <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true" (click)="close.emit()"></div>
          <div class="relative bg-white rounded-xl shadow-xl max-w-md w-full transform transition-all">
            <div class="px-6 py-4 border-b border-gray-200">
              <h2 id="modal-title" class="text-lg font-semibold text-gray-900">Reponer Espacio</h2>
              <p class="text-sm text-gray-500 mt-1">Espacio: <span class="font-mono">{{ espacio()?.codigo }}</span></p>
            </div>
            <div class="px-6 py-4 max-h-96 overflow-y-auto">
              @if (loading()) {
                <div class="flex items-center justify-center py-8">
                  <sl-loading-spinner size="32" message="Cargando productos..." />
                </div>
              } @else if (productos().length === 0) {
                <div class="text-center py-8 text-gray-500">
                  <svg class="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                  </svg>
                  <p>No hay productos activos disponibles</p>
                </div>
              } @else {
                <ul class="space-y-2" role="listbox" aria-label="Seleccionar producto">
                  @for (producto of productos(); track producto.id) {
                    <li>
                      <button
                        (click)="selectProducto(producto)"
                        [class]="productoCardClasses(producto)"
                        class="w-full text-left p-3 rounded-lg border transition-all focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        role="option"
                        [aria-selected]="selectedProducto()?.id === producto.id"
                      >
                        <div class="flex items-center space-x-3">
                          @if (producto.imagen_url) {
                            <img [src]="producto.imagen_url" [alt]="producto.nombre" class="w-10 h-10 object-cover rounded" />
                          } @else {
                            <div class="w-10 h-10 bg-gray-100 rounded flex items-center justify-center">
                              <svg class="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                              </svg>
                            </div>
                          }
                          <div class="flex-1 min-w-0">
                            <p class="font-medium text-gray-900 truncate">{{ producto.nombre }}</p>
                            <p class="text-xs text-gray-500">{{ producto.categoria }}</p>
                          </div>
                          @if (selectedProducto()?.id === producto.id) {
                            <svg class="w-5 h-5 text-indigo-600" fill="currentColor" viewBox="0 0 20 20">
                              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                            </svg>
                          }
                        </div>
                      </button>
                    </li>
                  }
                </ul>
              }
            </div>
            <div class="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
              <button
                (click)="close.emit()"
                class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500"
              >
                Cancelar
              </button>
              <button
                (click)="confirmar.emit(selectedProducto()!)"
                [disabled]="!selectedProducto()"
                class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 border border-transparent rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Confirmar
              </button>
            </div>
          </div>
        </div>
      </div>
    }
  `,
  styles: ``,
})
export class ModalReponerComponent {
  readonly isOpen = input<boolean>(false);
  readonly espacio = input<{ codigo: string } | null>(null);
  readonly productos = input<ProductoSimpleResponse[]>([]);
  readonly loading = input<boolean>(false);

  readonly close = output<void>();
  readonly confirmar = output<ProductoSimpleResponse>();

  readonly selectedProducto = signal<ProductoSimpleResponse | null>(null);

  selectProducto(producto: ProductoSimpleResponse) {
    this.selectedProducto.set(producto);
  }

  productoCardClasses(producto: ProductoSimpleResponse): string {
    const selected = this.selectedProducto()?.id === producto.id;
    return selected
      ? 'border-indigo-500 bg-indigo-50 ring-2 ring-indigo-500'
      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50';
  }
}