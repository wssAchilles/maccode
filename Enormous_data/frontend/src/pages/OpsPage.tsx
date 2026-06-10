import { Activity, BarChart3, CheckCircle2, Database, FileJson, GitBranch, HardDrive, Play, ShieldCheck, XCircle } from 'lucide-react';
import { useJob, useJobLineage, useJobQuality, useJobs, useOpsEvidence, useRefreshJob } from '../api/hooks';
import { compactDate } from '../lib/format';
import type { BenchmarkRun, EvidencePath, JobStatus, ModuleBenchmarkRun, QualityCheck } from '../types/api';

const activeStatuses = new Set(['queued', 'running']);

function statusLabel(status?: string) {
  if (!status) return 'unknown';
  if (status === 'succeeded') return 'succeeded';
  if (status === 'success') return 'succeeded';
  return status;
}

function shortHash(hash?: string | null) {
  return hash ? hash.slice(0, 12) : 'pending';
}

function qualityTone(status?: string | null) {
  if (status === 'passed') return 'success';
  if (status === 'failed') return 'danger';
  return 'warning';
}

function safeNumber(value?: number) {
  return typeof value === 'number' ? value.toLocaleString() : 'pending';
}

function seconds(value?: number | null) {
  return typeof value === 'number' ? `${value.toFixed(1)}s` : 'pending';
}

