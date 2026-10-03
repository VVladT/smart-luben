// SmartLuben IoT - Nodo ESP32 con 4 sensores FSR (uno por espacio E01-E04).
//
// Flujo: lectura con histéresis + anti-rebote -> evento confirmado ->
// POST a la API (reponer/liberar). Sin auth en MVP.
// Doctrina: 400 "ya está ..." = convergido (éxito).

#include <Arduino.h>
#include <WiFi.h>

#include "config.h"
#include "api_client.h"

// Pines analógicos (S1..S4 -> E01..E04)
static const int PINES_FSR[] = {32, 33, 34, 35};
static const int ESPACIO_IDS[] = SENSOR_ESPACIO_IDS;
static const int TOTAL_SENSORES = 4;

// Creencia local por sensor
static bool sensorOcupado[TOTAL_SENSORES] = {false, false, false, false};
// Evento pendiente de envío (para reintentos sin perderlo)
static bool eventoPendiente[TOTAL_SENSORES] = {false, false, false, false};
static bool eventoEsOcupado[TOTAL_SENSORES] = {false, false, false, false};
// Contadores de anti-rebote
static int contOcupado[TOTAL_SENSORES] = {0, 0, 0, 0};
static int contLibre[TOTAL_SENSORES] = {0, 0, 0, 0};

static unsigned long tMuestreo = 0;
static unsigned long tWifi = 0;
static unsigned long tReintento = 0;
static unsigned long tResync = 0;
static bool sincronizado = false;

static float leerGramos(int idx) {
  int lectura = analogRead(PINES_FSR[idx]);
  return (lectura / 4095.0f) * 2000.0f;  // Estimación a 2kg
}

static void conectarWifiBloqueante() {
  Serial.printf("WiFi conectando a %s...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  int intentos = 0;
  while (WiFi.status() != WL_CONNECTED && intentos < 40) {
    delay(500);
    Serial.print(".");
    intentos++;
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("WiFi OK, IP=%s\n", WiFi.localIP().toString().c_str());
  } else {
    Serial.println("WiFi FALLO al arranque (se reintentará en loop)");
  }
}

static void mantenerWifi() {
  unsigned long ahora = millis();
  if (WiFi.status() == WL_CONNECTED) return;
  if (ahora - tWifi < (unsigned long)INTERVALO_REINTENTO_WIFI) return;
  tWifi = ahora;
  Serial.println("WiFi reconectando...");
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASS);
}

// Sincroniza la creencia local con la API (arranque). No genera eventos.
// Devuelve true si logró leer los 4 espacios.
static bool sincronizarArranque() {
  Serial.println("Sync inicial con la API...");
  bool todoOk = true;
  for (int i = 0; i < TOTAL_SENSORES; i++) {
    char estado[16] = {0};
    if (apiGetEstado(ESPACIO_IDS[i], estado, sizeof(estado))) {
      sensorOcupado[i] = (strcmp(estado, "ocupado") == 0);
      Serial.printf("  E%02d (S%d): API dice %s\n", ESPACIO_IDS[i], i + 1, estado);
    } else {
      Serial.printf("  E%02d: sync fallo, se asume libre\n", ESPACIO_IDS[i]);
      sensorOcupado[i] = false;
      todoOk = false;
    }
    contOcupado[i] = 0;
    contLibre[i] = 0;
  }
  return todoOk;
}

// Intenta enviar UN evento pendiente. true = resuelto (OK o convergido).
static bool enviarEvento(int idx) {
  int espacioId = ESPACIO_IDS[idx];
  ApiResultado r;
  if (eventoEsOcupado[idx]) {
    r = apiReponer(espacioId);
  } else {
    r = apiLiberar(espacioId);
  }
  if (r == API_OK) {
    Serial.printf("S%d -> evento %s OK\n", idx + 1, eventoEsOcupado[idx] ? "ocupado" : "libre");
    return true;
  }
  if (r == API_CONVERGIDO) {
    Serial.printf("S%d -> ya convergido en API\n", idx + 1);
    return true;
  }
  Serial.printf("S%d -> fallo de red, reintentando...\n", idx + 1);
  return false;
}

static void muestrear() {
  for (int i = 0; i < TOTAL_SENSORES; i++) {
    float g = leerGramos(i);

    if (!sensorOcupado[i]) {
      // Buscando ocupación: supera umbral alto N veces seguidas
      if (g >= UMBRAL_OCUPADO_G) {
        contOcupado[i]++;
      } else {
        contOcupado[i] = 0;
      }
      contLibre[i] = 0;
      if (contOcupado[i] >= DEBOUNCE_LECTURAS) {
        contOcupado[i] = 0;
        sensorOcupado[i] = true;
        eventoPendiente[i] = true;
        eventoEsOcupado[i] = true;
        Serial.printf("S%d OCUPADO (%.0fg) -> evento\n", i + 1, g);
      }
    } else {
      // Buscando liberación: cae bajo umbral bajo N veces seguidas
      if (g <= UMBRAL_LIBRE_G) {
        contLibre[i]++;
      } else {
        contLibre[i] = 0;
      }
      contOcupado[i] = 0;
      if (contLibre[i] >= DEBOUNCE_LECTURAS) {
        contLibre[i] = 0;
        sensorOcupado[i] = false;
        eventoPendiente[i] = true;
        eventoEsOcupado[i] = false;
        Serial.printf("S%d LIBRE (%.0fg) -> evento\n", i + 1, g);
      }
    }
  }
}

static void procesarPendientes() {
  if (WiFi.status() != WL_CONNECTED) return;
  unsigned long ahora = millis();
  if (ahora - tReintento < (unsigned long)INTERVALO_REINTENTO_ENVIO) return;
  tReintento = ahora;
  for (int i = 0; i < TOTAL_SENSORES; i++) {
    if (eventoPendiente[i] && enviarEvento(i)) {
      eventoPendiente[i] = false;
    }
  }
}

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < TOTAL_SENSORES; i++) {
    pinMode(PINES_FSR[i], INPUT);
  }
  Serial.println("--- SmartLuben IoT v1.0 ---");
#if !TLS_VERIFICAR
  Serial.println("AVISO: TLS sin validación de cadena (solo dev/sim)");
#endif
  conectarWifiBloqueante();
  if (WiFi.status() == WL_CONNECTED) {
    diagnosticarRed();
    // Intento único rápido; si falla se reintenta en loop sin bloquear.
    sincronizado = sincronizarArranque();
  } else {
    Serial.println("Sin WiFi: se opera solo local hasta reconectar");
  }
  tMuestreo = millis();
}

void loop() {
  mantenerWifi();

  // Reintento de sync en segundo plano si el arranque falló
  if (!sincronizado && WiFi.status() == WL_CONNECTED) {
    unsigned long ahora = millis();
    if (ahora - tResync >= 30000UL) {
      tResync = ahora;
      sincronizado = sincronizarArranque();
    }
  }

  unsigned long ahora = millis();
  if (ahora - tMuestreo >= (unsigned long)INTERVALO_MUESTREO) {
    tMuestreo = ahora;
    muestrear();

    // Log compacto cada muestra (como antes)
    Serial.print("Valores -> ");
    for (int i = 0; i < TOTAL_SENSORES; i++) {
      Serial.printf("S%d: %dg%s", i + 1, (int)leerGramos(i), sensorOcupado[i] ? "[O]" : "[L]");
      if (i < TOTAL_SENSORES - 1) Serial.print(" | ");
    }
    Serial.println();
  }

  procesarPendientes();
}
