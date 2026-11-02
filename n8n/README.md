# n8n para SmartLuben

## Acceso

- Desarrollo: `http://localhost/n8n/` mediante el servicio `gateway` de
  `docker-compose.dev.yml`.
- Producción: `https://TU_DOMINIO/n8n/` mediante nginx del servicio `frontend`.
  El puerto 5678 no se publica en el host; n8n se comunica por la red de Compose.
- La configuración de nginx **no habilita TLS por sí sola**: el dominio debe
  tener HTTPS en el proxy/túnel público existente antes de dar acceso al docente.
  El acceso y la autenticación al editor se administran en n8n. No compartas
  la cuenta propietaria; crea una cuenta para el docente si tu edición lo permite,
  o presenta la pantalla en la demostración.

## Configuración inicial

1. Copia `.env.example` a `.env` si aún no tienes un `.env`. Genera una clave
   con `openssl rand -hex 32` y configura `N8N_ENCRYPTION_KEY` con ese valor.
   **No cambies la clave** después de crear credenciales: perderías acceso a ellas.
2. En producción establece `N8N_PUBLIC_URL=https://TU_DOMINIO/n8n/` en el
   `.env` del servidor (barra final obligatoria). Si hay un proxy de TLS delante
   del nginx de Compose, configura `N8N_PROXY_HOPS=2`; sin él, deja `1`.
   En desarrollo usa
   `N8N_PUBLIC_URL=http://localhost/n8n/`. No subas `.env` a Git.
3. Inicia producción con `docker compose up -d n8n frontend`; para desarrollo,
   `docker compose -f docker-compose.dev.yml up -d n8n gateway`. El primer inicio
   muestra el registro del usuario propietario: **complétalo antes de compartir
   públicamente la URL**. Consulta `docker compose logs -f n8n` ante errores.
4. Importa `workflows/automatic-plan.json` en el editor de n8n. El
   Schedule Trigger trae **horarios de ejemplo** 08:00, 12:00 y 16:00 todos
   los días en `America/Lima`: edítalos según los horarios reales. La ruta
   programada llama directamente a `POST http://backend:8000/api/ml/plan-now`
   incluso cuando todavía hay espacios ocupados (el backend no toca los
   ocupados ni los planes existentes).
   Si ya importaste la versión anterior (solo horario), despublícala o
   reemplázala: no dejes ambos workflows activos con los mismos horarios.
5. La ruta del Webhook `POST smart-luben-espacio-liberado` solo continúa si el
   evento es `space_released` y la hora actual en `America/Lima` está dentro
   de la **franja de ejemplo 08:00–20:00** (inicio inclusivo, fin exclusivo).
   Cambia `inicio` y `fin` en el nodo **Validar horario de operación** para
   reflejar el horario real; si varía por día, adapta esa lógica antes de publicar.
   Luego consulta todos los espacios y llama a `plan-now` solo cuando todos
   tienen `estado == "libre"` (un plan `pendiente` sigue físicamente libre).
6. Prueba cada ruta manualmente: confirma que la respuesta contiene `planned`
   y `skipped`, los espacios planificados quedan `pendiente` y no se registran
   reposiciones físicas. **Publica** el workflow antes de activar el webhook
   de producción. Una segunda ejecución no sustituye planes existentes.
   Los fallos quedan en el historial de n8n; añade una notificación si la necesitas.

El workflow exportado no debe contener secretos. El volumen Docker `n8n_data`
contiene su SQLite, usuarios, credenciales y ejecuciones: haz copias de ese volumen
y conserva también `N8N_ENCRYPTION_KEY`. n8n no usa la base de datos del backend.

## Evento de liberación desde la API

El backend puede notificar **cualquier liberación exitosa**, ya sea manual o IoT.
Una liberación fallida no envía eventos. Configura en el `.env` de Compose
`N8N_EMPTY_COUNTER_WEBHOOK_URL=http://n8n:5678/webhook/smart-luben-espacio-liberado`
**solo después de importar y publicar** el workflow incluido en esta carpeta;
reinicia el servicio backend para aplicar la variable. En
desarrollo, la URL de prueba `/webhook-test/...` funciona solo mientras el
editor está escuchando; usa la URL de producción `/webhook/...` al publicar.
La URL interna **no** incluye `/n8n/`: ese prefijo solo existe en el proxy web.

El cuerpo del evento contiene `event: "space_released"`, `movement_id`,
`space_id`, `space_code` y `occurred_at` (ISO 8601). El backend no comprueba si
todo el mostrador está vacío: el workflow debe consultar `GET
http://backend:8000/api/espacios` y continuar **solo si todos** los espacios
tienen `estado == "libre"` y la hora actual está dentro del horario de operación
(`America/Lima`). Entonces llama a `POST /api/ml/plan-now`. Los horarios
programados llaman a `plan-now` directamente, sin estas comprobaciones.
Si n8n está caído o el webhook falla, la liberación física sigue registrada;
revisa los logs del backend para detectar avisos no entregados.

## Despliegue automático con GitHub Actions

El workflow `.github/workflows/n8n.yml` valida el JSON en PR y, tras un push
a `main` que cambie `n8n/**` (o desde `workflow_dispatch`), lo despliega con
el runner `self-hosted`. Usa el mismo bloqueo `prod-deploy` que el resto de
servicios. No necesita API key de n8n.

**Preparación única en producción:** configura `.env` (y deja `../.env` y
`../garage.toml` junto al checkout, como en los demás deploys). El **primer
push levanta n8n automáticamente**. Si aún no tiene propietario, el pipeline
termina sin importar el JSON: crea la cuenta en la URL pública y vuelve a
ejecutar `n8n Workflow CI/CD` desde **Actions → Run workflow**. Los siguientes
pushes importan y publican el workflow automáticamente. El archivo
`automatic-plan.json` debe conservar su ID `25pZ9DqIHtB4KqOY`, que es el
usado para importarlo y publicar las revisiones siguientes. Si en producción
ya hay un workflow con ese mismo ID, revisa si corresponde a este flujo:
la importación lo sobrescribirá. No mantengas otro workflow antiguo publicado
con los mismos horarios o webhook.

El pipeline detiene n8n, copia su directorio persistente a
`../n8n-backups/<run-id>-<intento>/.n8n` (incluye credenciales cifradas y datos
sensibles: restringe acceso y realiza retención controlada), importa el JSON,
publica ese ID y arranca n8n de nuevo incluso si la importación falla. Si el
deploy falla tras importar, **no restaura automáticamente** el respaldo: revisa
los logs y restáuralo manualmente si es necesario. Por eso se debe validar
el flujo en desarrollo antes de subirlo a Git.

Tras el primer deploy exitoso, configura
`N8N_EMPTY_COUNTER_WEBHOOK_URL=http://n8n:5678/webhook/smart-luben-espacio-liberado`
en el `.env` del VPS y recrea el backend para que empiece a notificar. Los
futuros cambios del workflow se realizan en desarrollo, se exportan a ese
JSON con el mismo ID y se despliegan al hacer push; cambios solo en la UI de
producción se sobrescribirán en el siguiente despliegue.

> La documentación de n8n advierte que alojar el editor en una subruta con
> reverse proxy puede ocasionar problemas de navegación. Antes de la demo,
> verifica desde la URL pública el inicio de sesión, la navegación, las
> ejecuciones y, si se usan, los webhooks. La autenticación de escrituras en la
> API SmartLuben sigue siendo deuda técnica del MVP.
