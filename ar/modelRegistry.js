// modelRegistry.js - Model loading, caching, hot-swap, fallback

import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import * as THREE from 'three';

const loader = new GLTFLoader();
THREE.ColorManagement.enabled = false;

export class ModelRegistry {
  #loaded = new Map();        // producto_id -> THREE.Group (cached master)
  #loading = new Map();       // producto_id -> Promise (dedupe concurrent loads)
  #queued = new Map();        // producto_id -> queued load (foreground can reprioritize)
  #queue = [];
  #activeLoads = 0;
  #loadSequence = 0;
  #fallbackModel = null;      // Local placeholder
  #fallbackLoading = null;

  static MAX_CONCURRENT_LOADS = 1;

  constructor() {
    // Preload fallback
    this.#loadFallback();
  }

  async #loadFallback() {
    try {
      // Try to use a simple existing model as fallback, or create primitive
      const gltf = await loader.loadAsync('models/placeholder.glb');
      this.#fallbackModel = gltf.scene;
      this.#setupModel(this.#fallbackModel, { scale: 1, isFallback: true });
    } catch (err) {
      console.warn('[ModelRegistry] Fallback model not found, creating primitive');
      this.#createPrimitiveFallback();
    }
  }

  #createPrimitiveFallback() {
    const geometry = new THREE.BoxGeometry(1, 1, 1);
    const material = new THREE.MeshStandardMaterial({ 
      color: 0xff6b6b, 
      wireframe: true,
      transparent: true,
      opacity: 0.7
    });
    this.#fallbackModel = new THREE.Mesh(geometry, material);
    this.#setupModel(this.#fallbackModel, { scale: 1, isFallback: true });
  }

  #setupModel(model, options = {}) {
    model.scale.set(options.scale || 1, options.scale || 1, options.scale || 1);
    
    const box = new THREE.Box3().setFromObject(model);
    const height = box.max.y - box.min.y;
    
    model.userData = {
      yOffset: height / 2,
      isFallback: options.isFallback || false,
      version: options.version || 'fallback',
      productoId: options.productoId || 'fallback',
    };

    model.traverse(child => {
      if (child.isMesh) {
        child.castShadow = true;
        child.receiveShadow = true;
        child.frustumCulled = false;
      }
    });
  }

  async getModel(producto, { priority = 'foreground' } = {}) {
    const cached = this.#loaded.get(producto.id);
    if (cached && cached.userData.version === producto.version) {
      return cached;
    }

    // Dedupe concurrent loads. If a visible target requests a model that is
    // still queued for preloading, promote it ahead of background work.
    if (this.#loading.has(producto.id)) {
      if (priority === 'foreground') {
        const queued = this.#queued.get(producto.id);
        if (queued) {
          queued.priority = 0;
          this.#sortQueue();
          this.#pumpQueue();
        }
      }
      return this.#loading.get(producto.id);
    }

    let resolveLoad;
    let rejectLoad;
    const promise = new Promise((resolve, reject) => {
      resolveLoad = resolve;
      rejectLoad = reject;
    });
    const task = {
      producto,
      promise,
      resolve: resolveLoad,
      reject: rejectLoad,
      priority: priority === 'background' ? 1 : 0,
      sequence: this.#loadSequence++,
    };
    this.#queue.push(task);
    this.#queued.set(producto.id, task);
    this.#loading.set(producto.id, promise);
    this.#sortQueue();
    this.#pumpQueue();
    return promise;
  }

  #sortQueue() {
    this.#queue.sort((a, b) => a.priority - b.priority || a.sequence - b.sequence);
  }

  #pumpQueue() {
    while (this.#activeLoads < ModelRegistry.MAX_CONCURRENT_LOADS && this.#queue.length) {
      const task = this.#queue.shift();
      const id = task.producto.id;
      this.#queued.delete(id);
      this.#activeLoads += 1;

      this.#loadModel(task.producto)
        .then(task.resolve, task.reject)
        .finally(() => {
          if (this.#loading.get(id) === task.promise) this.#loading.delete(id);
          this.#activeLoads -= 1;
          this.#pumpQueue();
        });
    }
  }

  async #loadModel(producto) {
    try {
      const gltf = await loader.loadAsync(producto.modelo_url);
      const model = gltf.scene;

      this.#setupModel(model, {
        scale: producto.scale || 1,
        version: producto.version || '1',
        productoId: producto.id,
      });

      // Local rotation offset from product config (radians, XYZ order).
      // Composed onto the live tracking rotation in TargetTracker.
      model.rotation.set(
        producto.rotation_x || 0,
        producto.rotation_y || 0,
        producto.rotation_z || 0
      );

      this.#loaded.set(producto.id, model);
      console.log('[ModelRegistry] Loaded:', producto.id, 'height:', model.userData.yOffset.toFixed(2));
      return model;
    } catch (err) {
      console.error('[ModelRegistry] Failed to load', producto.id, ':', err.message);
      return this.getFallback();
    }
  }

  getFallback() {
    if (!this.#fallbackModel) this.#createPrimitiveFallback();
    const fallback = this.#fallbackModel.clone(true);
    fallback.userData = { ...this.#fallbackModel.userData, isFallback: true };
    return fallback;
  }

  // Y offset (half height, product scale baked in) so the model sits ON the target surface
  getYOffset(productoId) {
    return this.#loaded.get(productoId)?.userData?.yOffset || 0;
  }

  // Hot-swap: invalidate cache for a product
  invalidate(productoId) {
    this.#loaded.delete(productoId);
    this.#loading.delete(productoId);
  }

  // Queue preloads one at a time behind visible-target requests.
  async preload(productos) {
    await Promise.all(productos.map(p => this.getModel(p, { priority: 'background' }).catch(err => {
      console.warn('[ModelRegistry] Preload failed for', p.id, err.message);
    })));
  }
}

export const modelRegistry = new ModelRegistry();
