const os = require('node:os')
const fs = require('node:fs')
const path = require('node:path')

function resolveDevHost() {
  if (process.env.LHCI_PREVIEW_HOST) {
    return process.env.LHCI_PREVIEW_HOST
  }
  if (process.env.E2E_DEV_HOST) {
    return process.env.E2E_DEV_HOST
  }

  const candidates = Object.values(os.networkInterfaces())
    .flatMap((entries) => entries || [])
    .filter((entry) => entry.family === 'IPv4' && !entry.internal)
    .map((entry) => entry.address)

  return candidates[0] || '0.0.0.0'
}

function resolveHostingUrl() {
  if (process.env.FIREBASE_HOSTING_URL) {
    return process.env.FIREBASE_HOSTING_URL
  }

  try {
    const firebaseConfigPath = path.resolve(__dirname, '../../../firebase.json')
    const firebaseConfig = JSON.parse(fs.readFileSync(firebaseConfigPath, 'utf8'))
    const hostingSite = firebaseConfig?.hosting?.site
    if (typeof hostingSite === 'string' && hostingSite.trim().length > 0) {
      return `https://${hostingSite.trim()}.web.app`
    }
  } catch {
    return undefined
  }

  return undefined
}

const previewHost = resolveDevHost()
const previewPort = process.env.LHCI_PREVIEW_PORT || process.env.E2E_DEV_PORT || '4173'

const previewOrigin = `http://${previewHost}:${previewPort}`
const explicitCollectUrl =
  process.env.LHCI_COLLECT_URL || process.env.E2E_BASE_URL || resolveHostingUrl()
const collectUrl = explicitCollectUrl || previewOrigin
const managedPreview = !explicitCollectUrl

module.exports = {
  collectUrl,
  managedPreview,
}
