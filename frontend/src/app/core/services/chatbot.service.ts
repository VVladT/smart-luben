import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface ChatRequest {
  message: string;
}

export interface ChatResponse {
  response: string;
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