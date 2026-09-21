import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { rxResource } from '@angular/core/rxjs-interop';
import { MovimientosService, MovimientosFilters } from '../../core/services/movimientos.service';
import { EspaciosService } from '../../core/services/espacios.service';
import { ProductosService } from '../../core/services/productos.service';
import { ErrorMessageComponent } from '../../shared/error-message.component';
import { NavbarComponent } from '../../shared/navbar.component';

interface PaginatedMovimientosResponse {
  items: Array<{
    espacio_id: number;
    producto_id: number;
    tipo: 'reposicion' | 'salida';
    id: number;
    fecha_hora: string;
    espacio_codigo: string;
    producto_nombre: string;
    producto_categoria: string;
  }>;
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

@Component({
  selector: 'sl-movimientos-page',
  standalone: true,
  imports: [CommonModule, FormsModule, ErrorMessageComponent, NavbarComponent],
  template: `
    <div class="min-h-screen bg-gray-50">
      <sl-navbar />
      <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div class="mb-8">
          <h1 class="text-3xl font-bold text-gray-900">Historial de Movimientos</h1>
          <p class="text-gray-500 mt-1">Registro de reposiciones y salidas</p>
        </div>

        <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <div>
              <label for="filtro-espacio" class="block text-sm font-medium text-gray-700 mb-1">Espacio</label>
              <select
                id="filtro-espacio"
                [value]="filtros().espacioId ?? ''"
                (change)="onEspacioChange($event)"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Todos</option>
                @for (espacio of espaciosDisponibles(); track espacio.id) {
                  <option [value]="espacio.id">{{ espacio.codigo }} - {{ espacio.ubicacion }}</option>
                }
              </select>
            </div>
            <div>
              <label for="filtro-producto" class="block text-sm font-medium text-gray-700 mb-1">Producto</label>
              <select
                id="filtro-producto"
                [value]="filtros().productoId ?? ''"
                (change)="onProductoChange($event)"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Todos</option>
                @for (producto of productosDisponibles(); track producto.id) {
                  <option [value]="producto.id">{{ producto.nombre }}</option>
                }
              </select>
            </div>
            <div>
              <label for="filtro-tipo" class="block text-sm font-medium text-gray-700 mb-1">Tipo</label>
              <select
                id="filtro-tipo"
                [value]="filtros().tipo ?? ''"
                (change)="onTipoChange($event)"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Todos</option>
                <option value="reposicion">Reposición</option>
                <option value="salida">Salida</option>
              </select>
            </div>
            <div>
              <label for="filtro-desde" class="block text-sm font-medium text-gray-700 mb-1">Desde</label>
              <input
                type="date"
                id="filtro-desde"
                [value]="filtros().desde ?? ''"
                (change)="onDesdeChange($event)"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label for="filtro-hasta" class="block text-sm font-medium text-gray-700 mb-1">Hasta</label>
              <input
                type="date"
                id="filtro-hasta"
                [value]="filtros().hasta ?? ''"
                (change)="onHastaChange($event)"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>
          <div class="mt-4 flex items-center justify-end">
            <button
              (click)="limpiarFiltros()"
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500"
            >
              Limpiar filtros
            </button>
          </div>
        </div>

        @if (errorMessage()) {
          <sl-error-message [message]="errorMessage()" />
        }

        @if (movimientosResource.isLoading()) {
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fecha/Hora</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Espacio</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Producto</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tipo</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                @for (i of [1,2,3,4,5]; track i) {
                  <tr class="animate-pulse">
                    <td class="px-6 py-4"><div class="h-4 bg-gray-200 rounded w-3/4"></div></td>
                    <td class="px-6 py-4"><div class="h-4 bg-gray-200 rounded w-1/2"></div></td>
                    <td class="px-6 py-4"><div class="h-4 bg-gray-200 rounded w-1/2"></div></td>
                    <td class="px-6 py-4"><div class="h-5 bg-gray-200 rounded w-20"></div></td>
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
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fecha/Hora</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Espacio</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Producto</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Tipo</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                @for (movimiento of movimientos(); track movimiento.id) {
                  <tr class="hover:bg-gray-50">
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {{ formatFecha(movimiento.fecha_hora) }}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <span class="font-mono">{{ movimiento.espacio_codigo }}</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {{ movimiento.producto_nombre }}
                      <span class="text-gray-500 ml-1">({{ movimiento.producto_categoria }})</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                      <span
                        class="px-2 py-1 text-xs font-semibold rounded-full"
                        [class]="movimiento.tipo === 'reposicion' ? 'bg-blue-100 text-blue-700' : 'bg-orange-100 text-orange-700'"
                      >
                        {{ movimiento.tipo === 'reposicion' ? 'Reposición' : 'Salida' }}
                      </span>
                    </td>
                  </tr>
                }
                @if (movimientos().length === 0) {
                  <tr>
                    <td colspan="4" class="px-6 py-12 text-center text-gray-500">
                      <svg class="w-12 h-12 mx-auto mb-3 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                      </svg>
                      <p>No se encontraron movimientos</p>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>

          @if (pagination()) {
            <div class="mt-6 flex items-center justify-center space-x-2">
              <button
                (click)="cambiarPagina(pagination()!.page - 1)"
                [disabled]="pagination()!.page <= 1 || movimientosResource.isLoading()"
                class="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
              >
                Anterior
              </button>
              <span class="px-4 py-2 text-sm text-gray-700">
                Página {{ pagination()!.page }} de {{ pagination()!.total_pages }}
              </span>
              <button
                (click)="cambiarPagina(pagination()!.page + 1)"
                [disabled]="pagination()!.page >= pagination()!.total_pages || movimientosResource.isLoading()"
                class="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
              >
                Siguiente
              </button>
            </div>
          }
        }
      </main>
    </div>
  `,
  styles: ``,
})
export class MovimientosPageComponent implements OnInit {
  private movimientosService = inject(MovimientosService);
  private espaciosService = inject(EspaciosService);
  private productosService = inject(ProductosService);

