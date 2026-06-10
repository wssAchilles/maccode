import { Activity, Database, FileJson } from 'lucide-react';
import { useJob, useJobLineage, useJobQuality, useOpsEvidence, useSummary, useTopBrands } from '../api/hooks';
import { ChartPanel } from '../components/ChartPanel';
import { MetricCard } from '../components/MetricCard';
import { barOption } from '../lib/chartOptions';
import { formatNumber } from '../lib/format';

function statusTone(status?: string | null): 'success' | 'warning' | 'danger' {
  if (status === 'passed' || status === 'SUCCEEDED' || status === 'succeeded') return 'success';
  if (status === 'failed' || status === 'FAILED') return 'danger';
  return 'warning';
}

function metricNumber(value: unknown): number | undefined {
  return typeof value === 'number' ? value : undefined;
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

export function QualityPage() {
  const summary = useSummary();
  const brands = useTopBrands();
  const evidence = useOpsEvidence();
  const job = useJob();
  const currentJobId = job.data?.job_id;
  const lineage = useJobLineage(currentJobId);
  const quality = useJobQuality(currentJobId);
  const latest = job.data;
  const inputSnapshot = lineage.data?.input_snapshot ?? latest?.input_snapshot;
  const qualityReport = quality.data?.quality_report ?? latest?.quality_report;
  const sparkHistory = quality.data?.spark_history_metrics ?? lineage.data?.spark_history_metrics ?? latest?.spark_history_metrics;
  const sparkStatus = quality.data?.spark_application_status ?? lineage.data?.spark_application_status ?? latest?.spark_application_status;
  const historyStatus =
    quality.data?.spark_history_metrics_status ?? lineage.data?.spark_history_metrics_status ?? latest?.spark_history_metrics_status ?? 'not_configured';

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">Data quality</span>
        <h1>数据质量与清洗结果</h1>
        <p>展示缺失值、异常值、重复值处理结果，让 Spark 清洗过程可解释、可验收。</p>
      </section>
      <section className="quality-grid">
        <MetricCard label="剔除行数" value={formatNumber(summary.data?.removed_rows)} detail="无效时间、价格异常或缺关键字段" tone="danger" />
        <MetricCard label="异常价格" value={formatNumber(summary.data?.invalid_price_rows)} detail="price < 0 或过大" tone="danger" />
        <MetricCard label="空品牌" value={formatNumber(summary.data?.missing_brand_rows)} detail="统一填充为 unknown" tone="warning" />
        <MetricCard label="重复事件" value={formatNumber(summary.data?.duplicate_rows)} detail="按事件关键字段去重" />
        <MetricCard
          label="Spark 状态"
          value={sparkStatus ?? 'pending'}
          detail={latest?.spark_application_id ?? '等待 application id'}
          tone={statusTone(sparkStatus)}
        />
        <MetricCard
          label="质量门禁"
          value={quality.data?.quality_status ?? latest?.quality_status ?? 'pending'}
          detail={`${qualityReport?.gate?.checks?.filter((check) => check.passed).length ?? 0}/${qualityReport?.gate?.checks?.length ?? 0} checks passed`}
          tone={statusTone(quality.data?.quality_status ?? latest?.quality_status)}
        />
        <MetricCard
          label="HDFS 文件"
          value={formatNumber(inputSnapshot?.file_count)}
          detail={inputSnapshot?.storage_mode ?? latest?.storage_mode ?? 'unknown storage'}
        />
        <MetricCard
          label="History 指标"
          value={evidence.data?.history_summary?.collected_run_count ? `${evidence.data.history_summary.collected_run_count} runs` : historyStatus}
          detail={`failed ${formatNumber(evidence.data?.history_summary?.failed_task_count ?? metricNumber(sparkHistory?.failed_task_count))} / spill ${bytes(evidence.data?.history_summary?.memory_spill_bytes ?? metricNumber(sparkHistory?.memory_spill_bytes))}`}
          tone={statusTone(historyStatus === 'collected' ? 'passed' : historyStatus)}
        />
        <ChartPanel title="品牌销售额排行" subtitle="按 purchase 销售额聚合" option={barOption(brands.data ?? [], '销售额', '#a78bfa')} />
      </section>

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>实验质量证据</h2>
            <p>{evidence.data?.benchmark_summary.interpretation ?? '等待 benchmark 汇总数据'}</p>
          </div>
          <Activity size={20} />
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>样本</th>
                <th>对照组</th>
                <th>耗时</th>
                <th>任务</th>
                <th>失败任务</th>
                <th>Memory spill</th>
                <th>质量</th>
              </tr>
            </thead>
            <tbody>
              {(evidence.data?.benchmark_runs ?? []).map((row) => (
                <tr key={`${row.sample}-${row.variant}`}>
                  <td>{row.sample}</td>
                  <td>{row.variant}</td>
                  <td>{seconds(row.elapsed_seconds)}</td>
                  <td>{formatNumber(metricNumber(row.task_count))}</td>
                  <td>{formatNumber(metricNumber(row.failed_task_count))}</td>
                  <td>{bytes(row.memory_spill_bytes)}</td>
                  <td><span className={`status-pill tone-${statusTone(row.quality_status)}`}>{row.quality_status ?? row.status}</span></td>
                </tr>
              ))}
              {evidence.data?.benchmark_runs.length === 0 ? (
                <tr>
                  <td colSpan={7}>暂无实验质量证据</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>典型模块质量</h2>
            <p>{evidence.data?.scale_boundary?.conclusion ?? '使用部分典型数据验证模块级输出规模。'}</p>
          </div>
          <Database size={20} />
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>模块</th>
                <th>输入行</th>
                <th>输出行</th>
                <th>耗时</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              {(evidence.data?.module_benchmark_runs ?? []).map((row) => (
                <tr key={`${row.profile}-${row.task_name}`}>
                  <td>{row.profile}</td>
                  <td>{formatNumber(metricNumber(row.input_rows))}</td>
                  <td>{formatNumber(metricNumber(row.output_rows))}</td>
                  <td>{seconds(row.elapsed_seconds ?? row.duration_seconds)}</td>
                  <td><span className={`status-pill tone-${row.success ? 'success' : 'danger'}`}>{row.success ? 'passed' : 'failed'}</span></td>
                </tr>
              ))}
              {evidence.data?.module_benchmark_runs?.length === 0 ? (
                <tr>
                  <td colSpan={5}>暂无模块质量证据</td>
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
              <h2>YARN / HDFS 快照</h2>
              <p>{inputSnapshot?.actual_input_path ?? latest?.input_path ?? 'pending'}</p>
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

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>Spark History</h2>
              <p>{quality.data?.spark_history_metrics_error ?? latest?.spark_history_metrics_error ?? 'metrics ready'}</p>
            </div>
            <Activity size={20} />
          </div>
          <dl>
            <dt>Shuffle read</dt>
            <dd>{formatNumber(metricNumber(sparkHistory?.shuffle_read_bytes))}</dd>
            <dt>Shuffle write</dt>
            <dd>{formatNumber(metricNumber(sparkHistory?.shuffle_write_bytes))}</dd>
            <dt>Memory spill</dt>
            <dd>{formatNumber(metricNumber(sparkHistory?.memory_spill_bytes))}</dd>
            <dt>Retried tasks</dt>
            <dd>{formatNumber(metricNumber(sparkHistory?.retried_task_count))}</dd>
          </dl>
        </article>
      </section>
    </>
  );
}
