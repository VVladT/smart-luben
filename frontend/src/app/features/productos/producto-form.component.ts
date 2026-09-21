import { Component, input, output, signal, effect, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ProductoListResponse, ProductoCreate, ProductoUpdate } from '../../core/api/generated/types';
import { LoadingSpinnerComponent } from '../../shared/loading-spinner.component';

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
                  <input
                    type="url"
                    id="imagen_url"
                    formControlName="imagen_url"
                    class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="https://ejemplo.com/imagen.jpg"
                  />
                  @if (form.get('imagen_url')?.invalid && form.get('imagen_url')?.touched) {
                    <p class="mt-1 text-sm text-red-600">URL inválida</p>
                  }
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

  readonly isOpen = input<boolean>(false);
  readonly editingProducto = input<ProductoListResponse | null>(null);
  readonly loading = input<boolean>(false);

  readonly close = output<void>();
  readonly save = output<ProductoCreate | ProductoUpdate>();

  readonly form = this.fb.nonNullable.group({
    nombre: ['', [Validators.required, Validators.maxLength(100)]],
    categoria: ['', [Validators.required, Validators.maxLength(50)]],
    imagen_url: ['', [Validators.maxLength(500)]],
    activo: [true],
  });

  private autoFillFormEffect = effect(() => {
    const producto = this.editingProducto();
    
    if (producto) {
      this.form.patchValue({
        nombre: producto.nombre,
        categoria: producto.categoria,
        imagen_url: producto.imagen_url ?? '',
        activo: producto.activo,
      });
    } else {
      this.form.reset({
        nombre: '',
        categoria: '',
        imagen_url: '',
        activo: true,
      });
    }
  });

  onSubmit() {
    if (this.form.valid) {
      const value = this.form.getRawValue();
      const producto = this.editingProducto();

      if (producto) {
        const updateData: ProductoUpdate = {
          nombre: value.nombre,
          categoria: value.categoria,
          imagen_url: value.imagen_url || null,
          activo: value.activo,
        };
        this.save.emit(updateData);
      } else {
        const createData: ProductoCreate = {
          nombre: value.nombre,
          categoria: value.categoria,
          imagen_url: value.imagen_url || null,
        };
        this.save.emit(createData);
      }
    } else {
      this.form.markAllAsTouched();
    }
  }
}