import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { rxResource } from '@angular/core/rxjs-interop';
import { ProductosService } from '../../core/services/productos.service';
import { ProductoListResponse, ProductoCreate, ProductoUpdate } from '../../core/api/generated/types';
import { ProductoFormComponent } from './producto-form.component';
import { ErrorMessageComponent } from '../../shared/error-message.component';
import { NavbarComponent } from '../../shared/navbar.component';

@Component({
  selector: 'sl-productos-page',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ProductoFormComponent,
    ErrorMessageComponent,
    NavbarComponent,
  ],
  template: `
    <div class="min-h-screen bg-gray-50">
      <sl-navbar />
      <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div class="flex items-center justify-between mb-8">
          <div>
            <h1 class="text-3xl font-bold text-gray-900">Productos</h1>
            <p class="text-gray-500 mt-1">Gestión de productos del mostrador</p>
          </div>
          <button
            (click)="openCreateModal()"
            class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 border border-transparent rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 flex items-center space-x-2"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            <span>Nuevo producto</span>
          </button>
        </div>

        <div class="mb-6 flex items-center space-x-4">
          <label for="filtro-activo" class="text-sm font-medium text-gray-700">Filtrar:</label>
          <select
            id="filtro-activo"
            [(ngModel)]="filtroActivo"
            (change)="aplicarFiltro()"
            class="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Todos</option>
            <option value="true">Solo activos</option>
            <option value="false">Solo inactivos</option>
          </select>
        </div>

        @if (errorMessage()) {
          <sl-error-message [message]="errorMessage()" />
        }

        @if (productosResource.isLoading()) {
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nombre</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Categoría</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Imagen</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Estado</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Acciones</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                @for (i of [1,2,3,4,5]; track i) {
                  <tr class="animate-pulse">
                    <td class="px-6 py-4"><div class="h-4 bg-gray-200 rounded w-3/4"></div></td>
                    <td class="px-6 py-4"><div class="h-4 bg-gray-200 rounded w-1/2"></div></td>
                    <td class="px-6 py-4"><div class="w-12 h-12 bg-gray-200 rounded"></div></td>
                    <td class="px-6 py-4"><div class="h-5 bg-gray-200 rounded w-20"></div></td>
                    <td class="px-6 py-4"><div class="h-8 bg-gray-200 rounded w-20"></div></td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        } @else {
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nombre</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Categoría</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Imagen</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Estado</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Acciones</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                @for (producto of productos(); track producto.id) {
                  <tr class="hover:bg-gray-50">
                    <td class="px-6 py-4 whitespace-nowrap">
                      <div class="font-medium text-gray-900">{{ producto.nombre }}</div>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-gray-500">{{ producto.categoria }}</td>
                    <td class="px-6 py-4 whitespace-nowrap">
                      @if (producto.imagen_url) {
                        <img [src]="producto.imagen_url" [alt]="producto.nombre" class="w-12 h-12 object-cover rounded" />
                      } @else {
                        <div class="w-12 h-12 bg-gray-100 rounded flex items-center justify-center">
                          <svg class="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                        </div>
                      }
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                      <span class="px-2 py-1 text-xs font-semibold rounded-full" [class]="producto.activo ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'">
                        {{ producto.activo ? 'Activo' : 'Inactivo' }}
                      </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                      <button
                        (click)="openEditModal(producto)"
                        class="text-indigo-600 hover:text-indigo-900"
                      >
                        Editar
                      </button>
                      <button
                        (click)="toggleActivo(producto)"
                        [disabled]="guardandoEstado() === producto.id"
                        class="text-gray-600 hover:text-gray-900 disabled:opacity-50"
                      >
                        {{ producto.activo ? 'Desactivar' : 'Activar' }}
                      </button>
                    </td>
                  </tr>
                }
                @if (productos().length === 0) {
                  <tr>
                    <td colspan="5" class="px-6 py-12 text-center text-gray-500">
                      <svg class="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                      </svg>
                      <p>No se encontraron productos</p>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }

        <sl-producto-form
          [isOpen]="showFormModal()"
          [editingProducto]="editingProducto()"
          [loading]="guardando()"
          (close)="closeFormModal()"
          (save)="saveProducto($event)"
        />
      </main>
    </div>
  `,
  styles: ``,
})
export class ProductosPageComponent implements OnInit {
  private productosService = inject(ProductosService);

  readonly filtroActivo = signal<string>('');
  readonly showFormModal = signal(false);
  readonly editingProducto = signal<ProductoListResponse | null>(null);
  readonly guardando = signal(false);
  readonly guardandoEstado = signal<number | null>(null);
  readonly errorMessage = signal<string | null>(null);

  readonly productosResource = rxResource({
    params: () => ({ activo: this.filtroActivo() === '' ? undefined : this.filtroActivo() === 'true' }),
    stream: ({ params }) => this.productosService.getProductos(params.activo),
  });

  readonly productos = computed(() => {
    return this.productosResource.hasValue() ? this.productosResource.value() : [];
  });

  ngOnInit() {}

  aplicarFiltro() {
    this.productosResource.reload();
  }

  openCreateModal() {
    this.editingProducto.set(null);
    this.showFormModal.set(true);
  }

  openEditModal(producto: ProductoListResponse) {
    this.editingProducto.set(producto);
    this.showFormModal.set(true);
  }

  closeFormModal() {
    this.showFormModal.set(false);
    this.editingProducto.set(null);
  }

  saveProducto(data: ProductoCreate | ProductoUpdate) {
    this.guardando.set(true);
    const producto = this.editingProducto();

    const request = producto
      ? this.productosService.updateProducto(producto.id, data as ProductoUpdate)
      : this.productosService.createProducto(data as ProductoCreate);

    request.subscribe({
      next: () => {
        this.closeFormModal();
        this.guardando.set(false);
        this.productosResource.reload();
      },
      error: (error) => {
        this.guardando.set(false);
        this.errorMessage.set(this.extractErrorMessage(error));
      },
    });
  }

  toggleActivo(producto: ProductoListResponse) {
    this.guardandoEstado.set(producto.id);
    this.productosService.updateProducto(producto.id, { activo: !producto.activo }).subscribe({
      next: () => {
        this.guardandoEstado.set(null);
        this.productosResource.reload();
      },
      error: (error) => {
        this.guardandoEstado.set(null);
        this.errorMessage.set(this.extractErrorMessage(error));
      },
    });
  }

  extractErrorMessage(error: unknown): string {
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