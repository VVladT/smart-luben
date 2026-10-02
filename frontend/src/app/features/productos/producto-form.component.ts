import { Component, input, output, signal, effect, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ProductoListResponse, ProductoCreate, ProductoUpdate } from '../../core/api/generated/types';
import { LoadingSpinnerComponent } from '../../shared/loading-spinner.component';
import { UploadsService, UploadTipo } from '../../core/services/uploads.service';

@Component({
  selector: 'sl-producto-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LoadingSpinnerComponent],
  template: `
    @if (isOpen()) {
      <div class="fixed inset-0 z-50 overflow-y-auto" role="dialog" aria-modal="true" aria-labelledby="form-title">
        <div class="flex min-h-full items-center justify-center p-4">
          <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true" (click)="close.emit()"></div>
          <div class="relative bg-white rounded-xl shadow-xl max-w-md w-full transform transition-all max-h-[90vh] overflow-hidden">
            <form [formGroup]="form" (ngSubmit)="onSubmit()" class="flex flex-col">
              <div class="px-6 py-4 border-b border-gray-200">
                <h2 id="form-title" class="text-lg font-semibold text-gray-900">
                  {{ editingProducto() ? 'Editar producto' : 'Nuevo producto' }}
                </h2>
              </div>
              <div class="px-6 py-4 overflow-y-auto flex-1 space-y-4">
                <div>
                  <label for="nombre" class="block text-sm font-medium text-gray-700 mb-1">Nombre *</label>
                  <input
                    type="text"
                    id="nombre"
                    formControlName="nombre"
                    class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Ej: Croissant de mantequilla"
                  />
                  @if (form.get('nombre')?.invalid && form.get('nombre')?.touched) {
                    <p class="mt-1 text-sm text-red-600">El nombre es obligatorio</p>
                  }
                </div>

                <div>
                  <label for="categoria" class="block text-sm font-medium text-gray-700 mb-1">Categoría *</label>
                  <input
                    type="text"
                    id="categoria"
                    formControlName="categoria"
                    class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Ej: Panadería"
                  />
                  @if (form.get('categoria')?.invalid && form.get('categoria')?.touched) {
                    <p class="mt-1 text-sm text-red-600">La categoría es obligatoria</p>
                  }
                </div>

                <div>
                  <label for="imagen_url" class="block text-sm font-medium text-gray-700 mb-1">URL de imagen</label>
                  <div class="flex gap-2">
                    <input
                      type="url"
                      id="imagen_url"
                      formControlName="imagen_url"
                      class="flex-1 min-w-0 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      placeholder="https://ejemplo.com/imagen.jpg"
                    />
                    <label class="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer whitespace-nowrap">
                      Subir
                      <input type="file" accept="image/jpeg,image/png,image/webp" class="hidden" (change)="subirArchivo('imagen', $event)" />
                    </label>
                  </div>
                  @if (form.get('imagen_url')?.invalid && form.get('imagen_url')?.touched) {
                    <p class="mt-1 text-sm text-red-600">URL inválida</p>
                  }
                </div>

                <div>
                  <label for="modelo_url" class="block text-sm font-medium text-gray-700 mb-1">Modelo 3D (.glb)</label>
                  <div class="flex gap-2">
                    <input
                      type="url"
                      id="modelo_url"
                      formControlName="modelo_url"
                      class="flex-1 min-w-0 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      placeholder="https://.../modelo.glb"
                    />
                    <label class="px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 cursor-pointer whitespace-nowrap">
                      Subir
                      <input type="file" accept=".glb,model/gltf-binary" class="hidden" (change)="subirArchivo('modelo', $event)" />
                    </label>
                  </div>
                  @if (subiendo()) {
                    <p class="mt-1 text-sm text-indigo-600">Subiendo {{ subiendo() }}...</p>
                  }
                  @if (errorSubida()) {
                    <p class="mt-1 text-sm text-red-600">{{ errorSubida() }}</p>
                  }
                  @if (editingProducto()?.version) {
                    <p class="mt-1 text-xs text-gray-500">Versión del modelo: {{ editingProducto()!.version }} (se bumpea sola al cambiar el archivo)</p>
                  }
                </div>

                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label for="scale" class="block text-sm font-medium text-gray-700 mb-1">Escala</label>
                    <input
                      type="number"
                      id="scale"
                      formControlName="scale"
                      step="0.1"
                      min="0.01"
                      class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                  <div>
                    <label for="rotation_x" class="block text-sm font-medium text-gray-700 mb-1">Rotación X (rad)</label>
                    <input
                      type="number"
                      id="rotation_x"
                      formControlName="rotation_x"
                      step="0.1"
                      class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                  <div>
                    <label for="rotation_y" class="block text-sm font-medium text-gray-700 mb-1">Rotación Y (rad)</label>
                    <input
                      type="number"
                      id="rotation_y"
                      formControlName="rotation_y"
                      step="0.1"
                      class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                  <div>
                    <label for="rotation_z" class="block text-sm font-medium text-gray-700 mb-1">Rotación Z (rad)</label>
                    <input
                      type="number"
                      id="rotation_z"
                      formControlName="rotation_z"
                      step="0.1"
                      class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>
                </div>

                @if (editingProducto()) {
                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">Estado</label>
                    <div class="flex items-center space-x-2">
                      <input
                        type="checkbox"
                        id="activo"
                        formControlName="activo"
                        class="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                      />
                      <label for="activo" class="text-sm text-gray-700">Activo</label>
                    </div>
                  </div>
                }
              </div>
              <div class="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
                <button
                  type="button"
                  (click)="close.emit()"
                  class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  [disabled]="form.invalid || loading()"
                  class="px-4 py-2 text-sm font-medium text-white bg-indigo-600 border border-transparent rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                >
                  @if (loading()) {
                    <sl-loading-spinner size="16" />
                  } @else {
                    <span>{{ editingProducto() ? 'Actualizar' : 'Crear' }}</span>
                  }
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    }
  `,
  styles: ``,
})
export class ProductoFormComponent {
  private fb = inject(FormBuilder);
  private uploadsService = inject(UploadsService);

