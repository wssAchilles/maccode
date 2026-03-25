const collectUrl = process.env.LHCI_COLLECT_URL || process.env.E2E_BASE_URL || 'http://127.0.0.1:4173'
const localCollect = collectUrl.startsWith('http://127.0.0.1:4173')

module.exports = {
  ci: {
    collect: {
      url: [collectUrl],
      numberOfRuns: 2,
      ...(localCollect
        ? {
            startServerCommand: 'npm run preview -- --host 127.0.0.1 --port 4173',
            startServerReadyPattern: 'Local',
          }
        : {}),
      settings: {
        throttlingMethod: 'provided',
        formFactor: 'mobile',
        screenEmulation: {
          mobile: true,
          width: 390,
          height: 844,
          deviceScaleFactor: 2,
          disabled: false,
        },
      },
    },
    assert: {
      assertions: {
        'largest-contentful-paint': ['error', { maxNumericValue: 2600 }],
        'interaction-to-next-paint': ['warn', { maxNumericValue: 180 }],
        'total-blocking-time': ['error', { maxNumericValue: 300 }],
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
