// 一键启动：后端(8000) + 前端Vite(可接收 --port/--host 参数)
import { spawn } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.dirname(fileURLToPath(import.meta.url))
const extraArgs = process.argv.slice(2)

const backend = spawn('python', ['-m', 'uvicorn', 'main:app', '--host', '0.0.0.0', '--port', '8000'], {
  cwd: path.join(root, 'backend'), stdio: 'inherit', shell: true,
})
const frontend = spawn('npx', ['vite', ...extraArgs], {
  cwd: path.join(root, 'clue-pool-frontend'), stdio: 'inherit', shell: true,
})

function shutdown() { backend.kill(); frontend.kill(); process.exit(0) }
process.on('SIGINT', shutdown)
process.on('SIGTERM', shutdown)