function bytes(value?: number | null) {
  if (typeof value !== 'number') return 'pending';
  if (value >= 1024 ** 3) return `${(value / 1024 ** 3).toFixed(1)} GB`;
  if (value >= 1024 ** 2) return `${(value / 1024 ** 2).toFixed(1)} MB`;
  if (value >= 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${value} B`;
}

function metricNumber(value: unknown): number | undefined {
  return typeof value === 'number' ? value : undefined;
}

function jobMessage(job?: JobStatus) {
  if (!job?.message) return '等待首次运行';
  const lines = job.message.split('\n').filter(Boolean);
  return lines.at(-1) ?? job.message;
}

function variantLabel(variant: string) {
  const labels: Record<string, string> = {
    baseline_local_csv: 'Local CSV baseline',
    yarn_only_csv: 'YARN-only CSV',
    yarn_aqe_csv: 'YARN + AQE',
    yarn_algorithm_csv: 'YARN + algorithm',
    yarn_parquet: 'YARN + Parquet',
  };
  return labels[variant] ?? variant;
}

export function OpsPage() {
  const job = useJob();
  const jobs = useJobs(8);
  const currentJobId = job.data?.job_id ?? jobs.data?.rows[0]?.job_id;
  const lineage = useJobLineage(currentJobId);
  const quality = useJobQuality(currentJobId);
  const evidence = useOpsEvidence();
  const refresh = useRefreshJob();
  const latest = job.data;
  const inputSnapshot = lineage.data?.input_snapshot ?? latest?.input_snapshot;
  const outputArtifacts = lineage.data?.output_artifacts ?? latest?.output_artifacts;
  const qualityReport = quality.data?.quality_report ?? latest?.quality_report;
  const sparkStatus = quality.data?.spark_application_status ?? lineage.data?.spark_application_status ?? latest?.spark_application_status;
  const sparkAppId = quality.data?.spark_application_id ?? lineage.data?.spark_application_id ?? latest?.spark_application_id;
  const sparkHistory = quality.data?.spark_history_metrics ?? lineage.data?.spark_history_metrics ?? latest?.spark_history_metrics;
  const sparkHistoryStatus =
    quality.data?.spark_history_metrics_status ?? lineage.data?.spark_history_metrics_status ?? latest?.spark_history_metrics_status ?? 'not_configured';
  const checks = qualityReport?.gate?.checks ?? [];
  const checksPassed = checks.filter((check) => check.passed).length;
  const failureStage = quality.data?.failure_stage ?? latest?.failure_stage ?? 'none';
  const isActive = activeStatuses.has(latest?.status ?? '');
  const benchmarkRows = evidence.data?.benchmark_runs ?? [];
  const hdfsEvidence = evidence.data?.hdfs_inputs ?? [];
  const localSamples = evidence.data?.local_samples ?? [];
  const benchmarkSummary = evidence.data?.benchmark_summary;
  const historySummary = evidence.data?.history_summary;
  const moduleRows = evidence.data?.module_benchmark_runs ?? [];

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">Pipeline operations</span>
        <h1>作业治理与运行血缘</h1>
        <p>围绕真实 Kaggle 行为数据集跟踪 Spark 运行、HDFS 输入、质量门禁和缓存产物。</p>
      </section>

      <section className="ops-command-band">
        <div>
          <span className={`status-pill tone-${statusLabel(latest?.status)}`}>{statusLabel(latest?.status)}</span>
          <h2>{latest?.run_id ?? latest?.job_id ?? '尚未生成运行记录'}</h2>
          <p>{jobMessage(latest)}</p>
        </div>
        <button className="primary-action compact" disabled={refresh.isPending || isActive} onClick={() => refresh.mutate()} type="button">
          <Play size={16} />
          {refresh.isPending || isActive ? '运行中' : '启动 Spark'}
        </button>
      </section>

      <section className="ops-triage-grid" aria-label="作业首屏判断">
        <article className={`triage-card tone-${statusLabel(latest?.status) === 'succeeded' ? 'success' : activeStatuses.has(latest?.status ?? '') ? 'running' : 'warning'}`}>
          <span>最新运行</span>
          <strong>{statusLabel(latest?.status)}</strong>
          <small>{latest?.elapsed_seconds ? `${latest.elapsed_seconds}s` : '等待耗时'}</small>
          <p>{sparkAppId ?? 'waiting for application id'}</p>
        </article>
        <article className={`triage-card tone-${failureStage === 'none' ? 'success' : 'danger'}`}>
          <span>失败阶段</span>
          <strong>{failureStage}</strong>
          <small>{sparkHistoryStatus}</small>
          <p>{latest?.error ?? '当前没有失败阶段。'}</p>
        </article>
        <article className={`triage-card tone-${qualityTone(quality.data?.quality_status ?? latest?.quality_status)}`}>
          <span>质量门禁</span>
          <strong>{quality.data?.quality_status ?? latest?.quality_status ?? 'pending'}</strong>
          <small>{checks.length ? `${checksPassed}/${checks.length} checks passed` : '等待 Spark manifest'}</small>
          <p>{qualityReport?.gate?.status ?? 'not evaluated'}</p>
        </article>
        <article className="triage-card tone-success">
          <span>运行证据</span>
          <strong>{safeNumber((benchmarkSummary?.one_pct_run_count ?? 0) + (benchmarkSummary?.five_pct_run_count ?? 0))}</strong>
          <small>benchmark groups</small>
          <p>{benchmarkSummary?.interpretation ?? '等待 benchmark 汇总数据'}</p>
        </article>
      </section>

      <details className="ops-detail-disclosure">
        <summary>查看完整运行指标</summary>
        <section className="ops-kpi-grid">
          <article className="metric-card">
            <span>输入文件</span>
            <strong>{safeNumber(inputSnapshot?.file_count)}</strong>
            <small>{inputSnapshot?.storage_mode ?? latest?.storage_mode ?? 'unknown storage'}</small>
          </article>
          <article className="metric-card">
            <span>清洗行数</span>
            <strong>{safeNumber(qualityReport?.metrics?.cleaned_rows)}</strong>
            <small>removed ratio {qualityReport?.metrics?.removed_ratio ?? 'pending'}</small>
          </article>
          <article className="metric-card">
            <span>配置指纹</span>
            <strong>{shortHash(lineage.data?.config_hash ?? latest?.config_hash)}</strong>
            <small>{lineage.data?.contract_version ?? latest?.contract_version ?? 'contract pending'}</small>
          </article>
          <article className="metric-card">
            <span>Spark 状态</span>
            <strong>{sparkStatus ?? 'pending'}</strong>
            <small>{sparkAppId ?? 'waiting for application id'}</small>
          </article>
          <article className="metric-card">
            <span>History 指标</span>
            <strong>{sparkHistoryStatus}</strong>
            <small>spill {safeNumber(metricNumber(sparkHistory?.memory_spill_bytes))}, failed {safeNumber(metricNumber(sparkHistory?.failed_task_count))}</small>
          </article>
          <article className="metric-card tone-success">
            <span>AQE/算法加速</span>
            <strong>{benchmarkSummary?.yarn_only_to_algorithm_speedup ? `${benchmarkSummary.yarn_only_to_algorithm_speedup}x` : 'pending'}</strong>
            <small>相对 YARN-only CSV</small>
          </article>
          <article className="metric-card tone-success">
            <span>History 采集</span>
            <strong>{safeNumber(historySummary?.collected_run_count)}</strong>
            <small>failed {safeNumber(historySummary?.failed_task_count)}, retried {safeNumber(historySummary?.retried_task_count)}</small>
          </article>
          <article className="metric-card">
            <span>模块基准</span>
            <strong>{safeNumber(moduleRows.length)}</strong>
            <small>典型 20 万行样本</small>
          </article>
        </section>
      </details>

      <section className="ops-grid">
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>当前运行</h2>
              <p>后台 Spark 作业状态和运行耗时。</p>
            </div>
            <Activity size={20} />
          </div>
          <dl>
            <dt>Job ID</dt>
            <dd>{latest?.job_id ?? 'pending'}</dd>
            <dt>Run ID</dt>
            <dd>{latest?.run_id ?? 'pending'}</dd>
            <dt>开始时间</dt>
            <dd>{compactDate(latest?.started_at)}</dd>
            <dt>完成时间</dt>
            <dd>{compactDate(latest?.finished_at)}</dd>
            <dt>耗时</dt>
            <dd>{latest?.elapsed_seconds ? `${latest.elapsed_seconds}s` : 'pending'}</dd>
            <dt>失败阶段</dt>
            <dd>{quality.data?.failure_stage ?? latest?.failure_stage ?? 'none'}</dd>
          </dl>
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>输入血缘</h2>
              <p>HDFS 源文件和输出 manifest。</p>
            </div>
            <GitBranch size={20} />
          </div>
          <dl>
            <dt>实际输入</dt>
            <dd>{inputSnapshot?.actual_input_path ?? latest?.input_path ?? 'pending'}</dd>
            <dt>配置输入</dt>
            <dd>{inputSnapshot?.configured_input_path ?? 'pending'}</dd>
            <dt>Manifest</dt>
            <dd>{outputArtifacts?.run_manifest_path ?? outputArtifacts?.manifest_path ?? 'pending'}</dd>
            <dt>指标目录</dt>
            <dd>{outputArtifacts?.metrics_dir ?? 'pending'}</dd>
          </dl>
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>质量检查</h2>
              <p>阈值门禁用于阻止异常缓存发布。</p>
            </div>
            <ShieldCheck size={20} />
          </div>
          <div className="quality-checks">
            {checks.length ? checks.map((check) => <QualityCheckRow check={check} key={check.name} />) : <span className="empty-copy">等待质量报告</span>}
          </div>
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>输入文件快照</h2>
              <p>从 Spark DataFrame inputFiles 采集。</p>
            </div>
            <Database size={20} />
          </div>
          <div className="file-list">
            {(inputSnapshot?.files ?? []).slice(0, 5).map((file) => (
              <span key={file}>
                <FileJson size={14} />
                {file}
              </span>
            ))}
            {inputSnapshot?.files?.length ? null : <span className="empty-copy">等待 HDFS 文件快照</span>}
          </div>
        </article>
      </section>

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>Benchmark 证据</h2>
            <p>{benchmarkSummary?.interpretation ?? '等待 benchmark 汇总数据'}</p>
          </div>
          <BarChart3 size={20} />
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>样本</th>
                <th>对照组</th>
                <th>耗时</th>
                <th>吞吐</th>
                <th>YARN App</th>
                <th>任务</th>
                <th>Memory spill</th>
                <th>质量</th>
              </tr>
            </thead>
            <tbody>
              {benchmarkRows.map((row) => <BenchmarkRow row={row} key={`${row.sample}-${row.variant}`} />)}
              {benchmarkRows.length === 0 ? (
                <tr>
                  <td colSpan={8}>暂无 benchmark 证据</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>典型模块 Benchmark</h2>
            <p>使用 1% 样本中的 20 万行代表性数据，覆盖关联、推荐、异常和实验模块。</p>
          </div>
          <BarChart3 size={20} />
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>模块</th>
                <th>任务</th>
                <th>输入行</th>
                <th>输出行</th>
                <th>耗时</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              {moduleRows.map((row) => <ModuleBenchmarkRow row={row} key={`${row.profile}-${row.task_name}`} />)}
              {moduleRows.length === 0 ? (
                <tr>
                  <td colSpan={6}>暂无模块 benchmark 证据</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="ops-grid">
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>实验 HDFS 输入</h2>
              <p>正式 benchmark 使用的 CSV 与 Parquet 输入。</p>
            </div>
            <Database size={20} />
          </div>
          <EvidencePathList rows={hdfsEvidence} empty="等待 HDFS 实验证据" />
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>数据清理与样本</h2>
              <p>保留原始数据，清理旧 smoke/history 产物。</p>
            </div>
            <HardDrive size={20} />
          </div>
          <EvidencePathList rows={localSamples} empty="等待本地样本快照" />
          <div className="cleanup-policy">
            {(evidence.data?.cleanup_policy.kept_spark_history_app_ids ?? []).slice(0, 6).map((appId) => (
              <span key={appId}>{appId}</span>
            ))}
          </div>
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>规模与 Cluster Mode</h2>
              <p>{evidence.data?.scale_boundary?.reason ?? '等待规模边界证据'}</p>
            </div>
            <GitBranch size={20} />
          </div>
          <dl>
            <dt>全量 Oct+Nov</dt>
            <dd>{evidence.data?.scale_boundary?.full_oct_nov_status ?? 'pending'}</dd>
            <dt>实验策略</dt>
            <dd>{evidence.data?.scale_boundary?.policy ?? 'pending'}</dd>
            <dt>Cluster mode</dt>
            <dd>{evidence.data?.cluster_mode?.status ?? 'pending'}</dd>
            <dt>提交脚本</dt>
            <dd>{evidence.data?.cluster_mode?.submit_script ?? 'pending'}</dd>
          </dl>
        </article>
      </section>

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>最近运行</h2>
            <p>SQLite 作业记录，按创建时间倒序。</p>
          </div>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>状态</th>
                <th>Run ID</th>
                <th>质量</th>
                <th>输入</th>
                <th>完成时间</th>
              </tr>
            </thead>
            <tbody>
              {(jobs.data?.rows ?? []).map((row) => (
                <tr key={row.job_id}>
                  <td><span className={`status-pill tone-${statusLabel(row.status)}`}>{statusLabel(row.status)}</span></td>
                  <td>{row.run_id ?? row.job_id}</td>
                  <td><span className={`quality-dot tone-${qualityTone(row.quality_status)}`} />{row.quality_status ?? 'pending'}</td>
                  <td>{row.input_snapshot?.actual_input_path ?? row.input_path ?? 'pending'}</td>
                  <td>{compactDate(row.finished_at)}</td>
                </tr>
              ))}
              {jobs.data?.rows.length === 0 ? (
                <tr>
                  <td colSpan={5}>暂无作业记录</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

function BenchmarkRow({ row }: { row: BenchmarkRun }) {
  return (
    <tr>
      <td>{row.sample}</td>
      <td>{variantLabel(row.variant)}</td>
      <td>{seconds(row.elapsed_seconds)}</td>
      <td>{safeNumber(metricNumber(row.rows_per_second))} rows/s</td>
      <td>{row.spark_application_id ?? 'local'}</td>
      <td>{safeNumber(metricNumber(row.task_count))}</td>
      <td>{bytes(row.memory_spill_bytes)}</td>
      <td>
        <span className={`quality-dot tone-${qualityTone(row.quality_status)}`} />
        {row.quality_status ?? row.spark_application_status ?? row.status}
      </td>
    </tr>
  );
}

function ModuleBenchmarkRow({ row }: { row: ModuleBenchmarkRun }) {
  return (
    <tr>
      <td>{row.profile ?? 'module'}</td>
      <td>{row.task_name ?? 'pipeline'}</td>
      <td>{safeNumber(metricNumber(row.input_rows))}</td>
      <td>{safeNumber(metricNumber(row.output_rows))}</td>
      <td>{seconds(row.elapsed_seconds ?? row.duration_seconds)}</td>
      <td>
        <span className={`quality-dot tone-${row.success ? 'success' : 'danger'}`} />
        {row.success ? 'passed' : 'failed'}
      </td>
    </tr>
  );
}

function EvidencePathList({ rows, empty }: { rows: EvidencePath[]; empty: string }) {
  if (!rows.length) return <span className="empty-copy">{empty}</span>;
  return (
    <div className="evidence-path-list">
      {rows.map((row) => (
        <div key={`${row.sample ?? row.name}-${row.path}`}>
          <strong>{row.sample ?? row.name ?? row.role}</strong>
          <span>{row.size_label ?? row.role ?? 'ready'}</span>
          <p>{row.path}</p>
        </div>
      ))}
    </div>
  );
}

function QualityCheckRow({ check }: { check: QualityCheck }) {
  const Icon = check.passed ? CheckCircle2 : XCircle;
  return (
    <div className={`quality-check tone-${check.passed ? 'success' : 'danger'}`}>
      <Icon size={16} />
      <span>{check.name}</span>
      <strong>
        {check.actual} {check.operator} {check.expected}
      </strong>
    </div>
  );
}
