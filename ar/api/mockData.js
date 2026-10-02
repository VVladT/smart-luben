// api/mockData.js - Pure mock data, Node-safe (no fetch, no window).
// Used by the Vite dev plugin to serve /api/* endpoints.
// For MVP integration: replace the plugin with a real backend, no client changes needed.

import { readFileSync } from 'node:fs';

// Transform knobs per product (this is what the real API will send in the MVP).
// To change a product's size/rotation, edit its entry below — no code changes needed:
// - scale: uniform multiplier applied ON TOP of the live tracking scale (1 = no change)
// - rotation_x / rotation_y / rotation_z: local rotation offset in RADIANS (XYZ order),
//   composed onto the live target rotation. Ej: rotation_x: Math.PI / 2 "acuesta" el modelo
//   sobre la superficie (los GLB vienen en Y-up y el target se trackea en otro plano).
export const PRODUCTOS = [
  {
    id: 1,
    nombre: 'Strawberry Cheesecake',
    categoria: 'Postres',
    imagen_url: 'https://images.unsplash.com/photo-1533134242443-d4fd215305ad?w=200',
    modelo_url: 'models/strawberry_cheesecake.glb',
    activo: true,
    version: 'v1.0.0',
    scale: 1.5,
    rotation_x: Math.PI / 2,
  },
  {
    id: 2,
    nombre: 'Croissant',
    categoria: 'Panadería',
    imagen_url: 'https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=200',
    modelo_url: 'models/croissant.glb',
    activo: true,
    version: 'v1.0.0',
    scale: 1.2,
    rotation_x: Math.PI / 2,
  },
  {
    id: 3,
    nombre: 'Empanada',
    categoria: 'Salados',
    imagen_url: 'https://images.unsplash.com/photo-1541592106381-b31e9677c0e5?w=200',
    modelo_url: 'models/empanada.glb',
    activo: true,
    version: 'v1.0.0',
    scale: 1.0,
    rotation_x: Math.PI / 2,
  },
  {
    id: 4,
    nombre: 'Milhojas',
    categoria: 'Postres',
    imagen_url: 'https://images.unsplash.com/photo-1488477181946-6428a0291777?w=200',
    modelo_url: 'models/milhojas.glb',
    activo: true,
    version: 'v1.0.0',
    scale: 8,
    rotation_x: Math.PI / 2,
  },
  {
    id: 5,
    nombre: 'Carrot Cake',
    categoria: 'Postres',
    imagen_url: 'https://images.unsplash.com/photo-1586985289071-0c0e8b8b8b8b?w=200',
    modelo_url: 'models/carrot_cake.glb',
    activo: true,
    version: 'v1.0.0',
    scale: 1.4,
    rotation_x: Math.PI / 2,
  },
  {
    id: 6,
    nombre: 'Red Velvet',
    categoria: 'Postres',
    imagen_url: 'https://images.unsplash.com/photo-1586985289688-ca3cf47d3e6e?w=200',
    modelo_url: 'models/red_velvet.glb',
    activo: true,
    version: 'v1.0.0',
    scale: 1.5,
    rotation_x: Math.PI / 2,
  },
];

const UBICACIONES = {
  space_01: 'Mesa principal',
  space_02: 'Mesa ventana',
  space_03: 'Mesa esquina',
  space_04: 'Barra',
};

// espacio_{id} -> producto_actual_id (hardcoded for prototype)
const ASSIGNMENTS = { 1: 1, 2: 2, 3: 3, 4: 4 };

function targetConfigFor(codigo) {
  // Single source of truth: the CLI-generated JSON on disk.
  // `properties` (crop + geometry) is passed through untouched — the engine
  // requires the real values, never invented ones.
  try {
    const url = new URL(`../assets/targets/${codigo}.json`, import.meta.url);
    const data = JSON.parse(readFileSync(url, 'utf8'));
    return {
      type: data.type || 'PLANAR',
      name: data.name || codigo,
      imagePath: `targets/${codigo}_luminance.png`,
      properties: { ...data.properties },
    };
  } catch (err) {
    console.warn(`[mockData] No JSON for ${codigo}, using defaults:`, err.message);
    return {
      type: 'PLANAR',
      name: codigo,
      imagePath: `targets/${codigo}_luminance.png`,
      properties: {},
    };
  }
}

export function getEspacios() {
  return [1, 2, 3, 4].map((id) => {
    const codigo = `space_0${id}`;
    return {
      espacio: {
        id,
        codigo,
        ubicacion: UBICACIONES[codigo],
        estado: 'libre',
        producto_actual_id: ASSIGNMENTS[id],
      },
      targetConfig: targetConfigFor(codigo),
    };
  });
}

// Poll counter to simulate a version change every 10 polls (hot-swap testing)
let pollCount = 0;

export function pollForChanges() {
  pollCount += 1;
  if (pollCount % 10 === 0) {
    return {
      changes: [
        {
          type: 'producto_update',
          productoId: 1,
          version: `v1.0.${Math.floor(pollCount / 10)}`,
        },
      ],
    };
  }
  return { changes: [] };
}
