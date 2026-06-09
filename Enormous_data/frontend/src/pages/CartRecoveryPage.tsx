import { RotateCcw, ShieldCheck, ShoppingCart } from 'lucide-react';
import { useMemo, useState } from 'react';
import {
  useCartCategories,
  useCartProducts,
  useCartQuality,
  useCartRecoveryQueue,
  useCartSummary,
} from '../api/hooks';
import type { CartCategorySegment } from '../types/api';

function money(value?: number | null) {
  return typeof value === 'number' ? `¥${value.toLocaleString()}` : 'pending';
}

function number(value?: number | null) {
  return typeof value === 'number' ? value.toLocaleString() : 'pending';
}

function percent(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : 'pending';
}

function score(value?: number | null) {
  return typeof value === 'number' ? value.toFixed(2) : 'pending';
}

function categoryOptions(rows: CartCategorySegment[]) {
  return Array.from(new Set(rows.map((row) => row.category_level1))).sort();
}

function warningCopy(warnings?: string[]) {
  if (!warnings?.length) return null;
  if (warnings.includes('history_days')) return '当前输入窗口不足，购物车流失和召回优先级只能用于方向性诊断。';
  return `购物车质量门禁需要复核：${warnings.join(', ')}`;
}

function statusTone(status?: string) {
  return status === 'passed' ? 'success' : status === 'needs_review' ? 'queued' : 'failed';
}

