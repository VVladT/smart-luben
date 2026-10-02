import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface ChatRequest {
  message: string;
}

export interface SugerenciaRecomendacion {
  espacio_id: number;
  espacio_codigo: string;
  producto_id: number;
  producto_nombre: string;
  producto_categoria?: string;
  producto_imagen_url?: string | null;
  score: number;
  demand_score?: number;
  ranker_score?: number;
  reason?: string;
}

export interface SugerenciasDisposicion {
  recommendations: SugerenciaRecomendacion[];
  disposition: Record<string, string>;
}

export interface ChatResponse {
  response: string;
  sugerencias?: SugerenciasDisposicion | null;
}

@Injectable({ providedIn: 'root' })
export class ChatbotService {
  private http = inject(HttpClient);
  private baseUrl = environment.apiUrl;

  sendMessage(message: string): Observable<ChatResponse> {
    const body: ChatRequest = {
      message,
    };

    return this.http.post<ChatResponse>(
      `${this.baseUrl}/chatbot/chat`,
      body
    );
  }
}