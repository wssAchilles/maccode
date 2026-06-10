import { useEffect, useRef } from 'react';
import { animate, stagger } from 'animejs';
import { FileDown, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useJob, useRefreshJob, useSummary } from '../../api/hooks';
import { compactDate, formatNumber } from '../../lib/format';
import { DataGridMotion } from '../DataGridMotion';

export function Hero() {
  const heroRef = useRef<HTMLDivElement | null>(null);
  const navigate = useNavigate();
  const refresh = useRefreshJob();
  const summary = useSummary();
  const job = useJob();
  const latestRun = job.data?.run_id ?? job.data?.job_id ?? '暂无运行';
  const finishedAt = compactDate(job.data?.finished_at ?? job.data?.started_at);
  const qualityStatus = job.data?.quality_status ?? (job.data?.status === 'succeeded' ? 'passed' : 'pending');

  useEffect(() => {
    if (!heroRef.current) return;
    animate('.motion-grid span', {
      scale: [0.35, 1],
      opacity: [0.2, 0.95],
      delay: stagger(16, { grid: [12, 8], from: 'center' }),
      duration: 850,
      ease: 'out(3)',
    });
    animate('.hero-copy > *', {
      translateY: [16, 0],
      opacity: [0, 1],
      delay: stagger(90),
      duration: 720,
      ease: 'out(3)',
    });
  }, []);

  return (
    <header className="hero" ref={heroRef}>
      <DataGridMotion />
      <div className="hero-copy">
        <span className="eyebrow">Kaggle ecommerce behavior dataset</span>
        <h1>电商用户行为大数据分析工作台</h1>
        <p>把 Spark 作业、质量门禁和核心行为指标收在一个桌面工作台里，先判断数据是否可信，再进入转化、推荐和明细追踪。</p>
        <dl className="hero-insights" aria-label="数据运行摘要">
          <div>
            <dt>最近运行</dt>
            <dd>{latestRun.slice(0, 18)}</dd>
          </div>
          <div>
            <dt>刷新时间</dt>
            <dd>{finishedAt}</dd>
          </div>
          <div>
            <dt>有效事件</dt>
            <dd>{formatNumber(summary.data?.cleaned_rows)}</dd>
          </div>
          <div>
            <dt>质量状态</dt>
            <dd>{qualityStatus}</dd>
          </div>
        </dl>
      </div>
      <div className="hero-actions">
        <button className="primary-action" onClick={() => refresh.mutate()} disabled={refresh.isPending} type="button">
          <RefreshCw size={18} className={refresh.isPending ? 'spin' : ''} />
          {refresh.isPending ? '启动中' : '刷新 Spark'}
        </button>
        <button className="secondary-action" type="button" onClick={() => navigate('/table')}>
          <FileDown size={18} />
          查看明细
        </button>
      </div>
    </header>
  );
}
