import { Activity, BarChart3, CheckCircle2, Database, FileJson, GitBranch, HardDrive, Play, ShieldCheck, XCircle } from 'lucide-react';
import { useJob, useJobLineage, useJobQuality, useJobs, useOpsEvidence, useRefreshJob } from '../api/hooks';
import { ChartPanel } from '../components/ChartPanel';
import { OptimizationImpactPanel } from '../features/optimization/OptimizationImpactPanel';
import { fieldLabel, statusLabel as localizedStatusLabel } from '../i18n/displayText';
import { barOption } from '../lib/chartOptions';
import { compactDate } from '../lib/format';
import type { BenchmarkRun, EvidencePath, JobGovernanceArtifact, JobGovernanceStage, JobStatus, ModuleBenchmarkRun, QualityCheck, SparkHistoryMetrics } from '../types/api';

const activeStatuses = new Set(['queued', 'running']);

function statusLabel(status?: string) {
  if (!status) return 'pending';
  if (status === 'succeeded') return 'succeeded';
  if (status === 'success') return 'succeeded';
  return status;
}

function shortHash(hash?: string | null) {
  return hash ? hash.slice(0, 12) : '待生成';
}

function qualityTone(status?: string | null) {
  if (status === 'passed') return 'success';
  if (status === 'failed') return 'danger';
  return 'warning';
}

function safeNumber(value?: number) {
  return typeof value === 'number' ? value.toLocaleString() : '待生成';
}

function seconds(value?: number | null) {
  return typeof value === 'number' ? `${value.toFixed(1)}s` : '待生成';
}

