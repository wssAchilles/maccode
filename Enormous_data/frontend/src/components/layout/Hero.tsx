import { useEffect, useRef } from 'react';
import { animate, stagger } from 'animejs';
import { FileDown, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useRefreshJob } from '../../api/hooks';
import { DataGridMotion } from '../DataGridMotion';

export function Hero() {
  const heroRef = useRef<HTMLDivElement | null>(null);
  const navigate = useNavigate();
  const refresh = useRefreshJob();

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
        <p>React 前端独立运行，Flask 提供 API，Spark 负责离线清洗聚合。看板聚焦行为转化、销售趋势、数据质量和作业运行状态。</p>
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
