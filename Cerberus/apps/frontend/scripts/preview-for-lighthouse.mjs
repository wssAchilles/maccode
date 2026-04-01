import { spawn } from 'node:child_process'
import process from 'node:process'

const previewHost = process.env.LHCI_PREVIEW_HOST || 'localhost'
const previewPort = process.env.LHCI_PREVIEW_PORT || '4173'
const previewUrl = `http://${previewHost}:${previewPort}/`
const npmCommand = process.platform === 'win32' ? 'npm.cmd' : 'npm'

let ready = false
let shuttingDown = false

const preview = spawn(
  npmCommand,
  ['run', 'preview', '--', '--host', previewHost, '--port', previewPort, '--strictPort'],
  {
    cwd: process.cwd(),
    env: process.env,
    stdio: ['inherit', 'pipe', 'pipe'],
  },
)

function cleanup(code = 0) {
  if (shuttingDown) {
    return
  }

  shuttingDown = true

  if (!preview.killed) {
    preview.kill('SIGTERM')
    setTimeout(() => {
      if (!preview.killed) {
        preview.kill('SIGKILL')
      }
    }, 2_000).unref()
  }

  process.exit(code)
}

async function waitForPreview(url, attempts = 60, delayMs = 500) {
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    if (preview.exitCode !== null) {
      throw new Error(`preview exited before ready with code ${preview.exitCode}`)
    }

    try {
      const response = await fetch(url, { redirect: 'manual' })
      if (response.ok) {
        return
      }
    } catch {
      // Keep polling until the preview server is actually serving the built app.
    }

    await new Promise((resolve) => setTimeout(resolve, delayMs))
  }

  throw new Error(`preview did not become ready at ${url} within ${attempts * delayMs}ms`)
}

preview.stdout.on('data', (chunk) => {
  process.stdout.write(chunk)
})

preview.stderr.on('data', (chunk) => {
  process.stderr.write(chunk)
})

preview.on('exit', (code) => {
  if (!ready && !shuttingDown) {
    process.exit(code ?? 1)
  }
})

process.on('SIGINT', () => cleanup(130))
process.on('SIGTERM', () => cleanup(143))

waitForPreview(previewUrl)
  .then(() => {
    ready = true
    console.log(`LHCI_PREVIEW_READY ${previewUrl}`)
  })
  .catch((error) => {
    console.error(error instanceof Error ? error.message : String(error))
    cleanup(1)
  })
