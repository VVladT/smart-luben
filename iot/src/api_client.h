// Cliente HTTPS para la API SmartLuben (vía ngrok).
// Doctrina: 200 = aplicado; 400 "ya está ..." = convergido (éxito);
// resto/errores de red = reintentar.

#pragma once

#include <Arduino.h>

// Resultado de una llamada a la API
enum ApiResultado {
  API_OK = 0,          // 200
  API_CONVERGIDO = 1,  // 400: ya estaba en ese estado
  API_ERROR = 2,       // red, 404, 5xx, timeout...
};

// POST /api/espacios/{id}/reponer {}  (ocupa con plan o desconocido)
ApiResultado apiReponer(int espacioId);

// POST /api/espacios/{id}/liberar  (libera y elimina producto)
ApiResultado apiLiberar(int espacioId);

// GET /api/espacios -> imprime resumen por Serial. Devuelve true si 200.
bool apiSincronizar();

// GET /api/espacios/{id} -> estado ("libre"/"ocupado") en buf, o false.
bool apiGetEstado(int espacioId, char *buf, size_t buflen);

// Diagnóstico por etapas (DNS -> TCP:443 -> TLS -> HTTPS GET).
// Solo lectura: no crea movimientos. Llamar una vez con WiFi arriba.
void diagnosticarRed();
