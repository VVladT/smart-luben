import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpInterceptorFn, HttpRequest, HttpHandlerFn, provideHttpClient, withInterceptors } from '@angular/common/http';
import { environment } from '../../../environments/environment';

export function provideApiClient() {
  return provideHttpClient(
    withInterceptors([apiInterceptor])
  );
}

export const apiInterceptor: HttpInterceptorFn = (req: HttpRequest<unknown>, next: HttpHandlerFn) => {
  // Header anti-interstitial para túneles ngrok free (ignorado en el resto).
  const ngrokHeaders = { 'ngrok-skip-browser-warning': 'true' };
  const baseUrl = environment.apiUrl || '';
  if (!req.url.startsWith('http') && !req.url.startsWith('/api')) {
    const apiReq = req.clone({
      url: `${baseUrl}${req.url}`,
      headers: new HttpHeaders({
        'Content-Type': 'application/json',
        ...ngrokHeaders,
        ...req.headers.keys().reduce((acc, key) => ({ ...acc, [key]: req.headers.get(key)! }), {}),
      }),
    });
    return next(apiReq);
  }
  return next(req.clone({
    headers: new HttpHeaders({
      ...ngrokHeaders,
      ...req.headers.keys().reduce((acc, key) => ({ ...acc, [key]: req.headers.get(key)! }), {}),
    }),
  }));
};

export function getApiBaseUrl(): string {
  return environment.apiUrl || '';
}

/**
 * Resuelve una URL de objeto (relativa como /api/storage/... o absoluta)
 * contra la base de API en uso. Así dev y móvil comparten los mismos datos.
 */
export function resolveStorageUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  if (/^https?:\/\//i.test(url)) return url;
  const base = getApiBaseUrl() || (typeof window !== 'undefined' ? window.location.origin : '');
  try {
    return new URL(url, base || '/').href;
  } catch {
    return url;
  }
}