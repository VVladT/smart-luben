// api/client.js - HTTP API client (browser).
// Same-origin by default (prod: served under /ar/, API under /api/).
// Dev/prototype: the Vite mock plugin serves /api/*. To point at a real
// backend, build/run with VITE_API_BASE_URL (ej: http://localhost:8000).

const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL || '';

async function getJson(path) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'ngrok-skip-browser-warning': 'true' },
  });
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
  return res.json();
}

async function postJson(path, body) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} failed: ${res.status}`);
  return res.json();
}

// Mapeo código backend (E0X) -> target local (space_0X).
// Estático para el prototipo (los targets no cambian).
const TARGET_POR_CODIGO = {
  E01: 'space_01',
  E02: 'space_02',
  E03: 'space_03',
  E04: 'space_04',
};

async function targetConfigLocal(codigo) {
  const target = TARGET_POR_CODIGO[codigo] || codigo.toLowerCase();
  const base = {
    type: 'PLANAR',
    name: codigo,
    imagePath: `targets/${target}_luminance.png`,
    properties: {},
  };
  try {
    const res = await fetch(`targets/${target}.json`);
    if (res.ok) {
      const data = await res.json();
      return {
        type: data.type || base.type,
        name: codigo,
        imagePath: base.imagePath,
        properties: { ...(data.properties || {}) },
      };
    }
  } catch {
    // Sin JSON: config estática mínima (tracking degradado)
  }
  return base;
}

export class ApiClient {
  async getProductos() {
    return getJson('/api/productos');
  }

  async getEspacios() {
    const espacios = await getJson('/api/espacios');
    // El backend devuelve espacios planos; los targets siguen estáticos
    // y locales (deuda técnica): se adjunta el targetConfig por código,
    // con las properties reales del JSON CLI (el engine las requiere).
    const entries = await Promise.all(
      espacios.map(async (e) => ({
        espacio: e,
        targetConfig: await targetConfigLocal(e.codigo),
      })),
    );
    return entries;
  }

  async pollForChanges(versions, assignments = {}, estados = {}) {
    return postJson('/api/sync/changes', { versions, assignments, estados });
  }
}

// Singleton instance
export const apiClient = new ApiClient();
