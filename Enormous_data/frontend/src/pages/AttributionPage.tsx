import {
  ArrowRight,
  BadgeDollarSign,
  GitCompareArrows,
  MousePointerClick,
  Route,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
import { useMemo, useState, type CSSProperties } from 'react';
import {
  useAttributionAssists,
  useAttributionEntities,
  useAttributionModels,
  useAttributionPaths,
  useAttributionQuality,
  useAttributionSummary,
} from '../api/hooks';
import { ChartPanel } from '../components/ChartPanel';
import { displayValue, fieldLabel, label, listLabels, statusLabel } from '../i18n/displayText';
import { barOption } from '../lib/chartOptions';

type AttributionRevenueFields = {
  first_touch_revenue?: number | null;
  last_touch_revenue?: number | null;
  linear_assisted_revenue?: number | null;
  time_decay_assisted_revenue?: number | null;
};

function money(value?: number | null) {
  return typeof value === 'number' ? `¥${value.toLocaleString()}` : '待生成';
}

function number(value?: number | null) {
  return typeof value === 'number' ? value.toLocaleString() : '待生成';
}

function percent(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '待生成';
}

function score(value?: number | null) {
  return typeof value === 'number' ? value.toFixed(3) : '待生成';
}

function statusTone(status?: string) {
  return status === 'passed' ? 'success' : status === 'needs_review' ? 'queued' : 'failed';
}

function modelLabel(model: string) {
  return label('attributionModel', model);
}

function entityLabel(entityType: string) {
  return label('entityType', entityType);
}

function modelRevenue(row: AttributionRevenueFields | null | undefined, model: string) {
  if (!row) return null;
  if (model === 'first_touch') return row.first_touch_revenue;
  if (model === 'last_touch') return row.last_touch_revenue;
  if (model === 'linear') return row.linear_assisted_revenue;
  return row.time_decay_assisted_revenue;
}

function modelRows(row: AttributionRevenueFields | null | undefined) {
  if (!row) return [];
  const values = modelOptions.map((option) => ({
    name: option.label,
    raw: modelRevenue(row, option.value) ?? 0,
  }));
  const minValue = Math.min(...values.map((item) => item.raw));
  return values.map((item) => ({
    name: item.name,
    value: Number(Math.max(0, item.raw - minValue).toFixed(2)),
  }));
}

function pct(value?: number | null) {
  if (typeof value !== 'number' || Number.isNaN(value)) return 0;
  return Math.max(0, Math.min(100, value * 100));
}

function barVar(value?: number | null) {
  return { '--bar-width': `${pct(value)}%` } as CSSProperties;
}

const entityOptions = [
  { value: 'category', label: '品类' },
  { value: 'brand', label: '品牌' },
  { value: 'product', label: '商品' },
];

const modelOptions = [
  { value: 'time_decay', label: '时间衰减', hint: '越接近购买越重要' },
  { value: 'linear', label: '线性归因', hint: '每个触点平均分摊' },
  { value: 'last_touch', label: '末次触点', hint: '购买前最后一步' },
  { value: 'first_touch', label: '首次触点', hint: '首次发现来源' },
];

export function AttributionPage() {
  const [entityType, setEntityType] = useState('category');
  const [model, setModel] = useState('time_decay');
  const summary = useAttributionSummary();
  const models = useAttributionModels();
  const entities = useAttributionEntities({ entity_type: entityType, model, limit: 80 });
  const paths = useAttributionPaths(50);
  const assists = useAttributionAssists({ entity_type: entityType, limit: 80 });
  const quality = useAttributionQuality();
  const hasError = summary.isError || models.isError || entities.isError || paths.isError || assists.isError || quality.isError;
  const topEntity = entities.data?.[0];
  const topAssist = assists.data?.[0];
  const topPath = paths.data?.[0];
  const selectedRevenue = modelRevenue(topEntity, model);
  const modelChart = useMemo(() => barOption(modelRows(topEntity), '相对最低模型差额', '#39d0c8'), [topEntity]);
  const warning = summary.data?.warnings?.length
    ? `归因质量需要复核：${summary.data.warnings.map(fieldLabel).join('、')}`
    : null;

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">营收归因与辅助转化</span>
        <h1>营收归因与辅助转化洞察</h1>
        <p>基于同一会话内购买之前的浏览、加购和移出购物车触点，比较多种归因模型并识别辅助转化机会。</p>
      </section>

      {hasError ? <div className="error-banner">营收归因缓存尚未完整生成，请先运行 Spark 刷新任务。</div> : null}
      {warning ? <div className="error-banner">{warning}</div> : null}

      <section className="attribution-cockpit">
        <article className="attribution-hero-card">
          <div className="attribution-card-head">
            <span className={`status-pill tone-${statusTone(summary.data?.quality_status)}`}>
              {statusLabel(summary.data?.quality_status)}
            </span>
            <BadgeDollarSign size={20} />
          </div>
          <span className="mini-label">营收归因契约 v1</span>
          <h2>哪些触点真的帮成交？</h2>
          <div className="attribution-big-number">{money(summary.data?.assisted_revenue)}</div>
          <div className="attribution-flow">
            <span><MousePointerClick size={16} />浏览</span>
            <ArrowRight size={16} />
            <span><ShoppingCart size={16} />加购</span>
            <ArrowRight size={16} />
            <span><BadgeDollarSign size={16} />购买</span>
          </div>
          <p>{summary.data?.actual_input_path ?? '等待真实 HDFS 输入快照'}</p>
        </article>

        <article className="attribution-lens-card">
          <div className="attribution-card-head">
            <div>
              <span className="mini-label">当前镜头</span>
              <h2>{entityLabel(entityType)} · {modelLabel(model)}</h2>
            </div>
            <Sparkles size={20} />
          </div>
          <div className="attribution-focus-object">
            <span>{topEntity ? displayValue(topEntity.entity_label) : '待生成对象'}</span>
            <strong>{money(selectedRevenue)}</strong>
          </div>
          <div className="signal-stack">
            <div>
              <span>可归因覆盖</span>
              <i style={barVar(summary.data?.attribution_coverage_rate)}><b /></i>
              <strong>{percent(summary.data?.attribution_coverage_rate)}</strong>
            </div>
            <div>
              <span>多触点购买</span>
              <i style={barVar(summary.data?.multi_touch_purchase_rate)}><b /></i>
              <strong>{percent(summary.data?.multi_touch_purchase_rate)}</strong>
            </div>
            <div>
              <span>有效价格</span>
              <i style={barVar(quality.data?.valid_purchase_price_rate)}><b /></i>
              <strong>{percent(quality.data?.valid_purchase_price_rate)}</strong>
            </div>
          </div>
        </article>
      </section>

      <section className="visual-filter-board" aria-label="营收归因筛选">
        <div className="segment-block">
          <span>归因对象</span>
          <div className="segment-control" role="group" aria-label="归因对象快捷切换">
            {entityOptions.map((option) => (
              <button
                className={entityType === option.value ? 'is-active' : ''}
                type="button"
                key={option.value}
                onClick={() => setEntityType(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>
          <label className="compact-select-label">
            <span>归因对象</span>
            <select value={entityType} onChange={(event) => setEntityType(event.target.value)}>
              <option value="category">品类</option>
              <option value="brand">品牌</option>
              <option value="product">商品</option>
            </select>
          </label>
        </div>
        <div className="segment-block is-wide">
          <span>归因模型</span>
          <div className="segment-control attribution-model-control" role="group" aria-label="归因模型快捷切换">
            {modelOptions.map((option) => (
              <button
                className={model === option.value ? 'is-active' : ''}
                type="button"
                key={option.value}
                onClick={() => setModel(option.value)}
              >
                <strong>{option.label}</strong>
                <small>{option.hint}</small>
              </button>
            ))}
          </div>
          <label className="compact-select-label">
            <span>归因模型</span>
            <select value={model} onChange={(event) => setModel(event.target.value)}>
              <option value="time_decay">时间衰减</option>
              <option value="linear">线性归因</option>
              <option value="last_touch">末次触点</option>
              <option value="first_touch">首次触点</option>
            </select>
          </label>
        </div>
      </section>

      <section className="attribution-signal-grid">
        <article className="attribution-signal">
          <span>购买营收</span>
          <strong>{money(summary.data?.total_purchase_revenue)}</strong>
          <small>{number(summary.data?.purchase_rows)} 行购买记录</small>
        </article>
        <article className="attribution-signal">
          <span>首要机会</span>
          <strong>{topAssist ? displayValue(topAssist.entity_label) : '待生成'}</strong>
          <small>{topAssist ? label('action', topAssist.suggested_action) : '等待辅助转化对象'}</small>
        </article>
        <article className="attribution-signal">
          <span>高频路径</span>
          <strong>{topPath ? `${number(topPath.purchase_sessions)} 次购买` : '待生成'}</strong>
          <small>{topPath?.path_pattern ?? '等待路径证据'}</small>
        </article>
        <article className="attribution-signal">
          <span>平均触点</span>
          <strong>{score(summary.data?.avg_touchpoints_before_purchase)}</strong>
          <small>购买前 {score(summary.data?.avg_minutes_before_purchase)} 分钟</small>
        </article>
      </section>

      <section className="content-grid attribution-chart-grid">
        <ChartPanel
          title="归因模型差异"
          subtitle={`${topEntity ? displayValue(topEntity.entity_label) : entityLabel(entityType)}：四种模型相对最低归因值的差额`}
          option={modelChart}
        />
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>当前最强对象</h2>
              <p>按所选模型排序后的最高辅助转化实体。</p>
            </div>
            <Sparkles size={20} />
          </div>
          <dl>
            <dt>对象</dt>
            <dd>{topEntity ? displayValue(topEntity.entity_label) : '待生成'}</dd>
            <dt>{modelLabel(model)}</dt>
            <dd>{money(selectedRevenue)}</dd>
            <dt>辅助 / 直接</dt>
            <dd>{score(topEntity?.assist_to_direct_ratio)}</dd>
            <dt>置信度</dt>
            <dd>{percent(topEntity?.confidence)}</dd>
          </dl>
        </article>
      </section>

      <section className="forecast-main-grid">
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>质量门禁</h2>
              <p>覆盖率、购买样本、价格有效性和历史窗口共同决定是否可直接用于经营决策。</p>
            </div>
            <ShieldCheck size={20} />
          </div>
          <dl>
            <dt>购买会话</dt>
            <dd>{number(quality.data?.purchase_sessions)}</dd>
            <dt>覆盖率</dt>
            <dd>{percent(quality.data?.attribution_coverage_rate)}</dd>
            <dt>有效价格</dt>
            <dd>{percent(quality.data?.valid_purchase_price_rate)}</dd>
            <dt>历史天数</dt>
            <dd>{number(quality.data?.history_days)}</dd>
          </dl>
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>首要辅助机会</h2>
              <p>按辅助营收和置信度排序，给出可执行动作。</p>
            </div>
            <GitCompareArrows size={20} />
          </div>
          <dl>
            <dt>对象</dt>
            <dd>{topAssist ? displayValue(topAssist.entity_label) : '待生成'}</dd>
            <dt>动作</dt>
            <dd>{topAssist ? label('action', topAssist.suggested_action) : '待生成'}</dd>
            <dt>优先级</dt>
            <dd>{score(topAssist?.priority_score)}</dd>
            <dt>会话</dt>
            <dd>{number(topAssist?.assisted_purchase_sessions)}</dd>
          </dl>
        </article>
      </section>

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>归因实体排行</h2>
            <p>比较首次触点、末次触点、线性归因和时间衰减模型下的营收归因差异。</p>
          </div>
          <BadgeDollarSign size={20} />
        </div>
        <div className="table-scroll">
          <table aria-label="营收归因实体排行">
            <thead>
              <tr>
                <th>对象</th>
                <th>触点会话</th>
                <th>辅助购买</th>
                <th>首次触点</th>
                <th>末次触点</th>
                <th>线性归因</th>
                <th>时间衰减</th>
                <th>辅助 / 直接</th>
                <th>原因</th>
              </tr>
            </thead>
            <tbody>
              {(entities.data ?? []).map((row) => (
                <tr key={`${row.entity_type}:${row.entity_id}`}>
                  <td>
                    <strong>{displayValue(row.entity_label)}</strong>
                    <br />
                    <small>{entityLabel(row.entity_type)}</small>
                  </td>
                  <td>{number(row.touch_sessions)}</td>
                  <td>{number(row.assisted_purchase_sessions)}</td>
                  <td>{money(row.first_touch_revenue)}</td>
                  <td>{money(row.last_touch_revenue)}</td>
                  <td>{money(row.linear_assisted_revenue)}</td>
                  <td>{money(row.time_decay_assisted_revenue)}</td>
                  <td>{score(row.assist_to_direct_ratio)}</td>
                  <td>{listLabels('reason', row.reason_codes?.length ? row.reason_codes : ['multi_touch_driver'])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="content-grid">
        <article className="data-panel jobs-panel">
          <div className="panel-title">
            <div>
              <h2>辅助转化机会</h2>
              <p>面向推荐曝光、购物车路径和经营动作的优先队列。</p>
            </div>
            <Sparkles size={20} />
          </div>
          <div className="table-scroll">
            <table aria-label="辅助转化机会">
              <thead>
                <tr>
                  <th>对象</th>
                  <th>动作</th>
                  <th>优先级</th>
                  <th>置信度</th>
                  <th>辅助营收</th>
                </tr>
              </thead>
              <tbody>
                {(assists.data ?? []).slice(0, 12).map((row) => (
                  <tr key={`${row.entity_type}:${row.entity_id}:${row.suggested_action}`}>
                    <td>{displayValue(row.entity_label)}</td>
                    <td>{label('action', row.suggested_action)}</td>
                    <td>{score(row.priority_score)}</td>
                    <td>{percent(row.confidence)}</td>
                    <td>{money(row.time_decay_assisted_revenue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="data-panel jobs-panel">
          <div className="panel-title">
            <div>
              <h2>高频购买路径</h2>
              <p>按购买收入排序的会话路径模式，辅助解释归因结果。</p>
            </div>
            <Route size={20} />
          </div>
          <div className="table-scroll">
            <table aria-label="归因购买路径">
              <thead>
                <tr>
                  <th>路径</th>
                  <th>会话</th>
                  <th>购买</th>
                  <th>转化</th>
                  <th>营收</th>
                </tr>
              </thead>
              <tbody>
                {(paths.data ?? []).slice(0, 12).map((row) => (
                  <tr key={row.path_pattern}>
                    <td>{row.path_pattern}</td>
                    <td>{number(row.sessions)}</td>
                    <td>{number(row.purchase_sessions)}</td>
                    <td>{percent(row.conversion_rate)}</td>
                    <td>{money(row.revenue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      </section>
    </>
  );
}
