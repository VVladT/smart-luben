#include "api_client.h"
#include "config.h"

#include <HTTPClient.h>
#include <WiFiClientSecure.h>

// ISRG Root X1 (Let's Encrypt) para validar el TLS de ngrok.
// Descargado de https://letsencrypt.org/certs/isrgrootx1.pem
static const char ISRG_ROOT_X1[] PROGMEM = R"PEM(
-----BEGIN CERTIFICATE-----
MIIFazCCA1OgAwIBAgIRAIIQz7DSQONZRGPgu2OCiwAwDQYJKoZIhvcNAQELBQAw
TzELMAkGA1UEBhMCVVMxKTAnBgNVBAoTIEludGVybmV0IFNlY3VyaXR5IFJlc2Vh
cmNoIEdyb3VwMRUwEwYDVQQDEwxJU1JHIFJvb3QgWDEwHhcNMTUwNjA0MTEwNDM4
WhcNMzUwNjA0MTEwNDM4WjBPMQswCQYDVQQGEwJVUzEpMCcGA1UEChMgSW50ZXJu
ZXQgU2VjdXJpdHkgUmVzZWFyY2ggR3JvdXAxFTATBgNVBAMTDElTUkcgUm9vdCBY
MTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAK3oJHP0FDfzm54rVygc
h77ct984kIxuPOZXoHj3dcKi/vVqbvYATyjb3miGbESTtrFj/RQSa78f0uoxmyF+
0TM8ukj13Xnfs7j/EvEhmkvBioZxaUpmZmyPfjxwv60pIgbz5MDmgK7iS4+3mX6U
A5/TR5d8mUgjU+g4rk8Kb4Mu0UlXjIB0ttov0DiNewNwIRt18jA8+o+u3dpjq+sW
T8KOEUt+zwvo/7V3LvSye0rgTBIlDHCNAymg4VMk7BPZ7hm/ELNKjD+Jo2FR3qyH
B5T0Y3HsLuJvW5iB4YlcNHlsdu87kGJ55tukmi8mxdAQ4Q7e2RCOFvu396j3x+UC
B5iPNgiV5+I3lg02dZ77DnKxHZu8A/lJBdiB3QW0KtZB6awBdpUKD9jf1b0SHzUv
KBds0pjBqAlkd25HN7rOrFleaJ1/ctaJxQZBKT5ZPt0m9STJEadao0xAH0ahmbWn
OlFuhjuefXKnEgV4We0+UXgVCwOPjdAvBbI+e0ocS3MFEvzG6uBQE3xDk3SzynTn
jh8BCNAw1FtxNrQHusEwMFxIt4I7mKZ9YIqioymCzLq9gwQbooMDQaHWBfEbwrbw
qHyGO0aoSCqI3Haadr8faqU9GY/rOPNk3sgrDQoo//fb4hVC1CLQJ13hef4Y53CI
rU7m2Ys6xt0nUW7/vGT1M0NPAgMBAAGjQjBAMA4GA1UdDwEB/wQEAwIBBjAPBgNV
HRMBAf8EBTADAQH/MB0GA1UdDgQWBBR5tFnme7bl5AFzgAiIyBpY9umbbjANBgkq
hkiG9w0BAQsFAAOCAgEAVR9YqbyyqFDQDLHYGmkgJykIrGF1XIpu+ILlaS/V9lZL
ubhzEFnTIZd+50xx+7LSYK05qAvqFyFWhfFQDlnrzuBZ6brJFe+GnY+EgPbk6ZGQ
3BebYhtF8GaV0nxvwuo77x/Py9auJ/GpsMiu/X1+mvoiBOv/2X/qkSsisRcOj/KK
NFtY2PwByVS5uCbMiogziUwthDyC3+6WVwW6LLv3xLfHTjuCvjHIInNzktHCgKQ5
ORAzI4JMPJ+GslWYHb4phowim57iaztXOoJwTdwJx4nLCgdNbOhdjsnvzqvHu7Ur
TkXWStAmzOVyyghqpZXjFaH3pO3JLF+l+/+sKAIuvtd7u+Nxe5AW0wdeRlN8NwdC
jNPElpzVmbUq4JUagEiuTDkHzsxHpFKVK7q4+63SM1N95R1NbdWhscdCb+ZAJzVc
oyi3B43njTOQ5yOf+1CceWxG1bQVs5ZufpsMljq4Ui0/1lvh+wjChP4kqKOJ2qxq
4RgqsahDYVvTH9w7jXbyLeiNdd8XM2w9U/t7y0Ff/9yi0GE44Za4rF2LN9d11TPA
mRGunUHBcnWEvgJBQl9nJEiU0Zsnvgc/ubhPgXRR4Xq37Z0j4r7g1SgEEzwxA57d
emyPxgcYxn/eR44/KJ4EBs+lVDR3veyJm+kXQ99b21/+jh5Xos1AnX5iItreGCc=
-----END CERTIFICATE-----
)PEM";

