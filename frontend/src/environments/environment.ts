// Archivo base: lo usa el BUILD DE PRODUCCIÓN (angular.json no lo reemplaza).
// Debe ser relativo: en prod nginx proxea /api al backend (misma origen,
// sin CORS ni puertos). NO poner hosts absolutos aquí.
// Dev (ng serve) usa environment.dev.ts en su lugar.
export const environment = {
  production: true,
  apiUrl: '/api',
};
