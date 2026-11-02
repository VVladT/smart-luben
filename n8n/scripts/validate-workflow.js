const { readFileSync } = require('node:fs')

const path = 'n8n/workflows/automatic-plan.json'
const workflow = JSON.parse(readFileSync(path, 'utf8'))
const expectedId = '25pZ9DqIHtB4KqOY'
if (workflow.id !== expectedId) throw new Error(`El ID debe permanecer fijo: ${expectedId}`)

const nodes = new Map(workflow.nodes.map(node => [node.name, node]))
const schedule = [...nodes.values()].find(node => node.type === 'n8n-nodes-base.scheduleTrigger')
const webhook = [...nodes.values()].find(node => node.type === 'n8n-nodes-base.webhook')
if (!schedule || !webhook || webhook.parameters.httpMethod !== 'POST' ||
    webhook.parameters.path !== 'smart-luben-espacio-liberado') {
  throw new Error('Faltan el horario o el webhook POST de liberación')
}

const outgoing = name => workflow.connections[name]?.main?.[0]?.map(edge => edge.node) || []
if (!outgoing(schedule.name).includes('Planificar espacios libres') ||
    !outgoing(webhook.name).includes('Validar horario de operación') ||
    !outgoing('Validar horario de operación').includes('Consultar mostrador') ||
    !outgoing('Consultar mostrador').includes('Confirmar mostrador vacío') ||
    !outgoing('Confirmar mostrador vacío').includes('Planificar espacios libres')) {
  throw new Error('Las rutas del horario y del vaciado no coinciden con el contrato')
}

const plan = nodes.get('Planificar espacios libres')
if (plan?.parameters?.method !== 'POST' ||
    plan.parameters.url !== 'http://backend:8000/api/ml/plan-now') {
  throw new Error('La planificación debe llamar a la API interna del backend')
}
console.log(`Workflow válido: ${workflow.name} (${workflow.id})`)
