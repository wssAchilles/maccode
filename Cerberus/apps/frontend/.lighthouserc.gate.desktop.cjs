const collectUrl = process.env.LHCI_COLLECT_URL || process.env.E2E_BASE_URL || 'http://localhost:4173'
const localCollect =
  collectUrl.startsWith('http://localhost:4173') || collectUrl.startsWith('http://127.0.0.1:4173')

module.exports = {
  ci: {
    collect: {
      url: [collectUrl],
      numberOfRuns: 2,
      ...(localCollect
        ? {
            startServerCommand: 'node scripts/preview-for-lighthouse.mjs',
            startServerReadyPattern: 'LHCI_PREVIEW_READY',
          }
        : {}),
      settings: {
        preset: 'desktop',
        throttlingMethod: 'provided',
      },
    },
    assert: {
      assertions: {
        'largest-contentful-paint': ['error', { maxNumericValue: 2000 }],
        'interaction-to-next-paint': ['warn', { maxNumericValue: 150 }],
        'total-blocking-time': ['error', { maxNumericValue: 200 }],
        'cumulative-layout-shift': ['error', { maxNumericValue: 0.1 }],
        'categories:accessibility': ['error', { minScore: 0.9 }],
        'categories:best-practices': ['error', { minScore: 0.9 }],
      },
    },
    upload: {
      target: 'temporary-public-storage',
    },
  },
}
