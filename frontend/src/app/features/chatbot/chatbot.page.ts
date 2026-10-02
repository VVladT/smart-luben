import { CommonModule } from '@angular/common';
import { Component, ElementRef, inject, signal, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { finalize, timeout } from 'rxjs';
import { ChatbotService, SugerenciasDisposicion } from '../../core/services/chatbot.service';
import { NavbarComponent } from '../../shared/navbar.component';
import { SugerenciaDisposicionComponent } from './sugerencia-disposicion.component';

interface ChatMessage {
  text: string;
  sender: 'user' | 'bot';
  sugerencias?: SugerenciasDisposicion | null;
}

interface ChatMessage {
  text: string;
  sender: 'user' | 'bot';
}

@Component({
  selector: 'sl-chatbot-page',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    NavbarComponent,
    SugerenciaDisposicionComponent,
  ],
  templateUrl: './chatbot.page.html',
  styleUrl: './chatbot.page.scss',
})
export class ChatbotPageComponent {
  private chatbotService = inject(ChatbotService);

  message = '';
  // Señales (no propiedades planas): la app es zoneless y los callbacks
  // HTTP no disparan detección de cambios por sí solos.
  readonly loading = signal(false);

  private scrollContainer = viewChild<ElementRef<HTMLElement>>('scrollContainer');

  private scrollToBottom(): void {
    // Esperar al render antes de medir scrollHeight
    setTimeout(() => {
      const el = this.scrollContainer()?.nativeElement;
      if (el) {
        el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
      }
    });
  }

  messages = signal<ChatMessage[]>([
    {
      text: 'Hola, soy LubenBot. Puedo ayudarte con consultas sobre productos, espacios y reposiciones de SmartLuben.',
      sender: 'bot',
    },
  ]);

  sendMessage(): void {
    const message = this.message.trim();

    if (!message || this.loading()) {
      return;
    }

    this.messages.update((list) => [
      ...list,
      {
        text: message,
        sender: 'user',
      },
    ]);

    this.message = '';
    this.loading.set(true);
    this.scrollToBottom();

    this.chatbotService
      .sendMessage(message)
      .pipe(
        // La respuesta nunca debe quedarse colgada: 60s máx y loading
        // siempre se apaga aunque falle el observable.
        timeout(60000),
        finalize(() => {
          this.loading.set(false);
          this.scrollToBottom();
        }),
      )
      .subscribe({
        next: (response) => {
          this.messages.update((list) => [
            ...list,
            {
              text: response.response,
              sender: 'bot',
              sugerencias: response.sugerencias ?? null,
            },
          ]);
        },

        error: (error) => {
          console.error(
            'Error al consultar LubenBot:',
            error
          );

          this.messages.update((list) => [
            ...list,
            {
              text: 'No se pudo procesar la consulta. Verifica que el servicio de LubenBot esté disponible.',
              sender: 'bot',
            },
          ]);
        },
      });
  }
}