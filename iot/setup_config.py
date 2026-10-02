#!/usr/bin/env python3
"""Genera src/config.h desde iot/.env (con override por variables de entorno).

Uso:
    cp .env.example .env   # solo primera vez
    python setup_config.py
    pio run -e esp32

Por defecto API_BASE_URL apunta a un blackhole: la simulación/CI verifica
detección sin escribir jamás en una API real.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")
OUT_FILE = os.path.join(BASE_DIR, "src", "config.h")


def cargar_env(path):
    valores = {}
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea or linea.startswith("#") or "=" not in linea:
                    continue
                k, v = linea.split("=", 1)
                valores[k.strip()] = v.strip().strip("'\"")
    return valores


PLANTILLA = """// Configuración GENERADA por setup_config.py - NO EDITAR A MANO.
// Edita iot/.env y re-ejecuta: python setup_config.py

#pragma once

// WiFi (en Wokwi usar "Wokwi-GUEST" sin contraseña)
#define WIFI_SSID "{wifi_ssid}"
#define WIFI_PASS "{wifi_pass}"

// Base de la API (SIN barra final).
#define API_BASE_URL "{api_base_url}"

// Mapeo sensor -> espacio de la API (S1=E01, S2=E02, S3=E03, S4=E04)
#define SENSOR_ESPACIO_IDS {{1, 2, 3, 4}}

// Histéresis del FSR (gramos estimados, escala 0-2000g del sketch)
#define UMBRAL_OCUPADO_G 150.0f
#define UMBRAL_LIBRE_G 50.0f

// Lecturas consecutivas para confirmar un cambio (anti-rebote)
#define DEBOUNCE_LECTURAS 5

// Tiempos (ms)
#define INTERVALO_MUESTREO 250
#define INTERVALO_REINTENTO_WIFI 10000
#define INTERVALO_REINTENTO_ENVIO 5000
#define TIMEOUT_HTTP_MS 8000
#define REINTENTOS_HTTP 3
"""


def escapar(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def main():
    conf = cargar_env(ENV_FILE)
    for clave in ("WIFI_SSID", "WIFI_PASS", "API_BASE_URL"):
        if clave in os.environ:
            conf[clave] = os.environ[clave]
    conf.setdefault("WIFI_SSID", "Wokwi-GUEST")
    conf.setdefault("WIFI_PASS", "")
    conf.setdefault("API_BASE_URL", "http://127.0.0.1:9/")

    contenido = PLANTILLA.format(
        wifi_ssid=escapar(conf["WIFI_SSID"]),
        wifi_pass=escapar(conf["WIFI_PASS"]),
        api_base_url=escapar(conf["API_BASE_URL"].rstrip("/")),
    )
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(contenido)
    print(f"config.h generado desde {ENV_FILE if os.path.isfile(ENV_FILE) else 'defaults'}")
    print(f"  WIFI_SSID={conf['WIFI_SSID']} API_BASE_URL={conf['API_BASE_URL']}")


if __name__ == "__main__":
    sys.exit(main())
