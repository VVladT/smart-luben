import { Component, effect, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { rxResource } from '@angular/core/rxjs-interop';
import { EspaciosService } from '../../core/services/espacios.service';
import { ProductosService } from '../../core/services/productos.service';
import { EspacioConProductoResponse } from '../../core/api/generated/types';
import { EspacioCardComponent } from './espacio-card.component';
import { ModalReponerComponent } from './modal-reponer.component';
import { ModalConfirmarComponent } from './modal-confirmar.component';
import { ErrorMessageComponent } from '../../shared/error-message.component';
import { NavbarComponent } from '../../shared/navbar.component';

@Component({
  selector: 'sl-mostrador-page',
  standalone: true,
  imports: [
    CommonModule,
    EspacioCardComponent,
    ModalReponerComponent,
    ModalConfirmarComponent,
    ErrorMessageComponent,
    NavbarComponent,
  ],
  template: `
    <div class="min-h-screen bg-gray-50">
      <sl-navbar />
      <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div class="flex items-center justify-between mb-8">
          <div>
            <h1 class="text-3xl font-bold text-gray-900">Mostrador</h1>
            <p class="text-gray-500 mt-1">Gestión de espacios de exhibición</p>
          </div>
          <div class="flex items-center space-x-4">
            <div class="flex items-center space-x-2 text-sm text-gray-500">
              <span class="flex items-center space-x-1">
                <span class="w-3 h-3 rounded-full bg-gray-300"></span>
                <span>Libre</span>
              </span>
              <span class="flex items-center space-x-1">
                <span class="w-3 h-3 rounded-full bg-green-300"></span>
                <span>Ocupado</span>
              </span>
            </div>
            <button
              (click)="refreshEspacios()"
              [disabled]="espaciosResource.isLoading()"
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 flex items-center space-x-2"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span>Actualizar</span>
            </button>
          </div>
        </div>

        @if (errorMessage()) {
          <sl-error-message [message]="errorMessage()" />
        }

        @if (espaciosResource.isLoading()) {
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-4 gap-4">
            @for (i of [1,2,3,4,5,6,7,8]; track i) {
              <div class="bg-gray-50 border-2 border-gray-200 rounded-xl p-4 animate-pulse">
                <div class="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                <div class="h-3 bg-gray-200 rounded w-1/2 mb-4"></div>
                <div class="h-32 bg-gray-200 rounded"></div>
              </div>
            }
          </div>
        } @else {
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-4 gap-4">
            @for (espacio of espacios(); track espacio.id) {
              <sl-espacio-card
                [espacio]="espacio"
                (reponer)="openReponerModal($event)"
                (liberar)="openLiberarModal($event)"
              />
            }
            @if (espacios().length === 0) {
              <div class="col-span-full text-center py-12">
                <svg class="w-16 h-16 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                </svg>
                <h3 class="text-lg font-medium text-gray-900 mb-2">No hay espacios configurados</h3>
                <p class="text-gray-500">Los espacios se gestionan desde la API directamente.</p>
              </div>
            }
          </div>
        }

        <sl-modal-reponer
          [isOpen]="showReponerModal()"
          [espacio]="selectedEspacioParaReponer()"
          [productos]="productosActivos()"
          [loading]="productosResource.isLoading()"
          (close)="closeReponerModal()"
          (confirmar)="confirmarReponer($event)"
        />

        <sl-modal-confirmar
          [isOpen]="showLiberarModal()"
          [titulo]="'Liberar espacio'"
          [mensaje]="'¿Estás seguro de liberar el espacio ' + selectedEspacioParaLiberar()?.codigo + '?'"
          [detalle]="'Se registrará una salida del producto ' + selectedEspacioParaLiberar()?.producto_actual?.nombre"
          [textoConfirmar]="'Liberar'"
          [variante]="'danger'"
          [loading]="liberandoEspacioId() !== null"
          (confirm)="confirmarLiberar()"
          (cancel)="closeLiberarModal()"
        />
      </main>
    </div>
  `,
  styles: ``,
})
export class MostradorPageComponent implements OnInit {
  private espaciosService = inject(EspaciosService);
  private productosService = inject(ProductosService);

  readonly autoRefreshInterval = 10000;

  readonly espaciosResource = rxResource({
    params: () => ({}),
    stream: () => this.espaciosService.getEspacios(),
  });

  readonly productosResource = rxResource({
    params: () => ({}),
    stream: () => this.productosService.getProductosActivos(),
  });

  readonly espacios = computed(() => {
    return this.espaciosResource.hasValue() ? this.espaciosResource.value() : [];
  });
  readonly productosActivos = computed(() => {
    return this.productosResource.hasValue() ? this.productosResource.value() : [];
  });

  readonly showReponerModal = signal(false);
  readonly selectedEspacioParaReponer = signal<EspacioConProductoResponse | null>(null);
  readonly showLiberarModal = signal(false);
  readonly selectedEspacioParaLiberar = signal<EspacioConProductoResponse | null>(null);
  readonly liberandoEspacioId = signal<number | null>(null);
  readonly errorMessage = signal<string | null>(null);

  ngOnInit() {
    this.startAutoRefresh();
  }

  startAutoRefresh() {
    setInterval(() => {
      this.refreshEspacios();
    }, this.autoRefreshInterval);
  }

  refreshEspacios() {
    this.espaciosResource.reload();
    this.productosResource.reload();
  }

  openReponerModal(espacio: EspacioConProductoResponse) {
    this.selectedEspacioParaReponer.set(espacio);
    this.showReponerModal.set(true);
  }

  closeReponerModal() {
    this.showReponerModal.set(false);
    this.selectedEspacioParaReponer.set(null);
  }

  confirmarReponer(producto: { id: number }) {
    const espacio = this.selectedEspacioParaReponer();
    if (!espacio) return;

    this.espaciosService.reponerEspacio(espacio.id, { producto_id: producto.id }).subscribe({
      next: () => {
        this.closeReponerModal();
        this.refreshEspacios();
      },
      error: (error) => {
        this.errorMessage.set(this.extractErrorMessage(error));
      },
    });
  }

  openLiberarModal(espacio: EspacioConProductoResponse) {
    this.selectedEspacioParaLiberar.set(espacio);
    this.showLiberarModal.set(true);
  }

  closeLiberarModal() {
    this.showLiberarModal.set(false);
    this.selectedEspacioParaLiberar.set(null);
  }

  confirmarLiberar() {
    const espacio = this.selectedEspacioParaLiberar();
    if (!espacio) return;

    this.liberandoEspacioId.set(espacio.id);
    this.espaciosService.liberarEspacio(espacio.id).subscribe({
      next: () => {
        this.closeLiberarModal();
        this.liberandoEspacioId.set(null);
        this.refreshEspacios();
      },
      error: (error) => {
        this.liberandoEspacioId.set(null);
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