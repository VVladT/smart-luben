#include "wokwi-api.h"
#include <stdio.h>
#include <stdlib.h>

typedef struct {
  pin_t pin_p1;
  pin_t pin_p2;
  uint32_t force_attr;
  buffer_t fb;
  uint32_t width;
  uint32_t height;
} chip_state_t;

static uint32_t pixel_buffer[64 * 144];

void set_pixel(int x, int y, uint32_t color) {
  if (x >= 0 && x < 64 && y >= 0 && y < 144) {
    int x_rotado = 63 - x;
    int y_rotado = 143 - y;
    
    pixel_buffer[y_rotado * 64 + x_rotado] = color;
  }
}


// Renderizado gráfico del RP-C10 por software
void draw_rp_c10(uint32_t force) {
  uint32_t transparente = 0x00000000;
  uint32_t color_cuerpo = 0xff2c3e50;      // Resina gris/azul oscura del RP-C10
  uint32_t color_sensible = 0xff1a252f;    // Polímero negro semiconductor
  uint32_t color_pistas = 0xffbdc3c7;      // Pistas de circuito plateadas
  uint32_t color_pines = 0xffbdc3c7;       // Contactos físicos de la base
  
  // Iluminar el centro del sensor en rojo si recibe presión
  if (force > 0) {
    color_sensible = 0xffe74c3c;
  }

  // 1. Limpiar pantalla
  for (int i = 0; i < (64 * 144); i++) pixel_buffer[i] = transparente;

  // 2. Dibujar la cola del sensor flexible (Ancho de 16px, desde Y=35 hasta Y=130)
  for (int y = 35; y <= 130; y++) {
    for (int x = 24; x <= 40; x++) {
      set_pixel(x, y, color_cuerpo);
    }
  }

  // 3. Dibujar las dos pistas conductoras de plata bajando por la cola
  for (int y = 35; y <= 120; y++) {
    set_pixel(28, y, color_pistas);
    set_pixel(36, y, color_pistas);
  }

  // 4. Dibujar la cabeza redonda del RP-C10 (Centro X=32, Y=35, Radio Exterior=20, Interior=16)
  int xc = 32, yc = 35, r_cuerpo = 20, r_sensible = 16;
  for (int y = 15; y <= 55; y++) {
    for (int x = 12; x <= 52; x++) {
      int dist_sq = (x - xc) * (x - xc) + (y - yc) * (y - yc);
      if (dist_sq <= r_cuerpo * r_cuerpo) {
        set_pixel(x, y, color_cuerpo);
      }
      if (dist_sq <= r_sensible * r_sensible) {
        set_pixel(x, y, color_sensible);
      }
    }
  }

  // 5. Dibujar las dos terminales metálicas expuestas donde se conectan los cables (Y=130 a 142)
  for (int y = 130; y <= 142; y++) {
    for (int x = 26; x <= 29; x++) set_pixel(x, y, color_pines); // Pin 1
    for (int x = 35; x <= 38; x++) set_pixel(x, y, color_pines); // Pin 2
  }
}

static void chip_timer_callback(void *user_data) {
  chip_state_t *chip = (chip_state_t *)user_data;
  
  // Lógica de Voltaje
  uint32_t force = attr_read(chip->force_attr);
  float voltage = (force * 3.3f) / 100.0f;
  pin_dac_write(chip->pin_p2, voltage);

  // Lógica Gráfica
  draw_rp_c10(force);

  // Volcar el búfer renderizado al simulador de VSCode
  buffer_write(chip->fb, 0, pixel_buffer, sizeof(pixel_buffer));
}

void chip_init() {
  chip_state_t *chip = malloc(sizeof(chip_state_t));

  chip->pin_p1 = pin_init("P1", INPUT);
  chip->pin_p2 = pin_init("P2", ANALOG);
  chip->force_attr = attr_init("force", 0);

  // Inicializar Framebuffer oficial compatible con VSCode
  chip->fb = framebuffer_init(&chip->width, &chip->height);

  const timer_config_t config = {
    .callback = chip_timer_callback,
    .user_data = chip,
  };
  timer_t timer = timer_init(&config);
  timer_start(timer, 40000, true); // 25 FPS
}
