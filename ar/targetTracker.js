// targetTracker.js - Tracks 4 spaces, handles assignments, offsets, hot-swap

import { messageBridge, MessageType } from './messageBridge.js';
import { configManager } from './configManager.js';
import { modelRegistry } from './modelRegistry.js';
import * as THREE from 'three';

// Tracking stabilization tuning (module defaults, overridable per instance for tests)
const DEFAULT_LOST_GRACE_MS = 1200;    // keep last pose visible this long after imagelost
const DEFAULT_STABLE_MS = 300;         // pose must hold still this long before showing
const DEFAULT_POS_EPSILON = 0.02;      // meters
const DEFAULT_ROT_EPSILON = 0.035;     // radians (~2 deg)
const DEFAULT_BIG_MOVE_POS = 0.05;     // above this vs frozen pose -> hide immediately
const DEFAULT_BIG_MOVE_ROT = 0.09;     // radians (~5 deg)
const DEFAULT_PENDING_TIMEOUT_MS = 3000; // never-stable fallback: add anyway

export class TargetTracker {
  #activeInstances = new Map();    // espacio_codigo -> THREE.Group (active instance)
  #currentDetails = new Map();     // espacio_codigo -> last detail (for updates)
  #generations = new Map();        // espacio_codigo -> int (invalidates stale async work)
  #pendingRemoval = new Map();    // espacio_codigo -> timeout id (deferred hide)
  #pendingAdd = new Map();        // espacio_codigo -> pending stabilization state
  #scene = null;
  #configManager = configManager;
  #modelRegistry = modelRegistry;
  #unsubscribeConfig = null;
  #lostGraceMs = DEFAULT_LOST_GRACE_MS;
  #stableMs = DEFAULT_STABLE_MS;
  #posEpsilon = DEFAULT_POS_EPSILON;
  #rotEpsilon = DEFAULT_ROT_EPSILON;
  #bigMovePos = DEFAULT_BIG_MOVE_POS;
  #bigMoveRot = DEFAULT_BIG_MOVE_ROT;
  #pendingTimeoutMs = DEFAULT_PENDING_TIMEOUT_MS;
  #ultimasAsignaciones = new Map(); // última snapshot para diff de hot-swap
  #ultimasVersiones = new Map(); // productoId -> version (hot-swap de datos)
  #desvaneciendo = new Map(); // espacioCode -> { instance, inicio } (fade-out)
  #rafId = null;

  static FADE_MS = 600;

  // Solo se muestra modelo si el espacio está libre con producto (pendiente).
  // Ocupado (confirmado físicamente) u otro caso: sin overlay.
  debeMostrar(espacioCode) {
    const entry = this.#configManager.getEspacio(espacioCode);
    const libre = entry?.espacio?.estado === 'libre';
    return libre && this.#configManager.assignments.has(espacioCode);
  }

  constructor() {
    this.#unsubscribeConfig = configManager.onChange(this.#onConfigChange.bind(this));
  }

  setScene(scene) {
    this.#scene = scene;
  }

  // Next generation token for a space; async work holding an older token is discarded
  #bumpGeneration(espacioCode) {
    const next = (this.#generations.get(espacioCode) || 0) + 1;
    this.#generations.set(espacioCode, next);
    return next;
  }

