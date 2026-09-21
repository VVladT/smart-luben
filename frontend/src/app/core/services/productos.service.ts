import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  ProductoCreate,
  ProductoListResponse,
  ProductoResponse,
  ProductoUpdate,
  ProductoSimpleResponse,
} from '../api/generated/types';
import { getApiBaseUrl } from '../api/api-client';

@Injectable({ providedIn: 'root' })
export class ProductosService {
  private http = inject(HttpClient);
  private baseUrl = getApiBaseUrl() + '/productos';

  getProductos(activo?: boolean): Observable<ProductoListResponse[]> {
    const url = new URL(this.baseUrl, window.location.origin);
    if (activo !== undefined) {
      url.searchParams.set('activo', String(activo));
    }
    return this.http.get<ProductoListResponse[]>(url.toString());
  }

  getProducto(id: number): Observable<ProductoResponse> {
    return this.http.get<ProductoResponse>(`${this.baseUrl}/${id}`);
  }

  createProducto(producto: ProductoCreate): Observable<ProductoResponse> {
    return this.http.post<ProductoResponse>(this.baseUrl, producto);
  }

  updateProducto(id: number, producto: ProductoUpdate): Observable<ProductoResponse> {
    return this.http.put<ProductoResponse>(`${this.baseUrl}/${id}`, producto);
  }

  deleteProducto(id: number): Observable<ProductoResponse> {
    return this.http.delete<ProductoResponse>(`${this.baseUrl}/${id}`);
  }

  getProductosActivos(): Observable<ProductoSimpleResponse[]> {
    return this.http.get<ProductoSimpleResponse[]>(`${this.baseUrl}?activo=true`);
  }
}