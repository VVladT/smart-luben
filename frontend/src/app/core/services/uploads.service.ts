import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, switchMap, map } from 'rxjs';
import { getApiBaseUrl } from '../api/api-client';

export type UploadTipo = 'modelo' | 'imagen';

export interface PresignResponse {
  upload_url: string;
  public_url: string;
  bucket: string;
  object_path: string;
}

@Injectable({ providedIn: 'root' })
export class UploadsService {
  private http = inject(HttpClient);
  private baseUrl = getApiBaseUrl() + '/uploads';

  presign(tipo: UploadTipo, file: File): Observable<PresignResponse> {
    return this.http.post<PresignResponse>(`${this.baseUrl}/presign`, {
      tipo,
      filename: file.name,
      content_type: file.type,
      size: file.size,
    });
  }

  /** Flujo completo: presign + PUT directo a S3. Emite la URL pública final. */
  upload(tipo: UploadTipo, file: File): Observable<string> {
    return this.presign(tipo, file).pipe(
      switchMap((presigned) =>
        this.http
          .put(presigned.upload_url, file, {
            headers: {
              'Content-Type': file.type,
              // Requerido si la URL pasa por un túnel ngrok free
              'ngrok-skip-browser-warning': 'true',
            },
            responseType: 'text',
          })
          .pipe(map(() => presigned.public_url)),
      ),
    );
  }
}
