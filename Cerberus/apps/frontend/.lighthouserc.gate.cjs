const collectUrl = process.env.LHCI_COLLECT_URL || process.env.E2E_BASE_URL || 'http://127.0.0.1:4173'

module.exports = {
  ci: {
    collect: {
      url: [collectUrl],
      numberOfRuns: 2,
      settings: {
        preset: 'desktop',
        throttlingMethod: 'provided',
      },
    },
    assert: {
      assertions: {
        'largest-contentful-paint': ['error', { maxNumericValue: 2000 }],
        'interaction-to-next-paint': ['error', { maxNumericValue: 150 }],
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
