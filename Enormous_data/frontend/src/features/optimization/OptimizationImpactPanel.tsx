import { Activity, BarChart3, CheckCircle2, Database, Gauge, ShieldCheck } from 'lucide-react';
import { useOptimizationImpact } from '../../api/hooks';
import { algorithmCopy, statusLabel } from '../../i18n/displayText';
import type { OptimizationImpactCard, OptimizationImpactTone } from '../../types/api';

type OptimizationImpactPanelProps = {
  compact?: boolean;
};

type OptimizationModuleStripProps = {
  moduleId: string;
  title: string;
};

const cardIcons = [Database, ShieldCheck, Activity, Gauge];

function statusPillTone(tone?: OptimizationImpactTone) {
  if (tone === 'success') return 'success';
  if (tone === 'danger') return 'failed';
  if (tone === 'running') return 'running';
  return 'queued';
}

function firstPresent<T>(rows: Array<T | null | undefined>, limit: number): T[] {
  return rows.filter((row): row is T => Boolean(row)).slice(0, limit);
}

function localizedImpactText(value?: string | null) {
  return algorithmCopy(value ?? '')
    .replaceAll('YARN-only CSV', '集群 CSV 基线')
    .replaceAll('AQE', '自适应执行')
    .replaceAll('History event log', '运行日志')
    .replaceAll('benchmark', '基准')
    .replaceAll('shuffle', '洗牌')
    .replaceAll('spill', '溢出')
    .replaceAll('相对 集群', '相对集群')
    .replaceAll('正式 基准 使用', '正式基准使用');
}

function localizedImpactMetric(value?: string | null) {
  if (!value) return '待生成';
  const failedMatch = value.match(/^(\d+(?:\.\d+)?) failed$/);
  if (failedMatch) return `${failedMatch[1]} 个失败任务`;
  const pathsMatch = value.match(/^(\d+(?:\.\d+)?) paths$/);
  if (pathsMatch) return `${pathsMatch[1]} 条路径`;
  return localizedImpactText(value);
}

