// Tests unitarios AR (node --test). Solo lógica pura: sin DOM, sin 8th Wall,
// sin red (fetch y window se stubbean antes de importar los módulos).

import { describe, it, before, after } from 'node:test';
import assert from 'node:assert/strict';

before(() => {
  globalThis.window = { addEventListener() {}, parent: null };
  if (!globalThis.requestAnimationFrame) {
    globalThis.requestAnimationFrame = (cb) => setTimeout(() => cb(performance.now()), 16);
    globalThis.cancelAnimationFrame = (id) => clearTimeout(id);
  }
  globalThis.fetch = async () => {
    throw new Error('sin red en tests');
  };
});

const { targetTracker } = await import('../targetTracker.js');
const { configManager } = await import('../configManager.js');

after(() => {
  targetTracker.destroy();
  configManager.stopPolling();
});

describe('targetTracker', () => {
  it('no muestra nada sin asignaciones', () => {
    assert.equal(targetTracker.debeMostrar('E01'), false);
    assert.equal(targetTracker.getInstance('E01'), undefined);
  });

  it('onTargetFound sin asignación no crea instancia', async () => {
    await targetTracker.onTargetFound({
      detail: { name: 'E01', position: { x: 0, y: 0, z: 0 }, rotation: { x: 0, y: 0, z: 0, w: 1 } },
    });
    assert.equal(targetTracker.getInstance('E01'), undefined);
  });

  it('onTargetLost desconocido no revienta', () => {
    targetTracker.onTargetLost({ detail: { name: 'E99' } });
    assert.equal(targetTracker.getInstance('E99'), undefined);
  });

  it('desvanecer sin instancia es noop', () => {
    targetTracker.desvanecer('E01');
    assert.equal(targetTracker.getInstance('E01'), undefined);
  });

  it('setTuning acepta parciales', () => {
    targetTracker.setTuning({ stableMs: 10, pendingTimeoutMs: 50 });
    targetTracker.setTuning({});
  });
});

describe('configManager', () => {
  it('sin API queda no-listo pero usable', () => {
    assert.equal(configManager.ready, false);
    assert.equal(configManager.getProductForEspacio('E01'), null);
  });

  it('updateAssignment es local y reversible', () => {
    configManager.updateAssignment('E01', 1);
    // Sin productos cargados no resuelve, pero no revienta
    assert.equal(configManager.getProductForEspacio('E01'), null);
  });
});