export function CartRecoveryPage() {
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedAction, setSelectedAction] = useState('');
  const summary = useCartSummary();
  const categories = useCartCategories(80);
  const products = useCartProducts({ category: selectedCategory || undefined, limit: 80 });
  const queue = useCartRecoveryQueue({ action: selectedAction || undefined, confidence: 0.1, limit: 80 });
  const quality = useCartQuality();
  const hasError = summary.isError || categories.isError || products.isError || queue.isError || quality.isError;
  const options = useMemo(() => categoryOptions(categories.data ?? []), [categories.data]);
  const warning = warningCopy(summary.data?.warnings ?? quality.data?.warnings);

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">Cart abandonment & recovery intelligence</span>
        <h1>购物车流失与召回机会</h1>
        <p>基于真实 cart、remove_from_cart 和 purchase 行为识别可召回价值池，按商品和品类沉淀运营优先级。</p>
      </section>

      {hasError ? <div className="error-banner">购物车流失缓存尚未完整生成，请先运行 Spark 刷新任务。</div> : null}
      {warning ? <div className="error-banner">{warning}</div> : null}

      <section className="ops-command-band">
        <div>
          <span className={`status-pill tone-${statusTone(summary.data?.quality_status)}`}>
            {summary.data?.quality_status ?? 'pending'}
          </span>
          <h2>{summary.data?.contract_version ?? 'cart-recovery-intelligence/v1'}</h2>
          <p>{summary.data?.actual_input_path ?? '等待真实 HDFS 输入快照'}</p>
        </div>
        <ShoppingCart size={22} />
      </section>

      <section className="metrics-strip">
        <article className="metric-card tone-warning">
          <span>可召回价值池</span>
          <strong>{money(summary.data?.abandoned_value)}</strong>
          <small>{number(summary.data?.abandoned_sessions)} abandoned sessions</small>
        </article>
        <article className="metric-card">
          <span>购物车会话</span>
          <strong>{number(summary.data?.cart_product_sessions)}</strong>
          <small>{money(summary.data?.cart_value)} cart value</small>
        </article>
        <article className="metric-card tone-success">
          <span>已恢复</span>
          <strong>{percent(summary.data?.recovery_rate)}</strong>
          <small>{number(summary.data?.recovered_sessions)} recovered</small>
        </article>
        <article className="metric-card">
          <span>显式移除</span>
          <strong>{percent(summary.data?.remove_rate)}</strong>
          <small>{number(summary.data?.explicit_remove_sessions)} remove signals</small>
        </article>
      </section>

      <section className="toolbar forecast-toolbar" aria-label="购物车召回筛选">
        <label>
          <span>品类</span>
          <select value={selectedCategory} onChange={(event) => setSelectedCategory(event.target.value)}>
            <option value="">全部</option>
            {options.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span>召回动作</span>
          <select value={selectedAction} onChange={(event) => setSelectedAction(event.target.value)}>
            <option value="">全部</option>
            <option value="recovery_offer_or_reminder">优惠或提醒</option>
            <option value="inspect_product_friction">商品摩擦排查</option>
            <option value="category_merchandising_review">品类货架复核</option>
            <option value="category_recovery_campaign">品类召回活动</option>
            <option value="watch_cart_followup">观察跟进</option>
          </select>
        </label>
      </section>

      <section className="forecast-main-grid">
        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>质量门禁</h2>
              <p>校验购物车样本量、remove 信号、历史窗口和召回队列可信度。</p>
            </div>
            <ShieldCheck size={20} />
          </div>
          <dl>
            <dt>Cart events</dt>
            <dd>{number(quality.data?.cart_event_rows)}</dd>
            <dt>Remove events</dt>
            <dd>{number(quality.data?.remove_event_rows)}</dd>
            <dt>History days</dt>
            <dd>{number(quality.data?.history_days)}</dd>
            <dt>Min sessions</dt>
            <dd>{number(quality.data?.min_cart_sessions)}</dd>
          </dl>
        </article>

        <article className="data-panel ops-card">
          <div className="panel-title">
            <div>
              <h2>召回队列摘要</h2>
              <p>按优先级得分排序，聚焦高价值流失池。</p>
            </div>
            <RotateCcw size={20} />
          </div>
          <dl>
            <dt>Queue items</dt>
            <dd>{number(summary.data?.queue_count)}</dd>
            <dt>Products</dt>
            <dd>{number(summary.data?.product_count)}</dd>
            <dt>Categories</dt>
            <dd>{number(summary.data?.category_count)}</dd>
            <dt>Abandonment</dt>
            <dd>{percent(summary.data?.abandonment_rate)}</dd>
          </dl>
        </article>
      </section>

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
                <th>Remove</th>
                <th>原因</th>
              </tr>
            </thead>
            <tbody>
              {(queue.data ?? []).map((row) => (
                <tr key={`${row.entity_type}:${row.entity_id}:${row.recovery_action}`}>
                  <td>
                    <strong>{row.entity_label}</strong>
                    <br />
                    <small>{row.entity_type}</small>
                  </td>
                  <td>{row.recovery_action}</td>
                  <td>{score(row.priority_score)}</td>
                  <td>{percent(row.confidence)}</td>
                  <td>{money(row.abandoned_value)}</td>
                  <td>{percent(row.abandonment_rate)}</td>
                  <td>{percent(row.remove_rate)}</td>
                  <td>{row.reason_codes.join(', ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

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
                <th>Cart sessions</th>
                <th>Recovered</th>
                <th>Abandoned</th>
                <th>Abandoned value</th>
                <th>Priority</th>
              </tr>
            </thead>
            <tbody>
              {(products.data ?? []).map((row) => (
                <tr key={row.product_id}>
                  <td>{row.product_id}</td>
                  <td>{row.brand}</td>
                  <td>{row.category_level1}</td>
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

      <section className="data-panel jobs-panel">
        <div className="panel-title">
          <div>
            <h2>品类流失结构</h2>
            <p>品类层面观察购物车放弃、恢复和 remove_from_cart 信号。</p>
          </div>
          <ShoppingCart size={20} />
        </div>
        <div className="table-scroll">
          <table aria-label="品类购物车流失结构">
            <thead>
              <tr>
                <th>品类</th>
                <th>Cart sessions</th>
                <th>Recovered</th>
                <th>Abandoned</th>
                <th>Remove rate</th>
                <th>Abandoned value</th>
              </tr>
            </thead>
            <tbody>
              {(categories.data ?? []).map((row) => (
                <tr key={row.category_level1}>
                  <td>{row.category_level1}</td>
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
    </>
  );
}
