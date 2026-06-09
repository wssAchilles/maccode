import { Activity, Database, FileJson } from 'lucide-react';
import { useJob, useJobLineage, useJobQuality, useSummary, useTopBrands } from '../api/hooks';
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

export function QualityPage() {
  const summary = useSummary();
  const brands = useTopBrands();
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
          value={historyStatus}
          detail={`spill ${formatNumber(metricNumber(sparkHistory?.memory_spill_bytes))} / failed tasks ${formatNumber(metricNumber(sparkHistory?.failed_task_count))}`}
          tone={statusTone(historyStatus === 'collected' ? 'passed' : historyStatus)}
        />
        <ChartPanel title="品牌销售额排行" subtitle="按 purchase 销售额聚合" option={barOption(brands.data ?? [], '销售额', '#a78bfa')} />
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