export function OptimizationImpactPanel({ compact = false }: OptimizationImpactPanelProps) {
  const impact = useOptimizationImpact();
  const data = impact.data;

  if (impact.isError) {
    return <div className="error-banner">优化影响证据暂不可用，请先检查后端缓存与基准产物。</div>;
  }

  if (!data) {
    return (
      <section className="optimization-impact-panel" aria-label="优化影响加载中">
        <div className="optimization-impact-head">
          <div>
            <span className="eyebrow">优化影响</span>
            <h2>优化影响</h2>
            <p>正在读取优化后的前端展示证据。</p>
          </div>
          <span className="status-pill tone-queued">加载中</span>
        </div>
      </section>
    );
  }

  const highlights = compact
    ? firstPresent([data.performance_cards[0], data.performance_cards[1], data.data_layers[0]], 3)
    : firstPresent([data.data_layers[1], data.quality_gates[2], data.model_cards[1], data.performance_cards[0]], 4);
  const groups = [
    { title: '数据层', rows: data.data_layers },
    { title: '质量门禁', rows: data.quality_gates },
    { title: '模型影响', rows: data.model_cards },
    { title: '性能收益', rows: data.performance_cards },
  ];

  return (
    <section className={`optimization-impact-panel${compact ? ' is-compact' : ''}`} aria-label="优化后前端可见影响">
      <div className="optimization-impact-head">
        <div>
          <span className="eyebrow">优化影响</span>
          <h2>优化后前端可见影响</h2>
          <p>{localizedImpactText(data.headline)}</p>
        </div>
        <div className="optimization-impact-status">
          <span className={`status-pill tone-${statusPillTone(data.overall_tone)}`}>{statusLabel(data.overall_status)}</span>
          <small>{localizedImpactText(data.summary.primary_action)}</small>
        </div>
      </div>

      <div className="optimization-impact-summary" aria-label="优化影响摘要">
        <SummaryCell label="通过" value={data.summary.success_count ?? 0} tone="success" />
        <SummaryCell label="关注" value={data.summary.warning_count ?? 0} tone="warning" />
        <SummaryCell label="阻断" value={data.summary.danger_count ?? 0} tone="danger" />
        <SummaryCell label="页面" value={data.summary.visible_page_count ?? 0} tone="running" />
      </div>

      <div className="optimization-highlight-grid" aria-label="优化影响重点">
        {highlights.map((card, index) => (
          <ImpactCard card={card} iconIndex={index} key={card.id} />
        ))}
      </div>

      {compact ? null : (
        <div className="optimization-group-grid">
          {groups.map((group) => (
            <section className="optimization-group" key={group.title}>
              <div className="optimization-group-title">
                <h3>{group.title}</h3>
                <span>{group.rows.length}</span>
              </div>
              <div className="optimization-card-list">
                {group.rows.map((card, index) => (
                  <ImpactRow card={card} iconIndex={index} key={card.id} />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}

      {compact ? null : (
        <div className="frontend-impact-list" aria-label="前端页面体现">
          {data.frontend_sections.map((section) => (
            <div className={`frontend-impact-row tone-${section.tone}`} key={section.id}>
              <span>{section.page}</span>
              <strong>{section.visible_result}</strong>
              <small>{section.route}</small>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export function OptimizationModuleStrip({ moduleId, title }: OptimizationModuleStripProps) {
  const impact = useOptimizationImpact();
  const data = impact.data;
  const card =
    data?.model_cards.find((item) => item.id === moduleId) ??
    data?.quality_gates.find((item) => item.id === moduleId) ??
    data?.performance_cards.find((item) => item.id === moduleId);
  const section = data?.frontend_sections.find((item) => item.id === (moduleId.includes('forecast') ? 'forecasting' : 'recommendations'));

  if (!card) return null;

  return (
    <section className="optimization-mini-strip" aria-label={`${title}优化影响`}>
      <article className={`optimization-mini-card tone-${card.tone}`}>
        <div>
          <span className={`status-pill tone-${statusPillTone(card.tone)}`}>{statusLabel(card.status)}</span>
          <h2>{title}</h2>
          <p>{section?.visible_result ? localizedImpactText(section.visible_result) : localizedImpactText(card.detail)}</p>
        </div>
        <div className="optimization-mini-metric">
          <strong>{localizedImpactMetric(card.metric)}</strong>
          <small>{localizedImpactText(card.action)}</small>
        </div>
      </article>
    </section>
  );
}

function SummaryCell({ label, tone, value }: { label: string; tone: OptimizationImpactTone; value: number }) {
  return (
    <div className={`optimization-summary-cell tone-${tone}`}>
      <span>{label}</span>
      <strong>{value.toLocaleString()}</strong>
    </div>
  );
}

function ImpactCard({ card, iconIndex }: { card: OptimizationImpactCard; iconIndex: number }) {
  const Icon = cardIcons[iconIndex % cardIcons.length];
  return (
    <article className={`optimization-impact-card tone-${card.tone}`}>
      <div>
        <Icon size={18} />
        <span>{localizedImpactText(card.title)}</span>
      </div>
      <strong>{localizedImpactMetric(card.metric)}</strong>
      <p>{localizedImpactText(card.detail)}</p>
    </article>
  );
}

function ImpactRow({ card, iconIndex }: { card: OptimizationImpactCard; iconIndex: number }) {
  const Icon = card.tone === 'success' ? CheckCircle2 : iconIndex % 2 === 0 ? BarChart3 : Activity;
  return (
    <div className={`optimization-impact-row tone-${card.tone}`}>
      <Icon size={16} />
      <div>
        <span>{localizedImpactText(card.title)}</span>
        <strong>{localizedImpactMetric(card.metric)}</strong>
        <p>{localizedImpactText(card.action)}</p>
      </div>
    </div>
  );
}
