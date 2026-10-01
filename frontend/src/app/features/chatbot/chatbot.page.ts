import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ChatbotService } from '../../core/services/chatbot.service';

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
  ],
  templateUrl: './chatbot.page.html',
  styleUrl: './chatbot.page.scss',
})
export class ChatbotPageComponent {
  private chatbotService = inject(ChatbotService);

  message = '';
  loading = false;

  messages: ChatMessage[] = [
    {
      text: 'Hola, soy LubenBot. Puedo ayudarte con consultas sobre productos, espacios y reposiciones de SmartLuben.',
      sender: 'bot',
    },
  ];

  sendMessage(): void {
    const message = this.message.trim();

    if (!message || this.loading) {
      return;
    }

    this.messages.push({
      text: message,
      sender: 'user',
    });

    this.message = '';
    this.loading = true;

    this.chatbotService
      .sendMessage(message)
      .subscribe({
        next: (response) => {
          this.messages.push({
            text: response.response,
            sender: 'bot',
          });

          this.loading = false;
        },

        error: (error) => {
          console.error(
            'Error al consultar LubenBot:',
            error
          );

          this.messages.push({
            text: 'No se pudo procesar la consulta. Verifica que el servicio de LubenBot esté disponible.',
            sender: 'bot',
          });

          this.loading = false;
        },
      });
  }
}