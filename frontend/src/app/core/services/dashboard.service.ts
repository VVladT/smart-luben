import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { DashboardResumen } from '../api/generated/types';
import { getApiBaseUrl } from '../api/api-client';

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private http = inject(HttpClient);
  private baseUrl = getApiBaseUrl() + '/dashboard';

  getResumen(): Observable<DashboardResumen> {
    return this.http.get<DashboardResumen>(`${this.baseUrl}/resumen`);
  }
}