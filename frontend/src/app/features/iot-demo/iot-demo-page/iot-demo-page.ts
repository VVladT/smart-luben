import { CommonModule } from '@angular/common';
import { Component, computed, DestroyRef, OnInit, inject, signal } from '@angular/core';
import { catchError, forkJoin, of } from 'rxjs';
import { NavbarComponent } from '../../../shared/navbar.component';
import { resolveStorageUrl } from '../../../core/api/api-client';
import {
  EspacioConProductoResponse,
  ProductoSimpleResponse,
} from '../../../core/api/generated/types';
import { EspaciosService } from '../../../core/services/espacios.service';
import { ProductosService } from '../../../core/services/productos.service';
import {
  advanceSensorSample,
  DEBOUNCE_READINGS,
  FREE_THRESHOLD_G,
  MAX_LOAD_G,
  OCCUPIED_THRESHOLD_G,
  SAMPLE_INTERVAL_MS,
} from '../sensor-simulation';
type ApiAction = 'reponer' | 'liberar';

interface DemoSlot {
  space: EspacioConProductoResponse;
  physicalProduct: ProductoSimpleResponse | null;
  loadGrams: number;
  sensorOccupied: boolean;
  occupiedReadings: number;
  freeReadings: number;
  busy: boolean;
  error: string | null;
  retryAction: ApiAction | null;
}


@Component({
  imports: [CommonModule, NavbarComponent],
  selector: 'sl-iot-demo-page',
  styleUrl: './iot-demo-page.scss',
  templateUrl: './iot-demo-page.html',
})
export class IotDemoPage implements OnInit {
  private readonly destroyRef = inject(DestroyRef);
  private readonly espaciosService = inject(EspaciosService);
  private readonly productosService = inject(ProductosService);

  readonly slots = signal<DemoSlot[]>([]);
  readonly products = signal<ProductoSimpleResponse[]>([]);
  readonly productWeights = signal<Record<number, number>>({});
  readonly selectedProductId = signal<number | null>(null);
  readonly draggingProductId = signal<number | null>(null);
  readonly loading = signal(true);
  readonly pageError = signal<string | null>(null);
  readonly showCircuit = signal(false);
  readonly selectedProduct = computed(() => this.products().find((product) => product.id === this.selectedProductId()) ?? null);
  readonly productsWithWeight = computed(() => this.products().map((product) => ({
    product,
    weight: this.productWeights()[product.id] ?? 250,
  })));
  readonly circuitSensors = computed(() => this.slots().slice(0, 4).map((slot, index) => ({
    slot,
    index,
    sensor: `S${index + 1}`,
    pin: 32 + index,
  })));

  readonly occupiedThreshold = OCCUPIED_THRESHOLD_G;
  readonly freeThreshold = FREE_THRESHOLD_G;
  readonly maxLoad = MAX_LOAD_G;

  ngOnInit(): void {
    this.loadInitialState();
    const intervalId = window.setInterval(() => this.sampleSensors(), SAMPLE_INTERVAL_MS);
    this.destroyRef.onDestroy(() => window.clearInterval(intervalId));
  }

  loadInitialState(): void {
    this.loading.set(true);
    this.pageError.set(null);

    forkJoin({
      spaces: this.espaciosService.getEspacios(),
      products: this.productosService.getProductosActivos().pipe(catchError(() => of([]))),
    }).subscribe({
      next: ({ spaces, products }) => {
        const orderedSpaces = [...spaces].sort((a, b) => a.codigo.localeCompare(b.codigo));
        this.products.set(products);
        this.productWeights.set(this.readProductWeights(products));
        this.slots.set(orderedSpaces.map((space) => {
          const occupied = this.isOccupied(space);
          const illustrativeProduct = space.situacion === 'desconocido' && products.length
            ? products[Math.floor(Math.random() * products.length)]
            : null;
          const physicalProduct = space.situacion === 'desconocido'
            ? illustrativeProduct
            : space.situacion === 'ocupado'
              ? space.producto_actual ?? null
              : null;

          return {
            space,
            physicalProduct,
            // Never let page initialization itself trigger a release write to the API.
            loadGrams: occupied ? 250 : 0,
            sensorOccupied: occupied,
            occupiedReadings: 0,
            freeReadings: 0,
            busy: false,
            error: null,
            retryAction: null,
          };
        }));
        this.loading.set(false);
      },
      error: (error: unknown) => {
        this.pageError.set(this.extractErrorMessage(error));
        this.loading.set(false);
      },
    });
  }

