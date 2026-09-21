import { Component, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'sl-error-message',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (message()) {
      <div
        class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4 flex items-center justify-between"
        role="alert"
      >
        <div class="flex items-center">
          <svg
            class="w-5 h-5 mr-2"
            fill="currentColor"
            viewBox="0 0 20 20"
            aria-hidden="true"
          >
            <path
              fill-rule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
              clip-rule="evenodd"
            />
          </svg>
          <span>{{ message() }}</span>
        </div>
        @if (dismissible()) {
          <button
            (click)="dismiss.emit()"
            class="ml-4 text-red-500 hover:text-red-700 font-bold text-xl leading-none"
            aria-label="Cerrar"
          >
            &times;
          </button>
        }
      </div>
    }
  `,
  styles: ``,
})
export class ErrorMessageComponent {
  readonly message = input<string | null>('');
  readonly dismissible = input<boolean>(false);
  readonly dismiss = output<void>();
}