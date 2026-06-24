import {
  ArrowRight,
  BadgeDollarSign,
  BellRing,
  Boxes,
  CheckCircle2,
  Filter,
  PackageSearch,
  RotateCcw,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
  Target,
  TrendingDown,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import {
  useCartCategories,
  useCartProducts,
  useCartQuality,
  useCartRecoveryQueue,
  useCartSummary,
} from '../api/hooks';
import { ChartPanel } from '../components/ChartPanel';
import { displayValue, label, listLabels, statusLabel } from '../i18n/displayText';
import { donutOption, horizontalBarOption } from '../lib/chartOptions';
import type { CartCategorySegment, CartProductSegment, CartRecoveryQueueItem, NamedValue } from '../types/api';

function money(value?: number | null) {
  return typeof value === 'number' ? `¥${value.toLocaleString()}` : '待生成';
}

function compactMoney(value?: number | null) {
  if (typeof value !== 'number') return '待生成';
  if (value >= 10000) return `¥${(value / 10000).toFixed(1)}万`;
  return money(value);
}

function number(value?: number | null) {
  return typeof value === 'number' ? value.toLocaleString() : '待生成';
}

function percent(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '待生成';
}

function score(value?: number | null) {
  return typeof value === 'number' ? value.toFixed(2) : '待生成';
}

function categoryOptions(rows: CartCategorySegment[]) {
  return Array.from(new Set(rows.map((row) => row.category_level1))).sort();
}

const actionLabels: Record<string, string> = {
  category_merchandising_review: '品类陈列复核',
  category_recovery_campaign: '品类召回活动',
  category_watch: '品类观察',
  recovery_offer_or_reminder: '优惠或提醒召回',
  watch_cart_followup: '观察跟进',
};

function recoveryActionOptions(rows: Array<{ recovery_action: string }>) {
  return Array.from(new Set(rows.map((row) => row.recovery_action))).sort();
}

function shortLabel(value: string) {
  return value.length > 18 ? `${value.slice(0, 16)}...` : value;
}

function sumBy<T>(rows: T[], keyFn: (row: T) => string, valueFn: (row: T) => number): NamedValue[] {
  const totals = new Map<string, number>();
  rows.forEach((row) => {
    const key = keyFn(row);
    totals.set(key, (totals.get(key) ?? 0) + valueFn(row));
  });
  return Array.from(totals.entries())
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
}

function queueValueRows(rows: CartRecoveryQueueItem[]): NamedValue[] {
  return rows
    .slice(0, 10)
    .map((row) => ({ name: shortLabel(displayValue(row.entity_label)), value: Math.round(row.abandoned_value) }));
}

function productValueRows(rows: CartProductSegment[]): NamedValue[] {
  return rows
    .slice(0, 10)
    .map((row) => ({ name: shortLabel(`${displayValue(row.brand)} ${row.product_id}`), value: Math.round(row.abandoned_value) }));
}

function warningCopy(warnings?: string[]) {
  if (!warnings?.length) return null;
  if (warnings.includes('history_days')) return '当前输入窗口不足，购物车流失和召回优先级只能用于方向性诊断。';
  return `购物车质量门禁需要复核：${warnings.join(', ')}`;
}

function statusTone(status?: string) {
  return status === 'passed' ? 'success' : status === 'needs_review' ? 'queued' : 'failed';
}

function barWidth(value: number, max: number) {
  if (value <= 0 || max <= 0) return '0%';
  return `${Math.max(8, Math.min(100, (value / max) * 100))}%`;
}

function actionIcon(action: string) {
  if (action.includes('offer')) return <BadgeDollarSign size={18} />;
  if (action.includes('campaign')) return <BellRing size={18} />;
  if (action.includes('category')) return <Boxes size={18} />;
  if (action.includes('watch')) return <Target size={18} />;
  return <Sparkles size={18} />;
}

function categoryVisualRows(rows: CartCategorySegment[]) {
  const maxValue = Math.max(...rows.map((row) => row.abandoned_value), 1);
  return rows.slice(0, 8).map((row) => ({
    ...row,
    width: barWidth(row.abandoned_value, maxValue),
  }));
}

export function CartRecoveryPage() {
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedAction, setSelectedAction] = useState('');
  const summary = useCartSummary();
  const categories = useCartCategories(80);
  const products = useCartProducts({ category: selectedCategory || undefined, limit: 80 });
  const allQueue = useCartRecoveryQueue({ confidence: 0.1, limit: 200 });
  const queue = useCartRecoveryQueue({ action: selectedAction || undefined, confidence: 0.1, limit: 80 });
  const quality = useCartQuality();
  const hasError = summary.isError || categories.isError || products.isError || queue.isError || quality.isError;
  const options = useMemo(() => categoryOptions(categories.data ?? []), [categories.data]);
  const actionOptions = useMemo(() => recoveryActionOptions(allQueue.data ?? []), [allQueue.data]);
  const warning = warningCopy(summary.data?.warnings ?? quality.data?.warnings);
  const queueRows = useMemo(() => {
    const rows = queue.data ?? [];
    if (!selectedCategory) return rows;
    return rows.filter(
      (row) =>
        row.entity_id === selectedCategory ||
        row.entity_label.includes(selectedCategory) ||
        row.reason_codes.includes(`${selectedCategory}_cart_abandonment`),
    );
  }, [queue.data, selectedCategory]);
  const productRows = products.data ?? [];
  const categoryRows = categories.data ?? [];
  const visibleCategories = useMemo(() => categoryVisualRows(categoryRows), [categoryRows]);
  const actionMix = useMemo(
    () => sumBy(allQueue.data ?? [], (row) => actionLabels[row.recovery_action] ?? row.recovery_action, () => 1),
    [allQueue.data],
  );
  const queueValue = useMemo(() => queueValueRows(queueRows), [queueRows]);
  const productValue = useMemo(() => productValueRows(productRows), [productRows]);
  const categoryValue = useMemo(
    () => categoryRows.slice(0, 10).map((row) => ({ name: displayValue(row.category_level1), value: Math.round(row.abandoned_value) })),
    [categoryRows],
  );
  const topQueue = queueRows[0];
  const topProduct = productRows[0];
  const topCategory = categoryRows[0];
  const filteredLabel = selectedCategory ? displayValue(selectedCategory) : '全部品类';
  const filteredAction = selectedAction ? actionLabels[selectedAction] ?? selectedAction : '全部动作';
  const publishable = summary.data?.quality_status === 'passed' && !(summary.data?.warnings?.length ?? 0);

  useEffect(() => {
    if (selectedAction && actionOptions.length && !actionOptions.includes(selectedAction)) {
      setSelectedAction('');
    }
  }, [actionOptions, selectedAction]);

  return (
    <>
      <section className="page-heading cart-page-heading">
        <span className="eyebrow">购物车流失与召回智能</span>
        <h1>购物车流失与召回机会</h1>
        <p>看清谁在流失、值多少钱、该用什么动作召回。</p>
      </section>

      {hasError ? <div className="error-banner">购物车流失缓存尚未完整生成，请先运行 Spark 刷新任务。</div> : null}
      {warning ? <div className="error-banner">{warning}</div> : null}

      <section className="cart-control-surface">
        <div className="cart-command-center">
          <article className={`cart-decision-card tone-${statusTone(summary.data?.quality_status)}`}>
            <div className="cart-decision-copy">
              <span className={`status-pill tone-${statusTone(summary.data?.quality_status)}`}>
                {statusLabel(summary.data?.quality_status)}
              </span>
              <small className="cart-contract-label">购物车召回契约 v1</small>
              <h2>{publishable ? '当前快照可发布' : '当前快照需观察'}</h2>
              <p>{publishable ? '质量门禁允许进入前端召回策略。' : '先作为运营诊断，不直接承诺增量效果。'}</p>
            </div>
            <strong>{compactMoney(summary.data?.abandoned_value)}</strong>
          </article>

          <article className="cart-funnel-card" aria-label="购物车召回价值漏斗">
            <div className="cart-funnel-step">
              <ShoppingCart size={18} />
              <span>加购</span>
              <strong>{number(summary.data?.cart_product_sessions)}</strong>
            </div>
            <ArrowRight size={18} />
            <div className="cart-funnel-step is-warning">
              <TrendingDown size={18} />
              <span>流失</span>
              <strong>{number(summary.data?.abandoned_sessions)}</strong>
            </div>
            <ArrowRight size={18} />
            <div className="cart-funnel-step is-success">
              <CheckCircle2 size={18} />
              <span>恢复</span>
              <strong>{percent(summary.data?.recovery_rate)}</strong>
            </div>
          </article>
        </div>

        <div className="cart-kpi-grid">
          <article className="cart-kpi-card is-hot">
            <span>可召回价值池</span>
            <strong title={money(summary.data?.abandoned_value)}>{compactMoney(summary.data?.abandoned_value)}</strong>
            <small>{number(summary.data?.abandoned_sessions)} 个流失会话</small>
          </article>
          <article className="cart-kpi-card">
            <span>购物车会话</span>
            <strong>{number(summary.data?.cart_product_sessions)}</strong>
            <small>{money(summary.data?.cart_value)} 加购金额</small>
          </article>
          <article className="cart-kpi-card is-good">
            <span>已恢复</span>
            <strong>{percent(summary.data?.recovery_rate)}</strong>
            <small>{number(summary.data?.recovered_sessions)} 个会话</small>
          </article>
          <article className="cart-kpi-card">
            <span>显式移除</span>
            <strong>{percent(summary.data?.remove_rate)}</strong>
            <small>{number(summary.data?.explicit_remove_sessions)} 个移出信号</small>
          </article>
        </div>

        <div className="cart-filter-board" aria-label="购物车召回筛选">
          <div className="cart-filter-head">
            <div>
              <Filter size={18} />
              <strong>{filteredLabel}</strong>
              <span>{filteredAction}</span>
            </div>
            <small>{number(queueRows.length)} 条当前机会</small>
          </div>
          <div className="cart-chip-row" aria-label="品类快捷筛选">
            <button className={selectedCategory ? 'cart-chip' : 'cart-chip is-active'} type="button" onClick={() => setSelectedCategory('')}>
              全部品类
            </button>
            {options.slice(0, 8).map((category) => (
              <button
                className={selectedCategory === category ? 'cart-chip is-active' : 'cart-chip'}
                key={category}
                type="button"
                onClick={() => setSelectedCategory(category)}
              >
                {displayValue(category)}
              </button>
            ))}
          </div>
          <div className="cart-chip-row" aria-label="召回动作快捷筛选">
            <button className={selectedAction ? 'cart-chip' : 'cart-chip is-active'} type="button" onClick={() => setSelectedAction('')}>
              全部动作
            </button>
            {actionOptions.map((action) => (
              <button
                className={selectedAction === action ? 'cart-chip is-active' : 'cart-chip'}
                key={action}
                type="button"
                onClick={() => setSelectedAction(action)}
              >
                {actionIcon(action)}
                {actionLabels[action] ?? action}
              </button>
            ))}
          </div>
          <div className="cart-native-filters">
            <label>
              <span>品类</span>
              <select value={selectedCategory} onChange={(event) => setSelectedCategory(event.target.value)}>
                <option value="">全部</option>
                {options.map((category) => (
                  <option key={category} value={category}>
                    {displayValue(category)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>召回动作</span>
              <select value={selectedAction} onChange={(event) => setSelectedAction(event.target.value)}>
                <option value="">全部</option>
                {actionOptions.map((action) => (
                  <option key={action} value={action}>
                    {actionLabels[action] ?? action}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
      </section>

      <section className="cart-visual-grid">
        <article className="cart-opportunity-panel">
          <div className="panel-title">
            <div>
              <h2>召回机会地图</h2>
              <p>圆点越大，流失价值越高。</p>
            </div>
            <PackageSearch size={20} />
          </div>
          <div className="cart-category-cloud">
            {visibleCategories.map((row) => (
              <button
                className={selectedCategory === row.category_level1 ? 'cart-category-bubble is-active' : 'cart-category-bubble'}
                key={row.category_level1}
                type="button"
                onClick={() => setSelectedCategory(row.category_level1)}
              >
                <span>{displayValue(row.category_level1)}</span>
                <strong>{compactMoney(row.abandoned_value)}</strong>
                <i style={{ width: row.width }} />
              </button>
            ))}
          </div>
        </article>

        <article className="cart-top-opportunity">
          <div className="panel-title">
            <div>
              <h2>当前首要机会</h2>
              <p>随筛选实时变化。</p>
            </div>
            <Target size={20} />
          </div>
          {topQueue ? (
            <div className="cart-priority-card">
              <span>{label('entityType', topQueue.entity_type)}</span>
              <strong>{displayValue(topQueue.entity_label)}</strong>
              <div className="cart-priority-metrics">
                <small>流失 {money(topQueue.abandoned_value)}</small>
                <small>置信 {percent(topQueue.confidence)}</small>
                <small>得分 {score(topQueue.priority_score)}</small>
              </div>
              <div className="cart-reason-row">
                {topQueue.reason_codes.slice(0, 3).map((reason) => (
                  <em key={reason}>{actionLabels[reason] ?? label('reason', reason)}</em>
                ))}
              </div>
            </div>
          ) : (
            <div className="empty-panel">当前筛选下没有机会。</div>
          )}
        </article>
      </section>

      <section className="forecast-main-grid cart-chart-grid">
        <ChartPanel
          title="召回动作结构"
          subtitle="动作构成"
          option={donutOption(actionMix, '召回动作')}
          summary={actionMix[0] ? `${actionMix[0].name} ${number(actionMix[0].value)} 条。` : '等待召回动作数据。'}
        />
        <ChartPanel
          title="流失价值前列机会"
          subtitle="最高价值对象"
          option={horizontalBarOption(queueValue, '流失价值', '#f59e0b')}
          summary={topQueue ? `${displayValue(topQueue.entity_label)}：${money(topQueue.abandoned_value)}` : '等待召回机会队列。'}
        />
      </section>

      <section className="content-grid visual-first-grid cart-chart-grid">
        <ChartPanel
          title="商品流失优先级"
          subtitle="商品层"
          option={horizontalBarOption(productValue, '流失价值', '#65b8ff')}
          summary={topProduct ? `${displayValue(topProduct.brand)} ${topProduct.product_id}` : '等待商品召回数据。'}
        />
        <ChartPanel
          title="品类流失结构"
          subtitle="品类层"
          option={horizontalBarOption(categoryValue, '流失价值', '#56d27b')}
          summary={topCategory ? `${displayValue(topCategory.category_level1)}：${money(topCategory.abandoned_value)}` : '等待品类召回数据。'}
        />
      </section>

      <section className="cart-gate-grid">
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>质量门禁</h2>
              <p>能不能用。</p>
            </div>
            <ShieldCheck size={20} />
          </div>
          <dl>
            <dt>加购事件</dt>
            <dd>{number(quality.data?.cart_event_rows)}</dd>
            <dt>移出事件</dt>
            <dd>{number(quality.data?.remove_event_rows)}</dd>
            <dt>历史天数</dt>
            <dd>{number(quality.data?.history_days)}</dd>
            <dt>最小会话数</dt>
            <dd>{number(quality.data?.min_cart_sessions)}</dd>
          </dl>
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>召回队列摘要</h2>
              <p>召回池规模。</p>
            </div>
            <RotateCcw size={20} />
          </div>
          <dl>
            <dt>队列条目</dt>
            <dd>{number(summary.data?.queue_count)}</dd>
            <dt>商品数</dt>
            <dd>{number(summary.data?.product_count)}</dd>
            <dt>品类数</dt>
            <dd>{number(summary.data?.category_count)}</dd>
            <dt>放弃率</dt>
            <dd>{percent(summary.data?.abandonment_rate)}</dd>
          </dl>
        </article>
      </section>

      <details className="detail-table-disclosure cart-disclosure">
        <summary>查看召回机会队列明细</summary>
        <section className="data-panel jobs-panel">
          <div className="panel-title">
            <div>
              <h2>召回机会队列</h2>
              <p>商品和品类级机会，结合流失价值、放弃率和置信度排序。</p>
            </div>
            <RotateCcw size={20} />
          </div>
          <div className="table-scroll">
            <table aria-label="购物车召回机会队列">
              <thead>
                <tr>
                  <th>对象</th>
                  <th>动作</th>
                  <th>优先级</th>
                  <th>置信度</th>
                  <th>流失价值</th>
                  <th>放弃率</th>
                  <th>移出率</th>
                  <th>原因</th>
                </tr>
              </thead>
              <tbody>
                {queueRows.map((row) => (
                  <tr key={`${row.entity_type}:${row.entity_id}:${row.recovery_action}`}>
                    <td>
                      <strong>{displayValue(row.entity_label)}</strong>
                      <br />
                      <small>{label('entityType', row.entity_type)}</small>
                    </td>
                    <td>{label('action', row.recovery_action)}</td>
                    <td>{score(row.priority_score)}</td>
                    <td>{percent(row.confidence)}</td>
                    <td>{money(row.abandoned_value)}</td>
                    <td>{percent(row.abandonment_rate)}</td>
                    <td>{percent(row.remove_rate)}</td>
                    <td>{listLabels('reason', row.reason_codes)}</td>
                  </tr>
                ))}
                {queueRows.length === 0 ? (
                  <tr>
                    <td colSpan={8}>当前筛选条件下没有召回机会，请切换为全部或选择已有动作。</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      </details>

      <details className="detail-table-disclosure cart-disclosure">
        <summary>查看商品流失明细</summary>
        <section className="data-panel jobs-panel">
          <div className="panel-title">
            <div>
              <h2>商品流失优先级</h2>
              <p>按商品聚合购物车商品会话、恢复数、显式移除数和流失价值。</p>
            </div>
            <ShoppingCart size={20} />
          </div>
          <div className="table-scroll">
            <table aria-label="商品购物车流失优先级">
              <thead>
                <tr>
                  <th>商品</th>
                  <th>品牌</th>
                  <th>品类</th>
                  <th>购物车会话</th>
                  <th>已恢复</th>
                  <th>已流失</th>
                  <th>流失价值</th>
                  <th>优先级</th>
                </tr>
              </thead>
              <tbody>
                {productRows.map((row) => (
                  <tr key={row.product_id}>
                    <td>{row.product_id}</td>
                    <td>{displayValue(row.brand)}</td>
                    <td>{displayValue(row.category_level1)}</td>
                    <td>{number(row.cart_product_sessions)}</td>
                    <td>{number(row.recovered_sessions)}</td>
                    <td>{number(row.abandoned_sessions)}</td>
                    <td>{money(row.abandoned_value)}</td>
                    <td>{score(row.priority_score)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </details>

      <details className="detail-table-disclosure cart-disclosure">
        <summary>查看品类流失明细</summary>
        <section className="data-panel jobs-panel">
          <div className="panel-title">
            <div>
              <h2>品类流失结构</h2>
              <p>品类层面观察购物车放弃、恢复和移出购物车信号。</p>
            </div>
            <ShoppingCart size={20} />
          </div>
          <div className="table-scroll">
            <table aria-label="品类购物车流失结构">
              <thead>
                <tr>
                  <th>品类</th>
                  <th>购物车会话</th>
                  <th>恢复率</th>
                  <th>放弃率</th>
                  <th>移出率</th>
                  <th>流失价值</th>
                </tr>
              </thead>
              <tbody>
                {categoryRows.map((row) => (
                  <tr key={row.category_level1}>
                    <td>{displayValue(row.category_level1)}</td>
                    <td>{number(row.cart_product_sessions)}</td>
                    <td>{percent(row.recovery_rate)}</td>
                    <td>{percent(row.abandonment_rate)}</td>
                    <td>{percent(row.remove_rate)}</td>
                    <td>{money(row.abandoned_value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </details>
    </>
  );
}