static String baseUrl() {
  String b = API_BASE_URL;
  while (b.endsWith("/")) b.remove(b.length() - 1);
  return b;
}

static bool esHttps() {
  return String(API_BASE_URL).startsWith("https");
}

// Clientes compartidos + keep-alive: un solo handshake TLS por ciclo
// en vez de uno por request (en simulación cada handshake tarda decenas
// de segundos). Para http:// se usa cliente plano (dev contra 10.0.2.2).
static WiFiClientSecure clienteSeguro;
static WiFiClient clientePlano;
static bool clientesInit = false;

static void initClientes() {
  if (clientesInit) return;
  clientesInit = true;
  if (esHttps()) {
#if TLS_VERIFICAR
    clienteSeguro.setCACert(ISRG_ROOT_X1);
#else
    // Flexible: cifrado sin validar cadena (SOLO dev/sim contra ngrok).
    // La cadena YE2/X2 de ngrok no la valida el bundle ISRG.
    clienteSeguro.setInsecure();
#endif
  }
}

static void preparar(HTTPClient &http, const String &url, bool esPost) {
  initClientes();
  http.setTimeout(TIMEOUT_HTTP_MS);
  http.setReuse(true);
  if (esHttps()) {
    http.begin(clienteSeguro, url);
  } else {
    http.begin(clientePlano, url);
  }
  if (esPost) {
    http.addHeader("Content-Type", "application/json");
  }
  http.addHeader("ngrok-skip-browser-warning", "true");
}

// Ejecuta POST con reintentos. 200->OK, 400->CONVERGIDO, resto->ERROR.
static ApiResultado postConReintentos(const String &url, const char *body) {
  for (int intento = 0; intento < REINTENTOS_HTTP; intento++) {
    HTTPClient http;
    preparar(http, url, true);
    int code = http.POST((uint8_t *)body, strlen(body));
    http.end();
    if (code == 200) return API_OK;
    if (code == 400) return API_CONVERGIDO;
    if (code == 404) {
      Serial.printf("  API 404 (espacio inexistente): %s\n", url.c_str());
      return API_ERROR;
    }
    Serial.printf("  API intento %d/%d codigo=%d\n", intento + 1, REINTENTOS_HTTP, code);
    delay(1000);
  }
  return API_ERROR;
}

ApiResultado apiReponer(int espacioId) {
  String url = baseUrl() + "/api/espacios/" + String(espacioId) + "/reponer";
  Serial.printf("  -> POST reponer espacio %d\n", espacioId);
  return postConReintentos(url, "{}");
}

ApiResultado apiLiberar(int espacioId) {
  String url = baseUrl() + "/api/espacios/" + String(espacioId) + "/liberar";
  Serial.printf("  -> POST liberar espacio %d\n", espacioId);
  return postConReintentos(url, "{}");
}

bool apiGetEstado(int espacioId, char *buf, size_t buflen) {
  String url = baseUrl() + "/api/espacios/" + String(espacioId);
  for (int intento = 0; intento < REINTENTOS_HTTP; intento++) {
    Serial.printf("  GET E%d intento %d/%d...\n", espacioId, intento + 1, REINTENTOS_HTTP);
    HTTPClient http;
    preparar(http, url, false);
    int code = http.GET();
    if (code < 0) {
      Serial.printf("  GET E%d intento %d/%d error red=%d\n", espacioId, intento + 1, REINTENTOS_HTTP, code);
    } else if (code != 200) {
      Serial.printf("  GET E%d intento %d/%d http=%d\n", espacioId, intento + 1, REINTENTOS_HTTP, code);
    }
    if (code == 200) {
      String payload = http.getString();
      http.end();
      // Extracción mínima de "estado":"..." sin JSON parser
      int idx = payload.indexOf("\"estado\"");
      if (idx >= 0) {
        int q1 = payload.indexOf('"', idx + 8);
        int q2 = payload.indexOf('"', q1 + 1);
        if (q1 > 0 && q2 > q1 && (size_t)(q2 - q1 - 1) < buflen) {
          payload.substring(q1 + 1, q2).toCharArray(buf, buflen);
          return true;
        }
      }
      return false;
    }
    http.end();
    delay(1000);
  }
  return false;
}

