import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { QRCodeComponent } from 'angularx-qrcode';
import { NavbarComponent } from '../../shared/navbar.component';

@Component({
  selector: 'sl-ar-access-page',
  standalone: true,
  imports: [CommonModule, NavbarComponent, QRCodeComponent],
  template: `
    <div class="min-h-screen bg-gray-50">
      <sl-navbar />
      <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div class="mb-8">
          <h1 class="text-3xl font-bold text-gray-900">Experiencia AR</h1>
          <p class="text-gray-500 mt-1">Visualiza la disposición del mostrador en realidad aumentada</p>
        </div>

        @if (redireccionando()) {
          <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
            <p class="text-gray-600">Abriendo la experiencia AR...</p>
          </div>
        } @else {
          <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 md:p-8">
            <div class="flex flex-col md:flex-row items-center gap-8">
              <div class="shrink-0 bg-white p-4 border border-gray-200 rounded-xl">
                <qrcode
                  [qrdata]="arUrl()"
                  [width]="220"
                  [errorCorrectionLevel]="'M'"
                />
              </div>
              <div class="flex-1">
                <h2 class="text-lg font-semibold text-gray-900 mb-2">Escanea con tu móvil</h2>
                <ol class="list-decimal list-inside space-y-2 text-sm text-gray-600">
                  <li>Escanea el código QR en pantalla.</li>
                  <li>Habilita los permisos solicitados.</li>
                  <li>Enfoca los marcadores del mostrador (E01–E04) para ver los productos.</li>
                </ol>
                <p class="mt-3 text-xs text-gray-400 break-all">{{ arUrl() }}</p>
                <a
                  [href]="arUrl()"
                  class="inline-block mt-4 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
                >
                  Abrir de todos modos
                </a>
              </div>
            </div>
          </div>
        }
      </main>
    </div>
  `,
  styles: ``,
})
export class ArAccessPageComponent implements OnInit {
  readonly redireccionando = signal(false);
  readonly arUrl = signal('');

  ngOnInit() {
    const url = `${window.location.origin}/ar/`;
    this.arUrl.set(url);
    if (this.esCompatibleAR()) {
      this.redireccionando.set(true);
      window.location.href = url;
    }
  }

  /** Compatible = dispositivo móvil con cámara. Sin chequeo de contexto
   * seguro: la cámara se negocia en la propia experiencia. */
  esCompatibleAR(): boolean {
    if (typeof navigator === 'undefined') return false;
    const ua = navigator.userAgent || '';
    const esMovil = /Android|iPhone|iPad|iPod|Mobile/i.test(ua);
    const tieneCamara = !!navigator.mediaDevices?.getUserMedia;
    return esMovil && tieneCamara;
  }
}
