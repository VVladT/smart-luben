import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  EspacioCreate,
  EspacioUpdate,
  EspacioResponse,
  EspacioConProductoResponse,
  EstadoEspacio,
  ReponerRequest,
  MovimientoDetalleResponse,
} from '../api/generated/types';
import { getApiBaseUrl } from '../api/api-client';

@Injectable({ providedIn: 'root' })
export class EspaciosService {
  private http = inject(HttpClient);
  private baseUrl = getApiBaseUrl() + '/espacios';

  getEspacios(): Observable<EspacioConProductoResponse[]> {
    return this.http.get<EspacioConProductoResponse[]>(this.baseUrl);
  }

  getEspacio(id: number): Observable<EspacioConProductoResponse> {
    return this.http.get<EspacioConProductoResponse>(`${this.baseUrl}/${id}`);
  }

  createEspacio(espacio: EspacioCreate): Observable<EspacioResponse> {
    return this.http.post<EspacioResponse>(this.baseUrl, espacio);
  }

  updateEspacio(id: number, espacio: EspacioUpdate): Observable<EspacioResponse> {
    return this.http.put<EspacioResponse>(`${this.baseUrl}/${id}`, espacio);
  }

  deleteEspacio(id: number): Observable<EspacioResponse> {
    return this.http.delete<EspacioResponse>(`${this.baseUrl}/${id}`);
  }

  reponerEspacio(espacioId: number, request: ReponerRequest): Observable<MovimientoDetalleResponse> {
    return this.http.post<MovimientoDetalleResponse>(`${this.baseUrl}/${espacioId}/reponer`, request);
  }

  liberarEspacio(espacioId: number): Observable<MovimientoDetalleResponse> {
    return this.http.post<MovimientoDetalleResponse>(`${this.baseUrl}/${espacioId}/liberar`, {});
  }
}