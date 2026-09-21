import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { MovimientoDetalleResponse, TipoMovimiento } from '../api/generated/types';
import { getApiBaseUrl } from '../api/api-client';

export interface MovimientosFilters {
  espacioId?: number;
  productoId?: number;
  tipo?: TipoMovimiento;
  desde?: string;
  hasta?: string;
  skip?: number;
  limit?: number;
}

export interface PaginatedMovimientosResponse {
  items: MovimientoDetalleResponse[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

@Injectable({ providedIn: 'root' })
export class MovimientosService {
  private http = inject(HttpClient);
  private baseUrl = getApiBaseUrl() + '/movimientos';

  getMovimientos(filters: MovimientosFilters = {}): Observable<MovimientoDetalleResponse[]> {
    const url = new URL(this.baseUrl, window.location.origin);
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        // Convert camelCase to snake_case for query params
        const paramKey = key.replace(/([A-Z])/g, '_$1').toLowerCase();
        url.searchParams.set(paramKey, String(value));
      }
    });
    return this.http.get<MovimientoDetalleResponse[]>(url.toString());
  }

  getMovimiento(id: number): Observable<MovimientoDetalleResponse> {
    return this.http.get<MovimientoDetalleResponse>(`${this.baseUrl}/${id}`);
  }
}