  // Remove the active instance from the scene. Clones share geometries/materials
  // with the cached master, so scene.remove() is enough — no dispose needed.
  #removeInstance(espacioCode) {
    this.#cancelarFade(espacioCode);
    const instance = this.#activeInstances.get(espacioCode);
    if (instance) {
      this.#scene?.remove(instance);
      this.#activeInstances.delete(espacioCode);
    }
  }

  // Inicia fade-out (opacidad + escala) y retira al terminar.
  desvanecer(espacioCode) {
    const instance = this.#activeInstances.get(espacioCode);
    if (!instance) return;
    if (this.#desvaneciendo.has(espacioCode)) return;
    // Los clones comparten materiales con el master cacheado: clonar para
    // no transparentar otras instancias. Se liberan al terminar el fade.
    instance.traverse(child => {
      if (child.isMesh) {
        if (Array.isArray(child.material)) {
          child.material = child.material.map(m => m.clone());
        } else if (child.material) {
          child.material = child.material.clone();
        }
        const mats = Array.isArray(child.material) ? child.material : [child.material];
        mats.forEach(m => {
          m.transparent = true;
        });
      }
    });
    // Congelar escala base para interpolar hacia 0.9x
    instance.userData._escalaBase = instance.scale.x;
    this.#desvaneciendo.set(espacioCode, { instance, inicio: performance.now() });
    this.#asegurarLoopFade();
  }

  #cancelarFade(espacioCode) {
    this.#desvaneciendo.delete(espacioCode);
    if (this.#desvaneciendo.size === 0 && this.#rafId !== null) {
      cancelAnimationFrame(this.#rafId);
      this.#rafId = null;
    }
  }

  #asegurarLoopFade() {
    if (this.#rafId !== null) return;
    const paso = () => {
      const ahora = performance.now();
      for (const [codigo, { instance, inicio }] of [...this.#desvaneciendo]) {
        const t = Math.min(1, (ahora - inicio) / TargetTracker.FADE_MS);
        const resto = 1 - t;
        instance.traverse(child => {
          if (child.isMesh) {
            const mats = Array.isArray(child.material) ? child.material : [child.material];
            mats.forEach(m => {
              m.opacity = resto;
            });
          }
        });
        const base = instance.userData._escalaBase || 1;
        const s = base * (0.9 + 0.1 * resto);
        instance.scale.set(s, s, s);
        if (t >= 1) {
          this.#desvaneciendo.delete(codigo);
          instance.traverse(child => {
            if (child.isMesh) {
              const mats = Array.isArray(child.material) ? child.material : [child.material];
              mats.forEach(m => m.dispose?.());
            }
          });
          if (this.#activeInstances.get(codigo) === instance) {
            this.#scene?.remove(instance);
            this.#activeInstances.delete(codigo);
          }
        }
      }
      if (this.#desvaneciendo.size === 0) {
        this.#rafId = null;
        return;
      }
      this.#rafId = requestAnimationFrame(paso);
    };
    this.#rafId = requestAnimationFrame(paso);
  }

  // Override stabilization tuning (used by tests to shrink real-time waits)
  setTuning(partial = {}) {
    if (partial.lostGraceMs !== undefined) this.#lostGraceMs = partial.lostGraceMs;
    if (partial.stableMs !== undefined) this.#stableMs = partial.stableMs;
    if (partial.posEpsilon !== undefined) this.#posEpsilon = partial.posEpsilon;
    if (partial.rotEpsilon !== undefined) this.#rotEpsilon = partial.rotEpsilon;
    if (partial.bigMovePos !== undefined) this.#bigMovePos = partial.bigMovePos;
    if (partial.bigMoveRot !== undefined) this.#bigMoveRot = partial.bigMoveRot;
    if (partial.pendingTimeoutMs !== undefined) this.#pendingTimeoutMs = partial.pendingTimeoutMs;
  }

  #cancelPendingRemoval(espacioCode) {
    const id = this.#pendingRemoval.get(espacioCode);
    if (id !== undefined) {
      clearTimeout(id);
      this.#pendingRemoval.delete(espacioCode);
    }
  }

  #clearPendingAdd(espacioCode) {
    const pending = this.#pendingAdd.get(espacioCode);
    if (pending) {
      clearTimeout(pending.timer);
      this.#pendingAdd.delete(espacioCode);
    }
  }

  #scheduleRemoval(espacioCode) {
    this.#cancelPendingRemoval(espacioCode);
    const id = setTimeout(() => {
      this.#pendingRemoval.delete(espacioCode);
      this.#removeInstance(espacioCode);
      this.#currentDetails.delete(espacioCode);
      this.#clearPendingAdd(espacioCode);
    }, this.#lostGraceMs);
    this.#pendingRemoval.set(espacioCode, id);
  }

  // 8th Wall event details carry plain {x,y,z} / {x,y,z,w} payloads, not THREE
  // instances — never call THREE methods on `detail` itself. Normalize first.
  // (copying FROM plain objects INTO three objects via .copy() is safe.)
  #vec(p) {
    return new THREE.Vector3(p.x, p.y, p.z);
  }

  #quat(r) {
    return new THREE.Quaternion(r.x, r.y, r.z, r.w);
  }

  // True when the new pose moved far from the frozen instance (stale pose: hide now)
  #poseDeltaBig(instance, detail) {
    return instance.position.distanceTo(detail.position) > this.#bigMovePos ||
      instance.quaternion.angleTo(detail.rotation) > this.#bigMoveRot;
  }

  #onConfigChange(snapshot) {
    // Hot-swap en vivo: si cambió la asignación de un espacio visible,
    // recargar su modelo sin esperar al próximo imagefound.
    const previas = this.#ultimasAsignaciones || new Map();
    const actuales = snapshot.assignments || new Map();
    const todas = new Set([...previas.keys(), ...actuales.keys()]);
    for (const codigo of todas) {
      if (previas.get(codigo) !== actuales.get(codigo)) {
        if (this.#activeInstances.has(codigo) || this.#currentDetails.has(codigo)) {
          this.onAssignmentChanged(codigo, actuales.get(codigo));
        }
      }
    }
    this.#ultimasAsignaciones = new Map(actuales);

    // Hot-swap por datos del producto (nuevo .glb, scale, rotación):
    // la versión bumpeada en backend invalida lo visible sin mover la cámara.
    const productos = snapshot.products || new Map();
    for (const [codigo] of this.#activeInstances) {
      const pid = actuales.get(codigo);
      if (pid == null) continue;
      if (this.#ultimasVersiones.get(pid) !== productos.get(pid)?.version) {
        this.onAssignmentChanged(codigo, pid);
      }
    }
    this.#ultimasVersiones = new Map(
      [...productos].map(([id, p]) => [id, p?.version]),
    );

    // Barrido: visibles que dejaron de ser mostrables (ej: se ocupó
    // manteniendo el mismo producto) → fade-out.
    for (const codigo of this.#activeInstances.keys()) {
      if (!this.debeMostrar(codigo)) this.desvanecer(codigo);
    }
  }

  async onTargetFound({ detail }) {
    const espacioCode = detail.name;

    // Sin overlay si no es mostrable (ocupado confirmado, sin plan, etc.)
    if (!this.debeMostrar(espacioCode)) return;

    const productoId = this.#configManager.assignments.get(espacioCode);
    if (!productoId) return;

    const producto = this.#configManager.products.get(productoId);
    if (!producto) return;

    // Invalidate any previous in-flight work for this space
    const gen = this.#bumpGeneration(espacioCode);
    // Tracking is alive again: cancel a scheduled hide
    this.#cancelPendingRemoval(espacioCode);

    // Warm the cache now so the model is ready when stability confirms
    modelRegistry.getModel(producto).catch(() => {});

    const active = this.#activeInstances.get(espacioCode);
    if (active && this.#poseDeltaBig(active, detail)) {
      // Moved a lot: drop the stale frozen pose now, stay hidden until stable
      this.#removeInstance(espacioCode);
    }

    // Re-found while stabilizing (flicker): refresh pose/product but keep the
    // ORIGINAL deadline — restarting the forced-add timer on every found
    // postpones it forever and the model never appears.
    const existing = this.#pendingAdd.get(espacioCode);
    if (existing) {
      existing.detail = detail;
      existing.producto = producto;
      existing.gen = gen;
      existing.stableSince = null;
      existing.lastPos.copy(this.#vec(detail.position));
      existing.lastQuat.copy(this.#quat(detail.rotation));
    } else {
      // First found: start pending add with a hard deadline; nothing shown yet
      const state = {
        detail,
        producto,
        gen,
        stableSince: null,
        lastPos: this.#vec(detail.position),
        lastQuat: this.#quat(detail.rotation),
        timer: setTimeout(() => this.#confirmPendingAdd(espacioCode, true), this.#pendingTimeoutMs),
      };
      this.#pendingAdd.set(espacioCode, state);
    }
    this.#currentDetails.set(espacioCode, detail);

    messageBridge.emit(MessageType.AR_TARGET_FOUND, {
      espacio_codigo: espacioCode,
      producto_id: producto.id
    });
  }

  #tryFallback(espacioCode, detail, gen) {
    // Skip stale fallbacks from a superseded found
    if (gen !== undefined && gen !== this.#generations.get(espacioCode)) return;
    try {
      const fallback = modelRegistry.getFallback();
      const instance = fallback.clone(true);
      this.#removeInstance(espacioCode);
      this.#activeInstances.set(espacioCode, instance);
      this.#applyTransform(instance, detail, { scale: 1, rotation_x: 0 });
      this.#scene.add(instance);
      console.log('[TargetTracker] Using fallback for', espacioCode);
    } catch (err) {
      console.error('[TargetTracker] Fallback also failed', err);
    }
  }

  onTargetUpdated({ detail }) {
    const espacioCode = detail.name;
    this.#currentDetails.set(espacioCode, detail);

    const pending = this.#pendingAdd.get(espacioCode);
    if (pending) {
      // While stabilizing, keep the frozen pose (if any) — no jitter on screen
      this.#trackPendingStability(espacioCode, pending, detail);
      return;
    }

    const instance = this.#activeInstances.get(espacioCode);
    if (!instance) return;

    // En fade-out no se toca el transform (pelearía con la animación)
    if (this.#desvaneciendo.has(espacioCode)) return;

    const productoId = this.#configManager.assignments.get(espacioCode);
    const producto = this.#configManager.products.get(productoId);
    this.#applyTransform(instance, detail, producto);
  }

  #trackPendingStability(espacioCode, pending, detail) {
    const now = Date.now();
    const curPos = this.#vec(detail.position);
    const curQuat = this.#quat(detail.rotation);
    const posDelta = curPos.distanceTo(pending.lastPos);
    const rotDelta = curQuat.angleTo(pending.lastQuat);
    pending.lastPos.copy(curPos);
    pending.lastQuat.copy(curQuat);
    pending.detail = detail;

    if (posDelta <= this.#posEpsilon && rotDelta <= this.#rotEpsilon) {
      if (pending.stableSince === null) {
        pending.stableSince = now;
      } else if (now - pending.stableSince >= this.#stableMs) {
        this.#confirmPendingAdd(espacioCode, false);
      }
    } else {
      pending.stableSince = null;
    }
  }

  // Materialize a pending add. forced=true when the stabilization timeout fired:
  // add anyway so the model never stays invisible forever on marginal tracking.
  async #confirmPendingAdd(espacioCode, forced) {
    const pending = this.#pendingAdd.get(espacioCode);
    if (!pending) return;
    this.#clearPendingAdd(espacioCode);
    const { detail, producto, gen } = pending;

    if (gen !== this.#generations.get(espacioCode)) return;

    // El espacio pudo ocuparse mientras se estabilizaba: no materializar.
    // (Sin este gate, el timer forzado re-agrega el modelo tras cada fade.)
    if (!this.debeMostrar(espacioCode)) return;

    if (forced) {
      console.log('[TargetTracker] Pending add forced (never stabilized)', espacioCode);
    }

    try {
      const model = await modelRegistry.getModel(producto);
      if (gen !== this.#generations.get(espacioCode)) return;
      const instance = model.clone(true);
      this.#removeInstance(espacioCode);
      this.#activeInstances.set(espacioCode, instance);
      this.#currentDetails.set(espacioCode, detail);
      this.#applyTransform(instance, detail, producto);
      this.#scene.add(instance);

      messageBridge.emit(MessageType.AR_MODEL_LOADED, {
        espacio_codigo: espacioCode,
        producto_id: producto.id
      });
    } catch (err) {
      console.error('[TargetTracker] Pending add failed:', err);
      messageBridge.emit(MessageType.AR_MODEL_ERROR, {
        espacio_codigo: espacioCode,
        producto_id: producto.id,
        error: err.message
      });
      this.#tryFallback(espacioCode, detail, gen);
    }
  }

  onTargetLost({ detail }) {
    const espacioCode = detail.name;
    // Invalidate in-flight founds/adds; their pose is stale anyway
    this.#bumpGeneration(espacioCode);
    if (this.#activeInstances.has(espacioCode)) {
      // Defer the hide: a flicker re-found cancels it before anything blinks
      this.#scheduleRemoval(espacioCode);
    }
    // A pending add with no instance survives until its own timeout (brief flicker
    // while stabilizing); an expired grace already cleared everything.
    this.#currentDetails.delete(espacioCode);
    messageBridge.emit(MessageType.AR_TARGET_LOST, { espacio_codigo: espacioCode });
  }

  // Called when assignment changes at runtime
  async onAssignmentChanged(espacioCode, newProductoId) {
    // Dejó de ser mostrable (se ocupó / se quitó el plan): fade-out.
    if (!this.debeMostrar(espacioCode)) {
      this.desvanecer(espacioCode);
      return;
    }
    const gen = this.#bumpGeneration(espacioCode);
    this.#cancelPendingRemoval(espacioCode);
    this.#clearPendingAdd(espacioCode);
    const detail = this.#currentDetails.get(espacioCode);
    if (!detail) return;

    // Remove old instance
    this.#removeInstance(espacioCode);

    // Load new product and show
    const producto = this.#configManager.products.get(newProductoId);
    if (!producto) return;

    try {
      const model = await modelRegistry.getModel(producto);
      if (gen !== this.#generations.get(espacioCode)) return;
      const instance = model.clone(true);
      this.#removeInstance(espacioCode);
      this.#activeInstances.set(espacioCode, instance);
      this.#applyTransform(instance, detail, producto);
      this.#scene.add(instance);

      messageBridge.emit(MessageType.AR_MODEL_LOADED, { 
        espacio_codigo: espacioCode, 
        producto_id: newProductoId 
      });
    } catch (err) {
      console.error('[TargetTracker] Hot-swap failed:', err);
      this.#tryFallback(espacioCode, detail);
    }
  }

  #applyTransform(instance, detail, producto) {
    const trackScale = detail.scale ?? 1;
    const modelScale = producto?.scale || 1;

    // Product rotation offset (radians, XYZ) composed onto the live tracking rotation.
    // copy() resets the cloned master rotation first, so there is no double-apply.
    const offset = new THREE.Quaternion().setFromEuler(
      new THREE.Euler(
        producto?.rotation_x || 0,
        producto?.rotation_y || 0,
        producto?.rotation_z || 0
      )
    );

    instance.position.copy(detail.position);
    instance.quaternion.copy(detail.rotation).multiply(offset);
    const s = trackScale * modelScale;
    instance.scale.set(s, s, s);

    // Apply Y offset so the model sits ON the surface (offset has model scale baked in)
    if (producto?.id != null) {
      const yOffset = this.#modelRegistry.getYOffset(producto.id);
      if (yOffset > 0) {
        const lift = new THREE.Vector3(0, yOffset * trackScale, 0);
        lift.applyQuaternion(detail.rotation);
        instance.position.add(lift);
      }
    }
  }

  // Get current active instance for a space
  getInstance(espacioCode) {
    return this.#activeInstances.get(espacioCode);
  }

  // Cleanup
  destroy() {
    this.#unsubscribeConfig?.();
    if (this.#rafId !== null) {
      cancelAnimationFrame(this.#rafId);
      this.#rafId = null;
    }
    this.#desvaneciendo.clear();
    this.#pendingRemoval.forEach(id => clearTimeout(id));
    this.#pendingRemoval.clear();
    this.#pendingAdd.forEach(p => clearTimeout(p.timer));
    this.#pendingAdd.clear();
    this.#activeInstances.forEach(instance => this.#scene?.remove(instance));
    this.#activeInstances.clear();
    this.#currentDetails.clear();
    this.#generations.clear();
  }
}

// Fix: modelo variable reference
const modelo = null; // placeholder for reference

export const targetTracker = new TargetTracker();