  readonly filtros = signal<MovimientosFilters>({
    espacioId: undefined,
    productoId: undefined,
    tipo: undefined,
    desde: undefined,
    hasta: undefined,
    skip: 0,
    limit: 20,
  });

  readonly espaciosDisponibles = signal<{ id: number; codigo: string; ubicacion: string }[]>([]);
  readonly productosDisponibles = signal<{ id: number; nombre: string }[]>([]);
  readonly errorMessage = signal<string | null>(null);

  readonly movimientosResource = rxResource({
    params: () => this.filtros(),
    stream: ({ params }) => this.movimientosService.getMovimientos(params),
  });

  readonly movimientos = computed(() => {
    const value = this.movimientosResource.hasValue() ? this.movimientosResource.value() : [];
    return Array.isArray(value) ? value : [];
  });

  readonly pagination = computed((): PaginatedMovimientosResponse | null => {
    const value = this.movimientosResource.hasValue() ? this.movimientosResource.value() : [];
    if (value && typeof value === 'object' && 'items' in value) {
      return value as unknown as PaginatedMovimientosResponse;
    }
    return null;
  });

  ngOnInit() {
    this.cargarEspaciosYProductos();
  }

  cargarEspaciosYProductos() {
    this.espaciosService.getEspacios().subscribe((espacios) => {
      this.espaciosDisponibles.set(espacios.map((e) => ({ id: e.id, codigo: e.codigo, ubicacion: e.ubicacion })));
    });
    this.productosService.getProductosActivos().subscribe((productos) => {
      this.productosDisponibles.set(productos.map((p) => ({ id: p.id, nombre: p.nombre })));
    });
  }

  onEspacioChange(event: Event) {
    const value = (event.target as HTMLSelectElement).value;
    this.filtros.update((f) => ({ ...f, espacioId: value ? Number(value) : undefined, skip: 0 }));
  }

  onProductoChange(event: Event) {
    const value = (event.target as HTMLSelectElement).value;
    this.filtros.update((f) => ({ ...f, productoId: value ? Number(value) : undefined, skip: 0 }));
  }

  onTipoChange(event: Event) {
    const value = (event.target as HTMLSelectElement).value;
    this.filtros.update((f) => ({ ...f, tipo: value as 'reposicion' | 'salida' | undefined, skip: 0 }));
  }

  onDesdeChange(event: Event) {
    const value = (event.target as HTMLInputElement).value;
    this.filtros.update((f) => ({ ...f, desde: value || undefined, skip: 0 }));
  }

  onHastaChange(event: Event) {
    const value = (event.target as HTMLInputElement).value;
    this.filtros.update((f) => ({ ...f, hasta: value || undefined, skip: 0 }));
  }

  aplicarFiltros() {
    this.filtros.update((f) => ({ ...f, skip: 0 }));
  }

  limpiarFiltros() {
    this.filtros.set({
      espacioId: undefined,
      productoId: undefined,
      tipo: undefined,
      desde: undefined,
      hasta: undefined,
      skip: 0,
      limit: 20,
    });
  }

  cambiarPagina(page: number) {
    const limit = this.filtros().limit ?? 20;
    const skip = (page - 1) * limit;
    this.filtros.update((f) => ({ ...f, skip }));
  }

  formatFecha(fecha: string): string {
    const date = new Date(fecha);
    return date.toLocaleString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

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