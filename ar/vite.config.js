import { defineConfig } from 'vite'
import { PRODUCTOS, getEspacios, pollForChanges } from './api/mockData.js'

// Mock API plugin - serves /api/* from mockData.js (prototype only).
// NOTE: when mounted via server.middlewares.use('/api', handler),
// connect strips the mount prefix, so inside the handler req.url is
// '/productos' (not '/api/productos'). That was the previous 404 bug.
function mockApiPlugin() {
  return {
    name: 'mock-api',
    configureServer(server) {
      server.middlewares.use('/api', async (req, res, next) => {
        res.setHeader('Access-Control-Allow-Origin', '*')
        res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization')

        if (req.method === 'OPTIONS') {
          res.statusCode = 204
          res.end()
          return
        }

        // req.url here is already stripped of the '/api' prefix
        const path = req.url.split('?')[0]

        try {
          if (req.method === 'GET' && path === '/productos') {
            res.setHeader('Content-Type', 'application/json')
            res.end(JSON.stringify(PRODUCTOS))
            return
          }

          if (req.method === 'GET' && path === '/espacios') {
            res.setHeader('Content-Type', 'application/json')
            res.end(JSON.stringify(getEspacios()))
            return
          }

          if (req.method === 'POST' && path === '/sync/changes') {
            let body = ''
            req.on('data', (chunk) => { body += chunk })
            req.on('end', () => {
              try {
                JSON.parse(body || '{}') // validate, versions unused in mock
                res.setHeader('Content-Type', 'application/json')
                res.end(JSON.stringify(pollForChanges()))
              } catch (err) {
                res.statusCode = 400
                res.end(JSON.stringify({ error: 'Invalid JSON' }))
              }
            })
            return
          }

          // Unknown /api/* route: fall through to Vite (will 404)
          next()
        } catch (err) {
          console.error('[Mock API] Error:', err)
          res.statusCode = 500
          res.end(JSON.stringify({ error: 'Internal server error' }))
        }
      })
    },
  }
}

export default defineConfig({
  root: '.',
  base: '/ar/',
  publicDir: 'assets',
  server: {
    host: true,
    port: 4202,
    https: {
      key: './key.pem',
      cert: './cert.pem',
    },
    headers: {
      'X-Frame-Options': 'ALLOWALL',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  },
  plugins: [mockApiPlugin()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: 'index.html',
    },
  },
})