  refresh(): void {
    this.espaciosService.getEspacios().subscribe({
      next: (spaces) => {
        const current = new Map(this.slots().map((slot) => [slot.space.id, slot]));
        const orderedSpaces = [...spaces].sort((a, b) => a.codigo.localeCompare(b.codigo));
        this.slots.set(orderedSpaces.map((space) => {
          const existing = current.get(space.id);
          const occupied = this.isOccupied(space);
          const illustrativeProduct = space.situacion === 'desconocido'
            ? existing?.physicalProduct ?? this.randomProduct()
            : null;
          const physicalProduct = space.situacion === 'ocupado'
            ? existing?.physicalProduct ?? space.producto_actual ?? null
            : space.situacion === 'desconocido'
              ? illustrativeProduct
              : null;
          return {
            space,
            physicalProduct,
            // A manual refresh mirrors backend state; only new user placement changes virtual load.
            loadGrams: occupied ? 250 : 0,
            sensorOccupied: occupied,
            occupiedReadings: 0,
            freeReadings: 0,
            busy: false,
            error: null,
            retryAction: null,
          };
        }));
        this.pageError.set(null);
      },
      error: (error: unknown) => this.pageError.set(this.extractErrorMessage(error)),
    });
  }

  setProductWeight(productId: number, event: Event): void {
    const input = event.target as HTMLInputElement;
    const weight = Math.max(1, Math.min(MAX_LOAD_G, Number(input.value) || 1));
    this.productWeights.update((weights) => {
      const next = { ...weights, [productId]: weight };
      window.localStorage.setItem('smartluben-iot-demo-product-weights', JSON.stringify(next));
      return next;
    });
  }

  selectProduct(productId: number): void {
    this.selectedProductId.update((selected) => selected === productId ? null : productId);
  }

  toggleCircuit(): void {
    this.showCircuit.update((visible) => !visible);
  }

  startProductDrag(productId: number, event: DragEvent): void {
    this.draggingProductId.set(productId);
    event.dataTransfer?.setData('text/plain', String(productId));
    if (event.dataTransfer) event.dataTransfer.effectAllowed = 'copy';
  }

  allowProductDrop(event: DragEvent): void {
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'copy';
  }

  dropProduct(spaceId: number, event: DragEvent): void {
    event.preventDefault();
    const productId = Number(event.dataTransfer?.getData('text/plain')) || this.draggingProductId();
    if (productId) this.placeProduct(spaceId, productId);
    this.draggingProductId.set(null);
  }

  placeSelectedProduct(spaceId: number): void {
    const productId = this.selectedProductId();
    if (productId) this.placeProduct(spaceId, productId);
  }

  removePhysicalProduct(spaceId: number): void {
    this.updateSlot(spaceId, (slot) => ({
      ...slot,
      physicalProduct: null,
      loadGrams: 0,
      error: null,
      retryAction: null,
      occupiedReadings: 0,
      freeReadings: 0,
    }));
  }

  slotCanReceiveProduct(slot: DemoSlot): boolean {
    return !slot.physicalProduct && !this.isOccupied(slot.space) && !slot.busy && !slot.retryAction;
  }

  slotStatusLabel(slot: DemoSlot): string {
    if (slot.physicalProduct && !this.isOccupied(slot.space)) return 'Sin detectar';
    if (!slot.physicalProduct && this.isOccupied(slot.space) && !slot.busy) return 'Retiro pendiente';
    return this.statusLabel(slot.space);
  }

  circuitSignalLabel(slot: DemoSlot): string {
    if (slot.busy) return 'Sincronizando API';
    if (slot.retryAction) return 'Error de API';
    if (slot.sensorOccupied) return 'OCUPADO';
    if (slot.loadGrams >= OCCUPIED_THRESHOLD_G) return 'Umbral alcanzado';
    return 'En reposo';
  }

  circuitSignalActive(slot: DemoSlot): boolean {
    return slot.sensorOccupied || slot.loadGrams >= OCCUPIED_THRESHOLD_G;
  }

  retry(slot: DemoSlot): void {
    if (slot.retryAction) this.sendTransition(slot, slot.retryAction);
  }

  productImage(product: ProductoSimpleResponse | null): string | null {
    return resolveStorageUrl(product?.imagen_url);
  }

  statusLabel(space: EspacioConProductoResponse): string {
    switch (space.situacion) {
      case 'ocupado': return 'Ocupado';
      case 'desconocido': return 'Desconocido';
      case 'pendiente': return 'Pendiente';
      default: return 'Libre';
    }
  }

  isOccupied(space: EspacioConProductoResponse): boolean {
    return space.situacion === 'ocupado' || space.situacion === 'desconocido';
  }

