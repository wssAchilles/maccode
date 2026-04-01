const { collectUrl, managedPreview } = require('./scripts/lhci-runtime.cjs')

module.exports = {
  ci: {
    collect: {
      url: [collectUrl],
      numberOfRuns: 2,
      ...(managedPreview
        ? {
            startServerCommand: 'node scripts/preview-for-lighthouse.mjs',
            startServerReadyPattern: 'LHCI_PREVIEW_READY',
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
