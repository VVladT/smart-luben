import { Component, input, computed } from '@angular/core';

@Component({
  selector: 'sl-loading-spinner',
  standalone: true,
  template: `
    <div class="flex items-center justify-center" [class]="sizeClass()">
      <svg
        class="animate-spin text-indigo-600"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        [attr.width]="sizeNum()"
        [attr.height]="sizeNum()"
      >
        <circle
          class="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          stroke-width="4"
        />
        <path
          class="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
      @if (message()) {
        <span class="ml-2 text-gray-600 text-sm">{{ message() }}</span>
      }
    </div>
  `,
  styles: ``,
})
export class LoadingSpinnerComponent {
  readonly size = input<string | number>('24');
  readonly message = input<string>('');

  readonly sizeNum = computed(() => {
    const s = this.size();
    return typeof s === 'string' ? parseInt(s, 10) : s;
  });

  readonly sizeClass = computed(() => {
    const s = this.sizeNum();
    if (s >= 48) return 'h-16';
    if (s >= 32) return 'h-12';
    return 'h-8';
  });
}