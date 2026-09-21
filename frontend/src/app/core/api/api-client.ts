import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpHeaders, HttpInterceptorFn, HttpRequest, HttpHandlerFn, provideHttpClient, withInterceptors } from '@angular/common/http';
import { environment } from '../../../environments/environment';

export function provideApiClient() {
  return provideHttpClient(
    withInterceptors([apiInterceptor])
  );
}

export const apiInterceptor: HttpInterceptorFn = (req: HttpRequest<unknown>, next: HttpHandlerFn) => {
  const baseUrl = environment.apiUrl || '';
  if (!req.url.startsWith('http') && !req.url.startsWith('/api')) {
    const apiReq = req.clone({
      url: `${baseUrl}${req.url}`,
      headers: new HttpHeaders({
        'Content-Type': 'application/json',
        ...req.headers.keys().reduce((acc, key) => ({ ...acc, [key]: req.headers.get(key)! }), {}),
      }),
    });
    return next(apiReq);
  }
  return next(req);
};

export function getApiBaseUrl(): string {
  return environment.apiUrl || '';
}