bool apiSincronizar() {  String url = baseUrl() + "/api/espacios";
  HTTPClient http;
  preparar(http, url, false);
  int code = http.GET();
  if (code == 200) {
    Serial.printf("  Sync OK (%d bytes)\n", http.getString().length());
    http.end();
    return true;
  }
  Serial.printf("  Sync fallo codigo=%d\n", code);
  http.end();
  return false;
}

// Extrae host de API_BASE_URL (sin esquema, puerto ni path)
static String extraerHost() {
  String h = String(API_BASE_URL);
  h.replace("https://", "");
  h.replace("http://", "");
  int barra = h.indexOf('/');
  if (barra >= 0) h = h.substring(0, barra);
  int dosp = h.indexOf(':');
  if (dosp >= 0) h = h.substring(0, dosp);
  return h;
}

void diagnosticarRed() {
  String host = extraerHost();
  bool esTls = esHttps();
  Serial.printf("[DIAG] host=%s tls=%d\n", host.c_str(), esTls ? 1 : 0);

  // 1. DNS
  IPAddress ip;
  unsigned long t0 = millis();
  bool dnsOk = WiFi.hostByName(host.c_str(), ip);
  Serial.printf("[DIAG] DNS: %s (%lums) %s\n",
                dnsOk ? "OK" : "FALLO", millis() - t0,
                dnsOk ? ip.toString().c_str() : "");

  // 2. TCP 443 (plano, sin TLS: aísla red vs cifrado)
  t0 = millis();
  WiFiClient tcp;
  tcp.setTimeout(8000);
  bool tcpOk = tcp.connect(host.c_str(), 443);
  Serial.printf("[DIAG] TCP:443: %s (%lums)\n", tcpOk ? "OK" : "FALLO", millis() - t0);
  tcp.stop();

  // 3. TLS handshake (sin validar cadena si TLS_VERIFICAR=0)
  t0 = millis();
  WiFiClientSecure tls;
#if TLS_VERIFICAR
  tls.setCACert(ISRG_ROOT_X1);
#else
  tls.setInsecure();
#endif
  tls.setTimeout(15000);
  bool tlsOk = tls.connect(host.c_str(), 443);
  char tlsErr[96] = {0};
  int tlsCode = 0;
  if (!tlsOk) {
    tlsCode = tls.lastError(tlsErr, sizeof(tlsErr));
  }
  Serial.printf("[DIAG] TLS: %s (%lums) mbedtls=%d %s\n",
                tlsOk ? "OK" : "FALLO", millis() - t0, tlsCode, tlsErr);
  tls.stop();

  // 4. HTTPS GET mínimo contra /api/espacios/1
  t0 = millis();
  HTTPClient http;
  preparar(http, baseUrl() + "/api/espacios/1", false);
  int code = http.GET();
  Serial.printf("[DIAG] HTTPS GET: codigo=%d (%lums)\n", code, millis() - t0);
  http.end();

  // 5. Control neutral: HTTPS contra host público estándar, con cliente
  // propio aislado (no reutiliza el compartido). Si esto OK y ngrok RST =>
  // el edge de ngrok rechaza este handshake. Si ambos RST => egress TLS
  // del sim roto en general.
  t0 = millis();
  {
    WiFiClientSecure ctlTls;
#if TLS_VERIFICAR
    ctlTls.setCACert(ISRG_ROOT_X1);
#else
    ctlTls.setInsecure();
#endif
    HTTPClient ctl;
    ctl.setTimeout(15000);
    ctl.begin(ctlTls, "https://www.google.com/generate_204");
    int codeCtl = ctl.GET();
    Serial.printf("[DIAG] CTL google: codigo=%d (%lums)\n", codeCtl, millis() - t0);
    ctl.end();
  }
}
