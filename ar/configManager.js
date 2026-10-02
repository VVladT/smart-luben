// configManager.js - Self-initializing configuration from API

import { apiClient } from './api/client.js';

// Poll de cambios (hot-swap). 10s: frescura razonable sin cargar al backend
// (≈6 req/min por dispositivo, queries triviales, vacío si no hay cambios).
const POLL_INTERVAL_MS = 10000;

export class ConfigManager {
  #espacios = [];                    // All 4 spaces with target config
  #assignments = new Map();          // espacio_codigo -> producto_id
  #products = new Map();             // producto_id -> Producto
  #ready = false;
  #listeners = new Set();
  #pollingInterval = null;

  constructor() {
    // Initialize from API on construction
    this.initialize();
    this.startPolling();
  }

  async initialize() {
    try {
      console.log('[ConfigManager] Loading config from API...');
      const [productos, espacios] = await Promise.all([
        apiClient.getProductos(),
        apiClient.getEspacios()
      ]);

      this.#espacios = espacios;
      this.#products.clear();
      this.#assignments.clear();

      productos.forEach(p => this.#products.set(p.id, p));
      espacios.forEach(e => {
        if (e.espacio.producto_actual_id) {
          this.#assignments.set(e.espacio.codigo, e.espacio.producto_actual_id);
        }
      });

      this.#ready = true;
      this.#notify();
      console.log('[ConfigManager] Initialized with', this.#espacios.length, 'espacios,', this.#assignments.size, 'assignments,', this.#products.size, 'products');
    } catch (err) {
      console.error('[ConfigManager] Failed to initialize:', err);
    }
  }

  get espacios() { return this.#espacios; }
  get assignments() { return this.#assignments; }
  get products() { return this.#products; }
  get ready() { return this.#ready; }

  onChange(listener) {
    this.#listeners.add(listener);
    return () => this.#listeners.delete(listener);
  }

  #notify() {
    this.#listeners.forEach(l => l(this.getSnapshot()));
  }

  getSnapshot() {
    return {
      espacios: this.#espacios,
      assignments: new Map(this.#assignments),
      products: new Map(this.#products),
    };
  }

  // Poll for changes from API
  startPolling() {
    if (this.#pollingInterval) return;

    this.#pollingInterval = setInterval(async () => {
      try {
        // Build version map for change detection
        const versions = {};
        this.#products.forEach((p, id) => { versions[id] = p.version; });
        const assignments = {};
        this.#assignments.forEach((pid, codigo) => { assignments[codigo] = pid; });
        const estados = {};
        this.#espacios.forEach(e => {
          if (e.espacio?.codigo) estados[e.espacio.codigo] = e.espacio.estado;
        });

        const data = await apiClient.pollForChanges(versions, assignments, estados);
        if (data.changes && data.changes.length > 0) {
          await this.#aplicarCambios(data.changes);
        }
      } catch (err) {
        console.warn('[ConfigManager] Poll failed:', err);
      }
    }, POLL_INTERVAL_MS);
  }

  async #aplicarCambios(changes) {
    let productosRefrescados = false;
    for (const ch of changes) {
      if (ch.type === 'producto_update') {
        const { modelRegistry } = await import('./modelRegistry.js');
        modelRegistry.invalidate(ch.productoId);
        productosRefrescados = true;
      } else if (ch.type === 'espacio_assignment' && ch.espacio_codigo) {
        if (ch.productoId) {
          this.#assignments.set(ch.espacio_codigo, ch.productoId);
        } else {
          this.#assignments.delete(ch.espacio_codigo);
        }
      } else if (ch.type === 'espacio_estado' && ch.espacio_codigo) {
        // Refrescar el estado local: el tracker decide mostrar/retirar con
        // datos frescos (si no, debeMostrar() usaría la snapshot inicial).
        const entry = this.getEspacio(ch.espacio_codigo);
        if (entry?.espacio) entry.espacio.estado = ch.estado;
      }
    }
    if (productosRefrescados) {
      const productos = await apiClient.getProductos();
      this.#products.clear();
      productos.forEach(p => this.#products.set(p.id, p));
    }
    this.#notify();
  }

  stopPolling() {
    if (this.#pollingInterval) {
      clearInterval(this.#pollingInterval);
      this.#pollingInterval = null;
    }
  }

  // Get product for a specific espacio
  getProductForEspacio(espacioCodigo) {
    const productoId = this.#assignments.get(espacioCodigo);
    if (!productoId) return null;
    return this.#products.get(productoId) || null;
  }

  // Get espacio entry by code (items are { espacio, targetConfig })
  getEspacio(espacioCodigo) {
    return this.#espacios.find(e => e.espacio?.codigo === espacioCodigo) || null;
  }

  // Update assignment (for manual testing)
  updateAssignment(espacioCodigo, productoId) {
    this.#assignments.set(espacioCodigo, productoId);
    this.#notify();
  }
}

export const configManager = new ConfigManager();