  readonly isOpen = input<boolean>(false);
  readonly editingProducto = input<ProductoListResponse | null>(null);
  readonly loading = input<boolean>(false);

  readonly close = output<void>();
  readonly save = output<ProductoCreate | ProductoUpdate>();

  readonly subiendo = signal<UploadTipo | null>(null);
  readonly errorSubida = signal<string | null>(null);

  readonly form = this.fb.nonNullable.group({
    nombre: ['', [Validators.required, Validators.maxLength(100)]],
    categoria: ['', [Validators.required, Validators.maxLength(50)]],
    imagen_url: ['', [Validators.maxLength(500)]],
    modelo_url: ['', [Validators.maxLength(500)]],
    scale: [1, [Validators.min(0.01), Validators.max(100)]],
    rotation_x: [0],
    rotation_y: [0],
    rotation_z: [0],
    activo: [true],
  });

  private autoFillFormEffect = effect(() => {
    const producto = this.editingProducto();

    if (producto) {
      this.form.patchValue({
        nombre: producto.nombre,
        categoria: producto.categoria,
        imagen_url: producto.imagen_url ?? '',
        modelo_url: producto.modelo_url ?? '',
        scale: producto.scale ?? 1,
        rotation_x: producto.rotation_x ?? 0,
        rotation_y: producto.rotation_y ?? 0,
        rotation_z: producto.rotation_z ?? 0,
        activo: producto.activo,
      });
    } else {
      this.form.reset({
        nombre: '',
        categoria: '',
        imagen_url: '',
        modelo_url: '',
        scale: 1,
        rotation_x: 0,
        rotation_y: 0,
        rotation_z: 0,
        activo: true,
      });
    }
    this.errorSubida.set(null);
  });

  subirArchivo(tipo: UploadTipo, event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file || this.subiendo()) return;

    this.subiendo.set(tipo);
    this.errorSubida.set(null);
    this.uploadsService.upload(tipo, file).subscribe({
      next: (publicUrl) => {
        if (tipo === 'modelo') {
          this.form.patchValue({ modelo_url: publicUrl });
        } else {
          this.form.patchValue({ imagen_url: publicUrl });
        }
        this.subiendo.set(null);
      },
      error: (err) => {
        this.subiendo.set(null);
        this.errorSubida.set(this.mensajeSubida(err));
      },
    });
  }

  private mensajeSubida(error: unknown): string {
    if (error && typeof error === 'object' && 'error' in error) {
      const detail = (error as { error?: { detail?: string } }).error?.detail;
      if (typeof detail === 'string') return detail;
    }
    return 'No se pudo subir el archivo';
  }

  onSubmit() {
    if (this.form.valid) {
      const value = this.form.getRawValue();
      const producto = this.editingProducto();

      if (producto) {
        const updateData: ProductoUpdate = {
          nombre: value.nombre,
          categoria: value.categoria,
          imagen_url: value.imagen_url || null,
          modelo_url: value.modelo_url || null,
          scale: value.scale,
          rotation_x: value.rotation_x,
          rotation_y: value.rotation_y,
          rotation_z: value.rotation_z,
          activo: value.activo,
        };
        this.save.emit(updateData);
      } else {
        const createData: ProductoCreate = {
          nombre: value.nombre,
          categoria: value.categoria,
          imagen_url: value.imagen_url || null,
          modelo_url: value.modelo_url || null,
          scale: value.scale,
          rotation_x: value.rotation_x,
          rotation_y: value.rotation_y,
          rotation_z: value.rotation_z,
        };
        this.save.emit(createData);
      }
    } else {
      this.form.markAllAsTouched();
    }
  }
}