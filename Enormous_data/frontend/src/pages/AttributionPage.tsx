import { BadgeDollarSign, GitCompareArrows, Route, ShieldCheck, Sparkles } from 'lucide-react';
import { useMemo, useState } from 'react';
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
import type { AttributionModel } from '../types/api';

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

function modelRows(rows: AttributionModel[]) {
  return rows.map((row) => ({
    name: entityLabel(row.entity_type),
    value: Number(row.time_decay_assisted_revenue.toFixed(2)),
  }));
}

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
  const modelChart = useMemo(() => barOption(modelRows(models.data ?? []), '时间衰减辅助营收', '#39d0c8'), [models.data]);
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

      <section className="ops-command-band">
        <div>
          <span className={`status-pill tone-${statusTone(summary.data?.quality_status)}`}>
            {statusLabel(summary.data?.quality_status)}
          </span>
          <h2>营收归因契约 v1</h2>
          <p>{summary.data?.actual_input_path ?? '等待真实 HDFS 输入快照'}</p>
        </div>
        <BadgeDollarSign size={22} />
      </section>

      <section className="metrics-strip">
        <article className="metric-card tone-success">
          <span>可归因覆盖率</span>
          <strong>{percent(summary.data?.attribution_coverage_rate)}</strong>
          <small>{number(summary.data?.attributable_sessions)} 个可归因会话</small>
        </article>
        <article className="metric-card">
          <span>购买营收</span>
          <strong>{money(summary.data?.total_purchase_revenue)}</strong>
          <small>{number(summary.data?.purchase_rows)} 行购买记录</small>
        </article>
        <article className="metric-card tone-warning">
          <span>辅助营收</span>
          <strong>{money(summary.data?.assisted_revenue)}</strong>
          <small>{percent(summary.data?.multi_touch_purchase_rate)} 多触点购买</small>
        </article>
        <article className="metric-card">
          <span>平均触点</span>
          <strong>{score(summary.data?.avg_touchpoints_before_purchase)}</strong>
          <small>购买前 {score(summary.data?.avg_minutes_before_purchase)} 分钟</small>
        </article>
      </section>

      <section className="toolbar forecast-toolbar" aria-label="营收归因筛选">
        <label>
          <span>归因对象</span>
          <select value={entityType} onChange={(event) => setEntityType(event.target.value)}>
            <option value="category">品类</option>
            <option value="brand">品牌</option>
            <option value="product">商品</option>
          </select>
        </label>
        <label>
          <span>归因模型</span>
          <select value={model} onChange={(event) => setModel(event.target.value)}>
            <option value="time_decay">时间衰减</option>
            <option value="linear">线性归因</option>
            <option value="last_touch">末次触点</option>
            <option value="first_touch">首次触点</option>
          </select>
        </label>
      </section>

      <section className="content-grid">
        <ChartPanel title="归因模型对比" subtitle="按对象类型汇总时间衰减辅助营收" option={modelChart} />
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
            <dd>
              {money(
                model === 'first_touch'
                  ? topEntity?.first_touch_revenue
                  : model === 'last_touch'
                    ? topEntity?.last_touch_revenue
                    : model === 'linear'
                      ? topEntity?.linear_assisted_revenue
                      : topEntity?.time_decay_assisted_revenue,
              )}
            </dd>
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
