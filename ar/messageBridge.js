// messageBridge.js - postMessage communication bridge

export const MessageType = {
  // Parent -> Iframe
  AR_INIT: 'AR_INIT',
  AR_UPDATE_ASSIGNMENTS: 'AR_UPDATE_ASSIGNMENTS',
  AR_REFRESH_PRODUCTS: 'AR_REFRESH_PRODUCTS',
  AR_SET_POLLING: 'AR_SET_POLLING',
  AR_PAUSE: 'AR_PAUSE',
  AR_RESUME: 'AR_RESUME',

  // Iframe -> Parent
  AR_READY: 'AR_READY',
  AR_TARGET_FOUND: 'AR_TARGET_FOUND',
  AR_TARGET_LOST: 'AR_TARGET_LOST',
  AR_MODEL_LOADED: 'AR_MODEL_LOADED',
  AR_MODEL_ERROR: 'AR_MODEL_ERROR',
  AR_ERROR: 'AR_ERROR',
  AR_POLL_COMPLETE: 'AR_POLL_COMPLETE',
};

export function createMessageBridge() {
  const handlers = new Map();

  function on(type, handler) {
    if (!handlers.has(type)) handlers.set(type, []);
    handlers.get(type).push(handler);
  }

  function off(type, handler) {
    if (!handlers.has(type)) return;
    const arr = handlers.get(type);
    const idx = arr.indexOf(handler);
    if (idx >= 0) arr.splice(idx, 1);
  }

  function emit(type, payload) {
    window.parent?.postMessage({ type, payload }, '*');
  }

  function handleMessage(event) {
    if (!event.data?.type) return;
    const type = event.data.type;
    const payload = event.data.payload;
    const typeHandlers = handlers.get(type) || [];
    typeHandlers.forEach(h => {
      try { h(payload); } catch (err) { console.error(`Handler error for ${type}:`, err); }
    });
  }

  window.addEventListener('message', handleMessage);

  return { on, off, emit, MessageType };
}

export const messageBridge = createMessageBridge();