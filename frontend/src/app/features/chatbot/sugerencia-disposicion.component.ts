import { Component, computed, inject, input, output, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { catchError, concatMap, from, of, toArray } from 'rxjs';
import { SugerenciaRecomendacion } from '../../core/services/chatbot.service';
import { EspaciosService } from '../../core/services/espacios.service';
import { resolveStorageUrl } from '../../core/api/api-client';

@Component({
  selector: 'sl-sugerencia-disposicion',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="mt-3 rounded-xl border border-indigo-100 bg-indigo-50/50 p-3">
      <p class="text-xs font-semibold text-indigo-800 uppercase tracking-wide mb-2">
        Disposición sugerida
      </p>
      <div class="grid grid-cols-2 sm:grid-cols-3 gap-2">
        @for (rec of recommendations(); track rec.espacio_id) {
          <div class="bg-white rounded-lg border border-gray-200 overflow-hidden">
            @if (imagenRec(rec)) {
              <img
                [src]="imagenRec(rec)"
                [alt]="rec.producto_nombre"
                class="w-full h-16 object-cover"
                loading="lazy"
              />
            }
            <div class="p-2">
              <span class="inline-block px-1.5 py-0.5 text-[10px] font-mono font-semibold bg-indigo-100 text-indigo-700 rounded">
                {{ rec.espacio_codigo }}
              </span>
              <p class="text-xs font-medium text-gray-900 truncate mt-1" [title]="rec.producto_nombre">
                {{ rec.producto_nombre }}
              </p>
              <span
                class="inline-block mt-1 px-1.5 py-0.5 text-[10px] font-semibold rounded-full"
                [class]="confianzaClasses(rec.score)"
              >
                {{ confianzaLabel(rec.score) }}
              </span>
            </div>
          </div>
        }
      </div>
      @if (resultado()) {
        <p class="text-xs text-gray-600 mt-2">{{ resultado() }}</p>
      }
      <button
        type="button"
        (click)="aplicar()"
        [disabled]="aplicada() || aplicando()"
        class="mt-2 w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white py-2 px-3 rounded-lg text-sm font-medium transition-colors"
      >
        @if (aplicada()) {
          Aplicada ✓
        } @else if (aplicando()) {
          Aplicando...
        } @else {
          Aplicar disposición
        }
      </button>
    </div>
  `,
  styles: ``,
})
export class SugerenciaDisposicionComponent {
  private espaciosService = inject(EspaciosService);

  readonly recommendations = input.required<SugerenciaRecomendacion[]>();

  /** Avisa al padre cuando la aplicación termina (ok: n planificados, fallos: n omitidos). */
  readonly aplicado = output<{ ok: number; fallos: number }>();

  readonly aplicando = signal(false);
  readonly aplicada = signal(false);
  readonly resultado = signal<string | null>(null);

  imagenRec(rec: SugerenciaRecomendacion): string | null {
    return resolveStorageUrl(rec.producto_imagen_url);
  }

  private maxScore = computed(() =>
    Math.max(0, ...this.recommendations().map((r) => r.score ?? 0)),
  );

  confianzaLabel(score: number): string {
    const max = this.maxScore();
    if (max <= 0) return 'baja';
    const rel = score / max;
    if (rel >= 0.8) return 'alta';
    if (rel >= 0.4) return 'media';
    return 'baja';
  }

  confianzaClasses(score: number): string {
    const nivel = this.confianzaLabel(score);
    if (nivel === 'alta') return 'bg-green-100 text-green-700';
    if (nivel === 'media') return 'bg-amber-100 text-amber-700';
    return 'bg-gray-100 text-gray-600';
  }

  aplicar(): void {
    const recs = this.recommendations();
    if (recs.length === 0 || this.aplicada() || this.aplicando()) {
      return;
    }

    this.aplicando.set(true);
    this.resultado.set(null);

    from(recs)
      .pipe(
        concatMap((rec) =>
          this.espaciosService
            .planificarEspacio(rec.espacio_id, { producto_id: rec.producto_id })
            .pipe(catchError(() => of(null))),
        ),
        toArray(),
      )
      .subscribe((respuestas) => {
        const ok = respuestas.filter((r) => r !== null).length;
        const fallos = respuestas.length - ok;

        this.aplicando.set(false);
        this.aplicada.set(fallos === 0);
        this.resultado.set(
          fallos === 0
            ? `Plan aplicado en ${ok} espacio(s): ahora figuran como pendientes de reposición.`
            : `${ok} planificado(s), ${fallos} omitido(s) (ya no estaban libres). Revisa el mostrador.`,
        );
        this.aplicado.emit({ ok, fallos });
      });
  }
}
