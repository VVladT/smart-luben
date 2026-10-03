# SmartLuben IoT — Nodo ESP32 + 4 sensores FSR

Un ESP32 lee 4 sensores de fuerza (RP-C10, pines 32–35) — uno por
espacio del mostrador (S1→E01 … S4→E04) — y reporta ocupación /
liberación a la API por HTTPS (túnel zrok reservado).

## Cableado (ver `diagram.json` en Wokwi)

FSR en divisor de voltaje con resistencia 1k a GND, señal al pin
analógico. 3V3 compartido.

## Configuración (generada, no a mano)

```bash
cp .env.example .env   # solo primera vez; completar WIFI_* y API_BASE_URL
python setup_config.py # genera src/config.h
pio run -e esp32       # compilar
```

- `src/config.h` e `iot/.env` están ignorados en git (secretos).
- Por defecto `API_BASE_URL` apunta a un blackhole: simulación y CI
  verifican **detección sin escribir jamás** en una API real.
- Solo para E2E manual, apuntar al backend real en `.env`:
  Wokwi `http://host.wokwi.internal:8000`, prod zrok reservado
  `https://smartluben.shares.zrok.io` (estable; ngrok free es incompatible
  con este handshake: su edge lo resetea).

## Lógica de detección

- Histéresis: ocupa sobre `UMBRAL_OCUPADO_G`, libera bajo
  `UMBRAL_LIBRE_G` (ajustar con el peso real de los productos).
- Anti-rebote: `DEBOUNCE_LECTURAS` lecturas consecutivas antes de
  confirmar un cambio. Sin esto, cada ruido genera movimientos
  huérfanos en el historial.
- Al arrancar sincroniza la creencia local con `GET /api/espacios`
  (no genera eventos espurios tras reinicios).

## Contrato con la API (MVP, sin auth)

| Evento físico | Llamada | Efecto |
|---|---|---|
| Peso detectado | `POST /api/espacios/{id}/reponer {}` | Ocupa con el planificado, o `desconocido` si no hay plan |
| Peso retirado | `POST /api/espacios/{id}/liberar` | Libera y elimina el producto |
| `400` "ya está ..." | — | Convergido: tratar como éxito y re-sincronizar |

Headers: `Content-Type: application/json`,
`ngrok-skip-browser-warning: true` (requerido tras ngrok; inofensivo en zrok).
TLS validado con ISRG Root X1 (embebido en `src/api_client.cpp`).

## Simulación / build

```bash
pio run -e esp32            # compilar
pio device monitor           # ver Serial (115200)
```

### TLS flexible vs estricto

`TLS_VERIFICAR` (en `.env`, default 0):
- **0 flexible**: cifrado sin validar la cadena. Necesario tras túneles
  con cadenas modernas (ngrok YE2/X2) y suficiente para sim/dev.
  El arranque lo avisa por Serial.
- **1 estricto**: valida contra ISRG Root X1 embebido. Solo sirve con
  cadena anclada en X1 (dominio propio con `--preferred-chain`).
- Los timeouts están holgados (20s) porque el handshake simulado es lento.

### Tests automatizados con wokwi-cli

```bash
wokwi-cli . --scenario tests/sensor-fsr.yaml --timeout 180000
```

El escenario mueve los sliders FSR (vía `set-control force`) y espera
los logs de detección (`S1 OCUPADO`...). Requiere `WOKWI_CLI_TOKEN`
(en CI va como secret; el firmware de CI corre en CI con API blackhole).
El `wokwi.toml` no lleva `[net]`: no hace falta gateway (ver `config.h`
generado y `.env` para E2E manual).

## Pendiente post-MVP

- Auth (API key) en escritura.
- Túnel estable documentado (zrok reservado `smartluben.shares.zrok.io`).
- Calibrar umbrales con productos reales.
