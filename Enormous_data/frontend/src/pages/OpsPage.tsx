import { Activity, CheckCircle2, Database, FileJson, GitBranch, Play, ShieldCheck, XCircle } from 'lucide-react';
import { useJob, useJobLineage, useJobQuality, useJobs, useRefreshJob } from '../api/hooks';
import { compactDate } from '../lib/format';
import type { JobStatus, QualityCheck } from '../types/api';

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

function metricNumber(value: unknown): number | undefined {
  return typeof value === 'number' ? value : undefined;
}

function jobMessage(job?: JobStatus) {
  if (!job?.message) return '等待首次运行';
  const lines = job.message.split('\n').filter(Boolean);
  return lines.at(-1) ?? job.message;
}

export function OpsPage() {
  const job = useJob();
  const jobs = useJobs(8);
  const currentJobId = job.data?.job_id ?? jobs.data?.rows[0]?.job_id;
  const lineage = useJobLineage(currentJobId);
  const quality = useJobQuality(currentJobId);
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
  const isActive = activeStatuses.has(latest?.status ?? '');

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

      <section className="ops-kpi-grid">
        <article className="metric-card tone-success">
          <span>质量门禁</span>
          <strong>{quality.data?.quality_status ?? latest?.quality_status ?? 'pending'}</strong>
          <small>{checks.length ? `${checks.filter((check) => check.passed).length}/${checks.length} checks passed` : '等待 Spark manifest'}</small>
        </article>
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
      </section>

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
