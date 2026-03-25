import fs from 'node:fs'
import path from 'node:path'

const rootDir = process.cwd()
const assetsDir = path.join(rootDir, 'dist', 'assets')
const budgetFile = path.join(rootDir, 'perf', 'bundle-budget.json')
const baselineFile = path.join(rootDir, 'perf', 'bundle-baseline.json')

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf-8'))
}

function formatBytes(value) {
  return `${value.toLocaleString()} B`
}

function formatMetric(metricName, value) {
  if (metricName.endsWith('_count')) {
    return String(value)
  }
  return formatBytes(value)
}

function loadFiles(dirPath) {
  return fs
    .readdirSync(dirPath)
    .filter((file) => !file.endsWith('.map'))
    .map((file) => {
      const absolute = path.join(dirPath, file)
      const stats = fs.statSync(absolute)
      return { file, size: stats.size }
    })
}

if (!fs.existsSync(assetsDir)) {
  console.error(`bundle budget check failed: missing build output at ${assetsDir}`)
  console.error('run `npm run build` before running the budget gate')
  process.exit(1)
}

const files = loadFiles(assetsDir)
const jsFiles = files.filter((item) => item.file.endsWith('.js'))
const cssFiles = files.filter((item) => item.file.endsWith('.css'))

const metrics = {
  total_js_bytes: jsFiles.reduce((sum, item) => sum + item.size, 0),
  total_css_bytes: cssFiles.reduce((sum, item) => sum + item.size, 0),
  largest_js_bytes: jsFiles.reduce((max, item) => Math.max(max, item.size), 0),
  largest_css_bytes: cssFiles.reduce((max, item) => Math.max(max, item.size), 0),
  js_file_count: jsFiles.length,
  css_file_count: cssFiles.length,
}

const budget = readJson(budgetFile)
const baseline = readJson(baselineFile)
const failures = []

for (const [metricName, limitValue] of Object.entries(budget.absolute_limits)) {
  const currentValue = metrics[metricName]
  if (currentValue > limitValue) {
    failures.push(
      `[absolute] ${metricName}: current=${formatMetric(metricName, currentValue)} exceeds limit=${formatMetric(metricName, limitValue)}`,
    )
  }
}

for (const [metricName, baselineValue] of Object.entries(baseline)) {
  const currentValue = metrics[metricName]
  const growthLimit = Math.floor(baselineValue * (1 + budget.max_growth_ratio))
  if (currentValue > growthLimit) {
    failures.push(
      `[growth] ${metricName}: current=${formatMetric(metricName, currentValue)} exceeds baseline_growth_limit=${formatMetric(metricName, growthLimit)} (baseline=${formatMetric(metricName, baselineValue)}, growth_ratio=${budget.max_growth_ratio})`,
    )
  }
}

if (process.env.BUNDLE_BUDGET_WRITE_SNAPSHOT === 'true') {
  const currentFile = path.join(rootDir, 'perf', 'bundle-current.json')
  fs.writeFileSync(currentFile, `${JSON.stringify(metrics, null, 2)}\n`, 'utf-8')
}

console.log('bundle budget metrics:')
for (const [metricName, value] of Object.entries(metrics)) {
  console.log(`- ${metricName}: ${formatMetric(metricName, value)}`)
}

if (failures.length > 0) {
  console.error('\nbundle budget gate failed:')
  for (const failure of failures) {
    console.error(`- ${failure}`)
  }
  process.exit(1)
}

console.log('\nbundle budget gate passed')