  private sampleSensors(): void {
    for (const slot of this.slots()) {
      if (slot.busy || slot.retryAction) continue;
      const sample = advanceSensorSample(
        slot.loadGrams,
        slot.sensorOccupied,
        slot.occupiedReadings,
        slot.freeReadings,
      );

      if (sample.transition) {
        this.sendTransition(slot, sample.transition === 'occupied' ? 'reponer' : 'liberar');
      } else if (sample.occupiedReadings !== slot.occupiedReadings || sample.freeReadings !== slot.freeReadings) {
        this.updateSlot(slot.space.id, (current) => ({
          ...current,
          occupiedReadings: sample.occupiedReadings,
          freeReadings: sample.freeReadings,
        }));
      }
    }
  }

  private sendTransition(slot: DemoSlot, action: ApiAction): void {
    this.updateSlot(slot.space.id, (current) => ({ ...current, busy: true, error: null, retryAction: null }));
    const request = action === 'reponer'
      ? this.espaciosService.reponerEspacio(slot.space.id, {})
      : this.espaciosService.liberarEspacio(slot.space.id);

    request.subscribe({
      next: () => {
        this.reloadAfterTransition(slot.space.id);
      },
      error: (error: unknown) => {
        const message = this.extractErrorMessage(error);
        if ((action === 'reponer' && message.includes('ya está ocupado')) ||
            (action === 'liberar' && message.includes('ya está libre'))) {
          this.reloadAfterTransition(slot.space.id);
          return;
        }
        this.updateSlot(slot.space.id, (current) => ({
          ...current,
          busy: false,
          error: message,
          retryAction: action,
          occupiedReadings: 0,
          freeReadings: 0,
        }));
      },
    });
  }

  private reloadAfterTransition(spaceId: number): void {
    this.espaciosService.getEspacios().subscribe({
      next: (spaces) => {
        const updatedSpace = spaces.find((space) => space.id === spaceId);
        if (!updatedSpace) {
          this.pageError.set('La API no devolvió el espacio actualizado.');
          this.updateSlot(spaceId, (slot) => ({ ...slot, busy: false }));
          return;
        }
        const occupied = this.isOccupied(updatedSpace);
        this.updateSlot(spaceId, (slot) => ({
          ...slot,
          space: updatedSpace,
          sensorOccupied: occupied,
          occupiedReadings: 0,
          freeReadings: 0,
          busy: false,
          error: null,
          retryAction: null,
          physicalProduct: slot.physicalProduct ?? (updatedSpace.situacion === 'desconocido'
            ? this.randomProduct()
            : updatedSpace.situacion === 'ocupado'
              ? updatedSpace.producto_actual ?? null
              : null),
        }));
      },
      error: (error: unknown) => {
        this.updateSlot(spaceId, (slot) => ({ ...slot, busy: false }));
        this.pageError.set(`El evento se guardó, pero no se pudo actualizar la vista: ${this.extractErrorMessage(error)}`);
      },
    });
  }

  private randomProduct(): ProductoSimpleResponse | null {
    const products = this.products();
    return products.length ? products[Math.floor(Math.random() * products.length)] : null;
  }

  private placeProduct(spaceId: number, productId: number): void {
    const product = this.products().find((candidate) => candidate.id === productId);
    const slot = this.slots().find((candidate) => candidate.space.id === spaceId);
    if (!product || !slot || !this.slotCanReceiveProduct(slot)) return;

    const weight = this.productWeights()[productId] ?? 250;
    this.selectedProductId.set(null);
    this.updateSlot(spaceId, (current) => ({
      ...current,
      physicalProduct: product,
      loadGrams: weight,
      error: null,
      retryAction: null,
      occupiedReadings: 0,
      freeReadings: 0,
    }));
  }

  private readProductWeights(products: ProductoSimpleResponse[]): Record<number, number> {
    const defaults = Object.fromEntries(products.map((product) => [product.id, 250]));
    try {
      const saved = JSON.parse(window.localStorage.getItem('smartluben-iot-demo-product-weights') ?? '{}') as Record<string, unknown>;
      for (const product of products) {
        const weight = Number(saved[product.id]);
        if (Number.isFinite(weight) && weight > 0 && weight <= MAX_LOAD_G) defaults[product.id] = weight;
      }
    } catch {
      // Ignore invalid local preferences and use the demo default weight.
    }
    return defaults;
  }

  private updateSlot(spaceId: number, update: (slot: DemoSlot) => DemoSlot): void {
    this.slots.update((slots) => slots.map((slot) => slot.space.id === spaceId ? update(slot) : slot));
  }

  private extractErrorMessage(error: unknown): string {
    if (error && typeof error === 'object' && 'error' in error) {
      const body = (error as { error?: { detail?: string | { msg: string }[] } }).error;
      if (Array.isArray(body?.detail)) return body.detail.map((item) => item.msg).join(', ');
      if (body?.detail) return body.detail;
    }
    return 'No se pudo comunicar con la API.';
  }
}
