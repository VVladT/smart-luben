// modelRegistry.js - Model loading, caching, hot-swap, fallback

import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import * as THREE from 'three';

const loader = new GLTFLoader();
THREE.ColorManagement.enabled = false;

export class ModelRegistry {
  #loaded = new Map();        // producto_id -> THREE.Group (cached master)
  #loading = new Map();       // producto_id -> Promise (dedupe concurrent loads)
  #fallbackModel = null;      // Local placeholder
  #fallbackLoading = null;

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

  async getModel(producto) {
    const cached = this.#loaded.get(producto.id);
    if (cached && cached.userData.version === producto.version) {
      return cached;
    }

    // Dedupe concurrent loads
    if (this.#loading.has(producto.id)) {
      return this.#loading.get(producto.id);
    }

    const promise = this.#loadModel(producto);
    this.#loading.set(producto.id, promise);
    return promise;
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
      this.#loading.delete(producto.id);
      console.log('[ModelRegistry] Loaded:', producto.id, 'height:', model.userData.yOffset.toFixed(2));
      return model;
    } catch (err) {
      console.error('[ModelRegistry] Failed to load', producto.id, ':', err.message);
      this.#loading.delete(producto.id);
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

  // Preload multiple products
  async preload(productos) {
    await Promise.all(productos.map(p => this.getModel(p).catch(err => {
      console.warn('[ModelRegistry] Preload failed for', p.id, err.message);
    })));
  }
}

export const modelRegistry = new ModelRegistry();