function bytes(value?: number | null) {
  if (typeof value !== 'number') return '待生成';
  if (value >= 1024 ** 3) return `${(value / 1024 ** 3).toFixed(1)} GB`;
  if (value >= 1024 ** 2) return `${(value / 1024 ** 2).toFixed(1)} MB`;
  if (value >= 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${value} B`;
}

function percent(value?: number | null) {
  return typeof value === 'number' ? `${Math.round(value * 100)}%` : '待生成';
}

function metricNumber(value: unknown): number | undefined {
  return typeof value === 'number' ? value : undefined;
}

function jobMessage(job?: JobStatus) {
  if (!job?.message) return '等待首次运行';
  const lines = job.message.split('\n').filter(Boolean);
  const lastLine = lines.at(-1) ?? job.message;
  const finished = lastLine.match(/Spark job finished:\s*raw=(\d+)\s+cleaned=(\d+)\s+sales=([\d.]+)\s+elapsed=([\d.]+)s/);
  if (finished) {
    return `Spark 计算完成：原始 ${Number(finished[1]).toLocaleString()} 行，清洗后 ${Number(finished[2]).toLocaleString()} 行，成交额 ${Number(finished[3]).toLocaleString()}，耗时 ${Number(finished[4]).toFixed(1)} 秒`;
  }
  return lastLine.replace('Spark job finished', 'Spark 计算完成').replace('Spark refresh failed', 'Spark 刷新失败');
}

function variantLabel(variant: string) {
  const labels: Record<string, string> = {
    baseline_local_csv: '本地 CSV 基线',
    yarn_only_csv: '集群 CSV 基线',
    yarn_aqe_csv: '集群自适应执行',
    yarn_algorithm_csv: '集群算法优化',
    yarn_parquet: '集群 Parquet',
  };
  return labels[variant] ?? variant;
}

function sampleLabel(sample?: string | null) {
  const labels: Record<string, string> = {
    '1pct': '1% 样本',
    '5pct': '5% 样本',
    smoke: '冒烟样本',
    raw_oct: '10 月原始数据',
    raw_nov: '11 月原始数据',
  };
  return sample ? labels[sample] ?? sample : '样本';
}

function moduleLabel(value?: string | null) {
  const labels: Record<string, string> = {
    affinity: '商品关系',
    anomaly: '异常检测',
    experimentation: '实验分析',
    recommendation: '推荐模块',
    affinity_pipeline: '商品关系流水线',
    anomaly_pipeline: '异常检测流水线',
    experimentation_pipeline: '实验分析流水线',
    recommendation_pipeline: '推荐流水线',
    module: '算法模块',
    pipeline: '处理流水线',
  };
  return value ? labels[value] ?? value : '待生成';
}

function stageLabel(stage?: string | null) {
  const labels: Record<string, string> = {
    queued: '进入队列',
    spark_execution: 'Spark 计算',
    history_metrics: '运行指标采集',
    quality_gate: '质量门禁',
    artifact_publish: '产物发布',
  };
  return stage ? labels[stage] ?? stage : '待生成';
}

function artifactLabel(artifact?: string | null) {
  const labels: Record<string, string> = {
    run_manifest: '运行清单',
    dashboard_cube_summary: '指标层摘要',
    dashboard_cube_semantics: '指标语义',
    dashboard_cube_total: '物化汇总层',
    dashboard_cube_daily: '日级趋势层',
    feature_mart_summary: '特征集市摘要',
    feature_mart_freshness: '特征新鲜度',
    recommendation_evaluation: '推荐评估',
    forecasting_evaluation: '预测评估',
    anomaly_incidents: '异常事件',
    optimization_plan: '优化计划',
  };
  return artifact ? labels[artifact] ?? artifact : '产物';
}

function opsCopy(value?: string | null) {
  const labels: Record<string, string> = {
    'YARN-only increased scheduling overhead; AQE and algorithm guards made runtime and memory risk controllable.':
      '集群 CSV 基线调度开销较高，自适应执行与算法护栏让耗时和内存风险更可控。',
    'The experiment intentionally uses representative partial data instead of running the full Oct+Nov dataset.':
      '本阶段采用代表性抽样数据验证，不运行 10 月与 11 月全量数据。',
    typical_partial_only: '代表性抽样验证',
    entrypoint_ready_not_default: '入口已就绪，默认未启用',
    not_run_by_request: '按要求暂不运行',
    csv_input: 'CSV 输入',
    parquet_input: 'Parquet 输入',
  };
  return value ? labels[value] ?? value : '待生成';
}

function toneFromStatus(status?: string | null) {
  if (['succeeded', 'success', 'passed', 'collected', 'published', 'fresh', 'SUCCEEDED'].includes(status ?? '')) return 'success';
  if (['queued', 'running'].includes(status ?? '')) return 'running';
  if (['warning', 'needs_review', 'degraded', 'stale', 'skipped', 'not_configured'].includes(status ?? '')) return 'warning';
  if (['failed', 'rejected', 'missing', 'FAILED'].includes(status ?? '')) return 'danger';
  return 'warning';
}

function barWidth(value?: number | null, max = 1) {
  if (typeof value !== 'number' || !Number.isFinite(value) || max <= 0) return '0%';
  return `${Math.max(4, Math.min(100, (value / max) * 100))}%`;
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
  const governance = lineage.data?.governance ?? quality.data?.governance ?? latest?.governance;
  const governanceArtifacts = governance?.artifacts ?? [];
  const governanceStages = governance?.stages ?? [];
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
  const freshArtifactCount = governanceArtifacts.filter((artifact) => artifact.status === 'fresh').length;
  const benchmarkRuntimeRows = benchmarkRows
    .filter((row) => typeof row.elapsed_seconds === 'number')
    .map((row) => ({ name: `${sampleLabel(row.sample)} · ${variantLabel(row.variant)}`, value: row.elapsed_seconds ?? 0 }));
  const benchmarkSpillRows = benchmarkRows
    .filter((row) => typeof row.memory_spill_bytes === 'number')
    .map((row) => ({ name: `${sampleLabel(row.sample)} · ${variantLabel(row.variant)}`, value: Math.round(((row.memory_spill_bytes ?? 0) / 1024 ** 3) * 10) / 10 }));

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">管道运维</span>
        <h1>作业治理与运行血缘</h1>
        <p>围绕真实 Kaggle 行为数据集跟踪 Spark 运行、HDFS 输入、质量门禁和缓存产物。</p>
      </section>

      <section className="ops-command-band">
        <div>
          <span className={`status-pill tone-${statusLabel(latest?.status)}`}>{localizedStatusLabel(statusLabel(latest?.status))}</span>
          <h2>{latest?.run_id ?? latest?.job_id ?? '尚未生成运行记录'}</h2>
          <p>{jobMessage(latest)}</p>
        </div>
        <button className="primary-action compact" disabled={refresh.isPending || isActive} onClick={() => refresh.mutate()} type="button">
          <Play size={16} />
          {refresh.isPending || isActive ? '运行中' : '启动 Spark'}
        </button>
      </section>

      <OptimizationImpactPanel compact />

      <section className="ops-triage-grid" aria-label="作业首屏判断">
        <article className={`triage-card tone-${statusLabel(latest?.status) === 'succeeded' ? 'success' : activeStatuses.has(latest?.status ?? '') ? 'running' : 'warning'}`}>
          <span>最新运行</span>
          <strong>{localizedStatusLabel(statusLabel(latest?.status))}</strong>
          <small>{latest?.elapsed_seconds ? `${latest.elapsed_seconds}s` : '等待耗时'}</small>
          <p>{sparkAppId ?? '等待 Spark 应用 ID'}</p>
        </article>
        <article className={`triage-card tone-${failureStage === 'none' ? 'success' : 'danger'}`}>
          <span>失败阶段</span>
          <strong>{localizedStatusLabel(failureStage)}</strong>
          <small>{localizedStatusLabel(sparkHistoryStatus)}</small>
          <p>{latest?.error ?? '当前没有失败阶段。'}</p>
        </article>
        <article className={`triage-card tone-${qualityTone(quality.data?.quality_status ?? latest?.quality_status)}`}>
          <span>质量门禁</span>
          <strong>{localizedStatusLabel(quality.data?.quality_status ?? latest?.quality_status)}</strong>
          <small>{checks.length ? `${checksPassed}/${checks.length} 项检查通过` : '等待 Spark 清单'}</small>
          <p>{localizedStatusLabel(qualityReport?.gate?.status ?? 'not evaluated')}</p>
        </article>
        <article className={`triage-card tone-${toneFromStatus(governance?.status)}`}>
          <span>发布状态</span>
          <strong>{localizedStatusLabel(governance?.status)}</strong>
          <small>{freshArtifactCount}/{governanceArtifacts.length || 0} 个产物新鲜</small>
          <p>当前阶段：{stageLabel(governance?.active_stage)}</p>
        </article>
      </section>

      <section className="ops-visual-grid" aria-label="运行治理图">
        <article className="data-panel ops-card ops-wide-card">
          <div className="panel-title">
            <div>
              <h2>运行阶段时间轴</h2>
              <p>按队列、计算、指标采集、质量门禁和产物发布追踪一次刷新。</p>
            </div>
            <Activity size={20} />
          </div>
          <RunStageTimeline stages={governanceStages} />
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>产物新鲜度</h2>
              <p>物化层和算法产物按 24 小时服务承诺判定。</p>
            </div>
            <Database size={20} />
          </div>
          <ArtifactFreshnessList artifacts={governanceArtifacts} />
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>Spark 资源信号</h2>
              <p>失败任务、重试、溢出和洗牌读写作为运行健康证据。</p>
            </div>
            <BarChart3 size={20} />
          </div>
          <SparkResourceBars summary={governance?.spark_summary ?? sparkHistory} />
        </article>
      </section>

      <section className="ops-chart-grid" aria-label="基准运行图表">
        <ChartPanel
          title="基准耗时对比"
          subtitle="不同运行方案的端到端耗时，越低越好。"
          option={barOption(benchmarkRuntimeRows, '运行耗时（秒）', '#28d7c2', false)}
          summary={opsCopy(benchmarkSummary?.interpretation ?? '等待基准汇总数据')}
        />
        <ChartPanel
          title="内存溢出对比"
          subtitle="Spark 内存溢出规模，越低代表执行更稳定。"
          option={barOption(benchmarkSpillRows, '内存溢出（GB）', '#f59e0b', false)}
          summary="结合耗时一起看，避免只追求速度而放大资源风险。"
        />
      </section>

      <details className="ops-detail-disclosure">
        <summary>查看完整运行指标</summary>
        <section className="ops-kpi-grid">
          <article className="metric-card">
            <span>输入文件</span>
            <strong>{safeNumber(inputSnapshot?.file_count)}</strong>
            <small>{inputSnapshot?.storage_mode ?? latest?.storage_mode ?? '未知存储'}</small>
          </article>
          <article className="metric-card">
            <span>清洗行数</span>
            <strong>{safeNumber(qualityReport?.metrics?.cleaned_rows)}</strong>
            <small>剔除比例 {qualityReport?.metrics?.removed_ratio ?? '待生成'}</small>
          </article>
          <article className="metric-card">
            <span>配置指纹</span>
            <strong>{shortHash(lineage.data?.config_hash ?? latest?.config_hash)}</strong>
            <small>{lineage.data?.contract_version ?? latest?.contract_version ?? '契约待生成'}</small>
          </article>
          <article className="metric-card">
            <span>Spark 状态</span>
            <strong>{localizedStatusLabel(sparkStatus)}</strong>
            <small>{sparkAppId ?? '等待 Spark 应用 ID'}</small>
          </article>
          <article className="metric-card">
            <span>History 指标</span>
            <strong>{localizedStatusLabel(sparkHistoryStatus)}</strong>
            <small>内存溢出 {safeNumber(metricNumber(sparkHistory?.memory_spill_bytes))}，失败任务 {safeNumber(metricNumber(sparkHistory?.failed_task_count))}</small>
          </article>
          <article className="metric-card tone-success">
            <span>自适应执行/算法加速</span>
            <strong>{benchmarkSummary?.yarn_only_to_algorithm_speedup ? `${benchmarkSummary.yarn_only_to_algorithm_speedup}x` : '待生成'}</strong>
            <small>相对集群 CSV 基线</small>
          </article>
          <article className="metric-card tone-success">
            <span>History 采集</span>
            <strong>{safeNumber(historySummary?.collected_run_count)}</strong>
            <small>失败 {safeNumber(historySummary?.failed_task_count)}，重试 {safeNumber(historySummary?.retried_task_count)}</small>
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
            <dt>作业编号</dt>
            <dd>{latest?.job_id ?? '待生成'}</dd>
            <dt>运行编号</dt>
            <dd>{latest?.run_id ?? '待生成'}</dd>
            <dt>开始时间</dt>
            <dd>{compactDate(latest?.started_at)}</dd>
            <dt>完成时间</dt>
            <dd>{compactDate(latest?.finished_at)}</dd>
            <dt>耗时</dt>
            <dd>{latest?.elapsed_seconds ? `${latest.elapsed_seconds}s` : '待生成'}</dd>
            <dt>失败阶段</dt>
            <dd>{localizedStatusLabel(quality.data?.failure_stage ?? latest?.failure_stage ?? 'none')}</dd>
          </dl>
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>输入血缘</h2>
              <p>HDFS 源文件和输出运行清单。</p>
            </div>
            <GitBranch size={20} />
          </div>
          <dl>
            <dt>实际输入</dt>
            <dd>{inputSnapshot?.actual_input_path ?? latest?.input_path ?? '待生成'}</dd>
            <dt>配置输入</dt>
            <dd>{inputSnapshot?.configured_input_path ?? '待生成'}</dd>
            <dt>运行清单</dt>
            <dd>{outputArtifacts?.run_manifest_path ?? outputArtifacts?.manifest_path ?? '待生成'}</dd>
            <dt>指标目录</dt>
            <dd>{outputArtifacts?.metrics_dir ?? '待生成'}</dd>
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
              <p>从 Spark 输入文件清单采集。</p>
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
              <h2>基准证据</h2>
              <p>{opsCopy(benchmarkSummary?.interpretation ?? '等待基准汇总数据')}</p>
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
                <th>集群应用</th>
                <th>任务</th>
                <th>内存溢出</th>
                <th>质量</th>
              </tr>
            </thead>
            <tbody>
              {benchmarkRows.map((row) => <BenchmarkRow row={row} key={`${row.sample}-${row.variant}`} />)}
              {benchmarkRows.length === 0 ? (
                <tr>
                  <td colSpan={8}>暂无基准证据</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>典型模块基准</h2>
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
                  <td colSpan={6}>暂无模块基准证据</td>
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
              <p>正式基准使用的 CSV 与 Parquet 输入。</p>
            </div>
            <Database size={20} />
          </div>
          <EvidencePathList rows={hdfsEvidence} empty="等待 HDFS 实验证据" />
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>数据清理与样本</h2>
              <p>保留原始数据，清理旧试运行和运行日志产物。</p>
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
              <h2>规模与集群模式</h2>
              <p>{opsCopy(evidence.data?.scale_boundary?.reason ?? '等待规模边界证据')}</p>
            </div>
            <GitBranch size={20} />
          </div>
          <dl>
            <dt>全量 10 月 + 11 月</dt>
            <dd>{localizedStatusLabel(evidence.data?.scale_boundary?.full_oct_nov_status ?? 'pending')}</dd>
            <dt>实验策略</dt>
            <dd>{opsCopy(evidence.data?.scale_boundary?.policy)}</dd>
            <dt>集群模式</dt>
            <dd>{localizedStatusLabel(evidence.data?.cluster_mode?.status ?? 'pending')}</dd>
            <dt>提交脚本</dt>
            <dd>{evidence.data?.cluster_mode?.submit_script ?? '待生成'}</dd>
          </dl>
        </article>
      </section>

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>最近运行</h2>
            <p>本地作业记录，按创建时间倒序。</p>
          </div>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>状态</th>
                <th>运行编号</th>
                <th>质量</th>
                <th>输入</th>
                <th>完成时间</th>
              </tr>
            </thead>
            <tbody>
              {(jobs.data?.rows ?? []).map((row) => (
                <tr key={row.job_id}>
                  <td><span className={`status-pill tone-${statusLabel(row.status)}`}>{localizedStatusLabel(statusLabel(row.status))}</span></td>
                  <td>{row.run_id ?? row.job_id}</td>
                  <td><span className={`quality-dot tone-${qualityTone(row.quality_status)}`} />{localizedStatusLabel(row.quality_status)}</td>
                  <td>{row.input_snapshot?.actual_input_path ?? row.input_path ?? '待生成'}</td>
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

function RunStageTimeline({ stages }: { stages: JobGovernanceStage[] }) {
  if (!stages.length) return <span className="empty-copy">等待运行阶段数据</span>;
  return (
    <ol className="ops-stage-timeline">
      {stages.map((stage) => (
        <li className={`tone-${toneFromStatus(stage.status)}`} key={stage.stage}>
          <span>{stageLabel(stage.stage)}</span>
          <strong>{localizedStatusLabel(stage.status)}</strong>
          <small>{stage.duration_seconds ? seconds(stage.duration_seconds) : compactDate(stage.finished_at ?? stage.started_at)}</small>
        </li>
      ))}
    </ol>
  );
}

function ArtifactFreshnessList({ artifacts }: { artifacts: JobGovernanceArtifact[] }) {
  if (!artifacts.length) return <span className="empty-copy">等待产物清单</span>;
  return (
    <div className="ops-freshness-list">
      {artifacts.slice(0, 7).map((artifact) => {
        const elapsed = artifact.age_minutes ?? 0;
        const sla = artifact.freshness_sla_minutes ?? 1;
        return (
          <div className="ops-freshness-row" key={artifact.artifact_id} title={artifact.path}>
            <div>
              <strong>{artifactLabel(artifact.artifact_id)}</strong>
              <span className={`status-pill tone-${toneFromStatus(artifact.status)}`}>{localizedStatusLabel(artifact.status)}</span>
            </div>
            <div className="ops-freshness-track" aria-label={`${artifactLabel(artifact.artifact_id)}新鲜度`}>
              <span className={`tone-${toneFromStatus(artifact.status)}`} style={{ width: artifact.exists ? barWidth(sla - elapsed, sla) : '0%' }} />
            </div>
            <small>{artifact.updated_at ? `${compactDate(artifact.updated_at)} 更新` : '等待发布'}</small>
          </div>
        );
      })}
    </div>
  );
}

function SparkResourceBars({ summary }: { summary?: SparkHistoryMetrics | null }) {
  const rows = [
    { label: '失败任务', value: metricNumber(summary?.failed_task_count), format: safeNumber },
    { label: '重试任务', value: metricNumber(summary?.retried_task_count), format: safeNumber },
    { label: '内存溢出', value: metricNumber(summary?.memory_spill_bytes), format: bytes },
    { label: '磁盘溢出', value: metricNumber(summary?.disk_spill_bytes), format: bytes },
    { label: '洗牌读取', value: metricNumber(summary?.shuffle_read_bytes), format: bytes },
    { label: '洗牌写入', value: metricNumber(summary?.shuffle_write_bytes), format: bytes },
  ];
  const maxValue = Math.max(1, ...rows.map((row) => row.value ?? 0));
  return (
    <div className="ops-resource-bars">
      {rows.map((row) => (
        <div className="ops-resource-row" key={row.label}>
          <span>{row.label}</span>
          <div className="ops-resource-track">
            <strong style={{ width: barWidth(row.value, maxValue) }} />
          </div>
          <small>{row.format(row.value)}</small>
        </div>
      ))}
      <p>采集状态：{localizedStatusLabel(summary?.history_metrics_status ?? 'not_configured')}</p>
    </div>
  );
}

function BenchmarkRow({ row }: { row: BenchmarkRun }) {
  return (
    <tr>
      <td>{sampleLabel(row.sample)}</td>
      <td>{variantLabel(row.variant)}</td>
      <td>{seconds(row.elapsed_seconds)}</td>
      <td>{safeNumber(metricNumber(row.rows_per_second))} 行/秒</td>
      <td>{row.spark_application_id ?? '本地'}</td>
      <td>{safeNumber(metricNumber(row.task_count))}</td>
      <td>{bytes(row.memory_spill_bytes)}</td>
      <td>
        <span className={`quality-dot tone-${qualityTone(row.quality_status)}`} />
        {localizedStatusLabel(row.quality_status ?? row.spark_application_status ?? row.status)}
      </td>
    </tr>
  );
}

function ModuleBenchmarkRow({ row }: { row: ModuleBenchmarkRun }) {
  return (
    <tr>
      <td>{moduleLabel(row.profile ?? 'module')}</td>
      <td>{moduleLabel(row.task_name ?? 'pipeline')}</td>
      <td>{safeNumber(metricNumber(row.input_rows))}</td>
      <td>{safeNumber(metricNumber(row.output_rows))}</td>
      <td>{seconds(row.elapsed_seconds ?? row.duration_seconds)}</td>
      <td>
        <span className={`quality-dot tone-${row.success ? 'success' : 'danger'}`} />
        {localizedStatusLabel(row.success ? 'passed' : 'failed')}
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
          <strong>{sampleLabel(row.sample ?? row.name ?? row.role)}</strong>
          <span>{row.size_label ?? opsCopy(row.role) ?? '就绪'}</span>
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
      <span>{fieldLabel(check.name)}</span>
      <strong>
        {check.actual} {check.operator} {check.expected}
      </strong>
    </div>
  );
}
