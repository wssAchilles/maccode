import { Eye, HeartPulse, ListFilter, Target, UsersRound } from 'lucide-react';
import { useMemo, useState } from 'react';
import {
  useLifecycleCategoryAffinity,
  useLifecycleRiskQueue,
  useLifecycleRules,
  useLifecycleSegments,
  useLifecycleSummary,
} from '../api/hooks';
import { algorithmCopy, displayValue, label } from '../i18n/displayText';
import type { LifecycleCategoryAffinity, LifecycleSegment, LifecycleSummary, LifecycleUser } from '../types/api';

function number(value?: number | null) {
  return typeof value === 'number' ? value.toLocaleString() : '待生成';
}

function money(value?: number | null) {
  return typeof value === 'number' ? `¥${value.toLocaleString()}` : '待生成';
}

function percent(value?: number | null) {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '待生成';
}

function segmentTone(segment?: string) {
  if (segment === 'champion' || segment === 'high_value' || segment === 'loyal') return 'success';
  if (segment === 'cart_intent' || segment === 'at_risk_focus') return 'warning';
  if (segment === 'unknown') return 'danger';
  return 'queued';
}

type LifecycleView = 'matrix' | 'rules' | 'queue';

type LifecycleCard = {
  key: string;
  label: string;
  kind: '生命周期' | '风险队列';
  users: number;
  revenue: number;
  purchases: number;
  avgRecencyDays: number | null;
  share: number;
  action: string;
  rule: string;
  evidence: string;
};

const lifecycleCatalog: Array<Omit<LifecycleCard, 'users' | 'revenue' | 'purchases' | 'avgRecencyDays' | 'share'>> = [
  {
    key: 'champion',
    label: '冠军用户',
    kind: '生命周期',
    action: '保护体验',
    rule: '高收入且多次购买日，代表当前最核心的复购价值人群。',
    evidence: '收入和购买频次同时高。',
  },
  {
    key: 'high_value',
    label: '高价值',
    kind: '生命周期',
    action: '专属权益',
    rule: '购买用户收入达到高价值阈值。',
    evidence: '收入贡献高，但频次可能未达到冠军用户。',
  },
  {
    key: 'loyal',
    label: '忠诚用户',
    kind: '生命周期',
    action: '会员维护',
    rule: '购买天数达到忠诚阈值。',
    evidence: '复购频次稳定，是留存经营样本。',
  },
  {
    key: 'buyer',
    label: '购买用户',
    kind: '生命周期',
    action: '交叉推荐',
    rule: '有购买行为，但价值和频次未达到高阶分层。',
    evidence: '已完成成交，可观察下一次复购。',
  },
  {
    key: 'cart_intent',
    label: '加购意图',
    kind: '生命周期',
    action: '购物车召回',
    rule: '存在加购但尚无购买证据。',
    evidence: '转化意图强，适合价格或库存摩擦排查。',
  },
  {
    key: 'browser',
    label: '浏览用户',
    kind: '生命周期',
    action: '内容种草',
    rule: '只有浏览行为，尚未进入加购或购买。',
    evidence: '活跃但交易意图弱，适合内容和品类推荐。',
  },
  {
    key: 'unknown',
    label: '未知分层',
    kind: '生命周期',
    action: '补充数据',
    rule: '行为证据不足，未进入明确生命周期标签。',
    evidence: '需要继续积累行为或检查数据质量。',
  },
  {
    key: 'at_risk_focus',
    label: '流失风险',
    kind: '风险队列',
    action: '召回干预',
    rule: '最近活跃间隔超过风险阈值。',
    evidence: '这是风险带，不是 lifecycle_segment；用于运营优先级排序。',
  },
];

function segmentName(value?: string | null) {
  if (value === 'browser') return '浏览用户';
  if (value === 'loyal') return '忠诚用户';
  if (value === 'at_risk') return '流失风险';
  if (value === 'at_risk_focus') return '流失风险';
  return label('segment', value, { fallback: displayValue(value) });
}

function ruleThresholdCopy(rule: { name: string; threshold: number }) {
  if (rule.name === 'champion' || rule.name === 'high_value') return `收入 >= ${money(rule.threshold)}`;
  if (rule.name === 'loyal') return `购买活跃天数 >= ${number(rule.threshold)} 天`;
  if (rule.name === 'at_risk') return `最近活跃间隔 >= ${number(rule.threshold)} 天`;
  if (rule.name === 'cart_intent') return `加购次数 >= ${number(rule.threshold)} 次`;
  return `阈值 ${number(rule.threshold)}`;
}

function ruleDescriptionCopy(rule: { name: string; description?: string }) {
  if (rule.name === 'champion') return '高收入且多购买日，进入核心复购人群。';
  if (rule.name === 'high_value') return '收入达到高价值门槛，进入高价值人群。';
  if (rule.name === 'loyal') return '购买活跃天数达标，进入忠诚维护人群。';
  if (rule.name === 'at_risk') return '最近活跃间隔过长，进入流失风险队列。';
  if (rule.name === 'cart_intent') return '有加购但无购买证据，进入购物车召回。';
  return rule.description ?? '规则阈值来自后端生命周期契约。';
}

function buildLifecycleCards(summary: LifecycleSummary | undefined, segments: LifecycleSegment[], users: LifecycleUser[]): LifecycleCard[] {
  const segmentMap = new Map(segments.map((segment) => [segment.lifecycle_segment, segment]));
  const atRiskUsers = users.filter((user) => user.risk_band === 'at_risk');
  const atRiskRevenue = atRiskUsers.reduce((sum, user) => sum + user.revenue, 0);
  const atRiskPurchases = atRiskUsers.reduce((sum, user) => sum + user.purchases, 0);
  const atRiskRecency = atRiskUsers.length ? atRiskUsers.reduce((sum, user) => sum + user.recency_days, 0) / atRiskUsers.length : null;
  const totalUsers = summary?.user_count || segments.reduce((sum, segment) => sum + segment.users, 0) || 0;

  return lifecycleCatalog.map((item) => {
    if (item.key === 'at_risk_focus') {
      const usersCount = summary?.at_risk_users ?? atRiskUsers.length;
      return {
        ...item,
        users: usersCount,
        revenue: atRiskRevenue,
        purchases: atRiskPurchases,
        avgRecencyDays: atRiskRecency,
        share: totalUsers ? usersCount / totalUsers : 0,
      };
    }
    const segment = segmentMap.get(item.key);
    return {
      ...item,
      users: segment?.users ?? 0,
      revenue: segment?.revenue ?? 0,
      purchases: segment?.purchases ?? 0,
      avgRecencyDays: segment?.avg_recency_days ?? null,
      share: totalUsers && segment ? segment.users / totalUsers : 0,
    };
  });
}

function filterLifecycleUsers(users: LifecycleUser[], selectedSegment: string) {
  if (selectedSegment === 'all') return users;
  if (selectedSegment === 'at_risk_focus') return users.filter((user) => user.risk_band === 'at_risk');
  return users.filter((user) => user.lifecycle_segment === selectedSegment);
}

function topAffinityRows(rows: LifecycleCategoryAffinity[], limit = 5) {
  return rows.slice().sort((a, b) => b.user_revenue - a.user_revenue || b.users - a.users).slice(0, limit);
}

export function LifecyclePage() {
  const [selectedSegment, setSelectedSegment] = useState('all');
  const [selectedView, setSelectedView] = useState<LifecycleView>('matrix');
  const summary = useLifecycleSummary();
  const segments = useLifecycleSegments();
  const riskQueue = useLifecycleRiskQueue(200);
  const affinity = useLifecycleCategoryAffinity(50);
  const rules = useLifecycleRules();
  const hasError = summary.isError || segments.isError || riskQueue.isError || affinity.isError || rules.isError;
  const lifecycleCards = useMemo(
    () => buildLifecycleCards(summary.data, segments.data ?? [], riskQueue.data ?? []),
    [summary.data, segments.data, riskQueue.data],
  );
  const selectedCard = lifecycleCards.find((card) => card.key === selectedSegment) ?? lifecycleCards[0];
  const representativeUsers = filterLifecycleUsers(riskQueue.data ?? [], selectedSegment).slice(0, 8);
  const affinityRows = topAffinityRows(affinity.data ?? []);
  const activeRules = rules.data?.rules ?? [];
  const hasSelectedPopulation = selectedSegment !== 'all' && Boolean(selectedCard?.users);
  const previewSampleCount = riskQueue.data?.length ?? 0;
  const emptyQueueMessage = selectedSegment === 'all'
    ? '当前预览队列为空，请先生成生命周期缓存。'
    : hasSelectedPopulation
      ? `${segmentName(selectedSegment)} 全量命中 ${number(selectedCard?.users)} 人，但当前 ${number(previewSampleCount)} 条预览样本未覆盖该分层；左侧统计来自全量 Spark 聚合，队列表只是风险/价值优先抽样。`
      : '当前分层暂无命中用户，说明本批次没有进入该类别的重点用户。';

  return (
    <>
      <section className="page-heading">
        <span className="eyebrow">用户生命周期智能</span>
        <h1>用户生命周期与价值分层</h1>
        <p>基于特征集市用户日级事实构建最近活跃、频次、价值、活跃度、偏好类目和运营动作队列。</p>
      </section>

      {hasError ? (
        <div className="error-banner" role="alert">
          用户生命周期缓存尚未生成，请先运行 Spark 刷新任务。
        </div>
      ) : null}

      <section className="ops-command-band">
        <div>
          <span className="status-pill tone-success">生命周期契约 v1</span>
          <h2>{summary.data?.run_id ? `运行 ${summary.data.run_id}` : '等待生命周期运行'}</h2>
          <p>快照 {summary.data?.snapshot_dt ?? '待生成'} · 监控用户 {number(summary.data?.user_count)}</p>
        </div>
        <UsersRound size={22} />
      </section>

      <section className="metrics-strip">
        <article className="metric-card tone-success">
          <span>高价值用户</span>
          <strong>{number(summary.data?.high_value_users)}</strong>
          <small>生命周期收入 {money(summary.data?.revenue)}</small>
        </article>
        <article className="metric-card tone-warning">
          <span>转化意图</span>
          <strong>{number(summary.data?.convert_intent_users)}</strong>
          <small>购物车召回候选</small>
        </article>
        <article className="metric-card tone-danger">
          <span>流失风险</span>
          <strong>{number(summary.data?.at_risk_users)}</strong>
          <small>平均最近活跃 {number(summary.data?.avg_recency_days)} 天</small>
        </article>
        <article className="metric-card">
          <span>购买次数</span>
          <strong>{number(summary.data?.purchase_count)}</strong>
          <small>{number(summary.data?.segment_count)} 个生命周期分层</small>
        </article>
      </section>

      <section className={`lifecycle-console is-view-${selectedView}`} aria-label="用户生命周期分层控制台">
        <div className="lifecycle-console-head">
          <div>
            <span className="eyebrow">分层覆盖矩阵</span>
            <h2>每类用户都可见，但只下钻代表样本</h2>
            <p>左侧展示完整生命周期目录，右侧根据选中类别解释进入规则、当前规模和建议动作。</p>
          </div>
          <div className="lifecycle-tabs" aria-label="用户分层视图">
            {[
              ['matrix', '分层矩阵'],
              ['rules', '规则解释'],
              ['queue', '运营队列'],
            ].map(([key, text]) => (
              <button
                type="button"
                className={selectedView === key ? 'is-active' : ''}
                aria-pressed={selectedView === key}
                key={key}
                onClick={() => setSelectedView(key as LifecycleView)}
              >
                {text}
              </button>
            ))}
          </div>
        </div>

        <div className="lifecycle-teacher-note">
          <strong>答辩提示：</strong>
          <span>这里不是枚举所有用户，而是先证明分层体系覆盖了所有关键类别，再按选中类别展示代表样本和运营动作。</span>
        </div>

        <div className="lifecycle-view-status" aria-live="polite">
          <strong>
            当前视图：
            {selectedView === 'matrix' ? '分层矩阵' : selectedView === 'rules' ? '规则解释' : '运营队列'}
          </strong>
          <span>
            {selectedView === 'matrix'
              ? '展示所有生命周期类别和风险队列，点击卡片会联动右侧检查器。'
              : selectedView === 'rules'
                ? '聚焦进入分层的判定门槛，右侧数字均为规则阈值，不是用户数。'
                : '展示当前选中类别的代表用户样本，用于说明后续运营动作。'}
          </span>
        </div>

        <div className="lifecycle-workbench">
          <div className="lifecycle-matrix" aria-label="生命周期分层矩阵">
            <button
              type="button"
              className={`lifecycle-segment-tile tone-queued${selectedSegment === 'all' ? ' is-active' : ''}`}
              onClick={() => setSelectedSegment('all')}
            >
              <span>全部用户</span>
              <strong>{number(summary.data?.user_count)}</strong>
              <small>完整用户池 · {number(summary.data?.segment_count)} 个真实分层</small>
              <i style={{ width: '100%' }} />
              <em>查看全局代表队列</em>
            </button>
            {lifecycleCards.map((card) => (
              <button
                type="button"
                className={`lifecycle-segment-tile tone-${segmentTone(card.key)}${selectedSegment === card.key ? ' is-active' : ''}`}
                key={card.key}
                onClick={() => setSelectedSegment(card.key)}
              >
                <span>{card.label}</span>
                <strong>{number(card.users)}</strong>
                <small>{card.kind} · {money(card.revenue)} · {number(card.purchases)} 次购买</small>
                <i style={{ width: card.share > 0 ? `${Math.max(4, Math.min(100, card.share * 100))}%` : '0%' }} />
                <em>{card.action} · 占比 {percent(card.share)}</em>
              </button>
            ))}
          </div>

          <aside className={`lifecycle-inspector tone-${segmentTone(selectedCard?.key)}`} aria-label="生命周期分层规则检查器">
            <div className="panel-title">
              <div>
                <h2>{selectedSegment === 'all' ? '全局分层检查器' : `${selectedCard?.label} 检查器`}</h2>
                <p>{algorithmCopy(rules.data?.model ?? '最近活跃、频次和价值规则 + 活跃度分层')}</p>
              </div>
              <HeartPulse size={20} />
            </div>
            <dl className="lifecycle-inspector-metrics">
              <div>
                <dt>用户规模</dt>
                <dd>{selectedSegment === 'all' ? number(summary.data?.user_count) : number(selectedCard?.users)}</dd>
              </div>
              <div>
                <dt>收入贡献</dt>
                <dd>{selectedSegment === 'all' ? money(summary.data?.revenue) : money(selectedCard?.revenue)}</dd>
              </div>
              <div>
                <dt>平均最近活跃</dt>
                <dd>{selectedSegment === 'all' ? `${number(summary.data?.avg_recency_days)} 天` : selectedCard?.avgRecencyDays == null ? '待生成' : `${number(selectedCard.avgRecencyDays)} 天`}</dd>
              </div>
              <div>
                <dt>推荐动作</dt>
                <dd>{selectedSegment === 'all' ? '按分层分配动作' : selectedCard?.action}</dd>
              </div>
            </dl>
            <div className="lifecycle-rule-copy">
              <strong>进入规则</strong>
              <p>{selectedSegment === 'all' ? 'Spark 按用户日级事实聚合最近活跃、购买频次、收入和行为强度，再生成生命周期标签与风险带。' : selectedCard?.rule}</p>
              <strong>证据解释</strong>
              <p>{selectedSegment === 'all' ? '矩阵中 0 用户类别仍保留，表示体系具备该类识别能力，只是当前批次没有命中。' : selectedCard?.evidence}</p>
            </div>
            <div className="lifecycle-rule-list" aria-label="生命周期阈值规则">
              <div className="lifecycle-rule-list-head">
                <span>规则阈值，不是用户数</span>
                <small>左侧卡片显示实际命中用户；这里显示进入该分层的判定门槛。</small>
              </div>
              {activeRules.map((rule) => (
                <button
                  type="button"
                  className={rule.name === selectedSegment || (selectedSegment === 'at_risk_focus' && rule.name === 'at_risk') ? 'is-active' : ''}
                  key={rule.name}
                  onClick={() => setSelectedSegment(rule.name === 'at_risk' ? 'at_risk_focus' : rule.name)}
                >
                  <span>
                    <strong>{segmentName(rule.name)}</strong>
                    <small>{ruleDescriptionCopy(rule)}</small>
                  </span>
                  <em>{ruleThresholdCopy(rule)}</em>
                </button>
              ))}
            </div>
          </aside>
        </div>

        {selectedView === 'queue' ? (
          <article className="data-panel lifecycle-queue-panel lifecycle-inline-queue">
            <div className="panel-title">
              <div>
                <h2>当前视图：运营队列</h2>
                <p>当前筛选：{selectedSegment === 'all' ? '全部关键用户' : segmentName(selectedSegment)}。这里展示代表样本，不枚举全量用户。</p>
              </div>
              <Target size={20} />
            </div>
            <div className="lifecycle-queue-toolbar" aria-label="代表用户队列筛选">
              <ListFilter size={16} />
              {['all', 'champion', 'high_value', 'cart_intent', 'at_risk_focus'].map((key) => (
                <button
                  type="button"
                  className={selectedSegment === key ? 'is-active' : ''}
                  key={key}
                  onClick={() => setSelectedSegment(key)}
                >
                  {key === 'all' ? '全部' : segmentName(key)}
                </button>
              ))}
            </div>
            {representativeUsers.length === 0 && hasSelectedPopulation ? (
              <div className="lifecycle-sample-gap" role="status">
                <strong>{segmentName(selectedSegment)} 有全量用户，但预览样本未覆盖</strong>
                <dl>
                  <div>
                    <dt>全量用户</dt>
                    <dd>{number(selectedCard?.users)}</dd>
                  </div>
                  <div>
                    <dt>收入贡献</dt>
                    <dd>{money(selectedCard?.revenue)}</dd>
                  </div>
                  <div>
                    <dt>购买次数</dt>
                    <dd>{number(selectedCard?.purchases)}</dd>
                  </div>
                  <div>
                    <dt>预览样本池</dt>
                    <dd>{number(previewSampleCount)}</dd>
                  </div>
                </dl>
                <p>该表只展示后端导出的代表样本，不等于全量用户清单；左侧卡片才是该分层的全量统计。</p>
              </div>
            ) : null}
            <div className="table-scroll">
              <table aria-label="当前视图代表用户队列">
                <thead>
                  <tr>
                    <th>用户</th>
                    <th>分层</th>
                    <th>风险</th>
                    <th>偏好类目</th>
                    <th>浏览</th>
                    <th>加购</th>
                    <th>购买</th>
                    <th>收入</th>
                    <th>建议动作</th>
                  </tr>
                </thead>
                <tbody>
                  {representativeUsers.map((user) => (
                    <tr key={user.user_id}>
                      <td>{user.user_id}</td>
                      <td><span className={`status-pill tone-${segmentTone(user.lifecycle_segment)}`}>{segmentName(user.lifecycle_segment)}</span></td>
                      <td>{label('risk', user.risk_band)}</td>
                      <td>{displayValue(user.preferred_category_level1)}</td>
                      <td>{number(user.views)}</td>
                      <td>{number(user.carts)}</td>
                      <td>{number(user.purchases)}</td>
                      <td>{money(user.revenue)}</td>
                      <td>{algorithmCopy(user.recommended_action)}</td>
                    </tr>
                  ))}
                  {representativeUsers.length === 0 ? (
                    <tr>
                      <td colSpan={9}>{emptyQueueMessage}</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </article>
        ) : null}
      </section>

      <section className="lifecycle-ops-grid">
        <article className="data-panel lifecycle-affinity-panel">
          <div className="panel-title">
            <div>
              <h2>偏好类目摘要</h2>
              <p>用 Top 类目概览替代表格堆叠，说明用户分层背后的商品兴趣。</p>
            </div>
            <Eye size={20} />
          </div>
          <div className="lifecycle-affinity-list">
            {affinityRows.map((row) => {
              const maxRevenue = Math.max(...affinityRows.map((item) => item.user_revenue), 1);
              return (
                <div className="lifecycle-affinity-row" key={row.category_level1 ?? 'unknown'}>
                  <span>{displayValue(row.category_level1)}</span>
                  <strong>{number(row.users)} 人</strong>
                  <i style={{ width: row.user_revenue > 0 ? `${Math.max(4, (row.user_revenue / maxRevenue) * 100)}%` : '0%' }} />
                  <small>{money(row.user_revenue)} · {number(row.user_purchases)} 次购买</small>
                </div>
              );
            })}
          </div>
        </article>

        <article className="data-panel lifecycle-queue-panel">
          <div className="panel-title">
            <div>
              <h2>代表运营队列</h2>
              <p>当前筛选：{selectedSegment === 'all' ? '全部关键用户' : segmentName(selectedSegment)}。仅展示代表样本，不枚举全量用户。</p>
            </div>
            <Target size={20} />
          </div>
          <div className="lifecycle-queue-toolbar" aria-label="代表用户队列筛选">
            <ListFilter size={16} />
            {['all', 'champion', 'high_value', 'cart_intent', 'at_risk_focus'].map((key) => (
              <button
                type="button"
                className={selectedSegment === key ? 'is-active' : ''}
                key={key}
                onClick={() => setSelectedSegment(key)}
              >
                {key === 'all' ? '全部' : segmentName(key)}
              </button>
            ))}
          </div>
          {representativeUsers.length === 0 && hasSelectedPopulation ? (
            <div className="lifecycle-sample-gap" role="status">
              <strong>{segmentName(selectedSegment)} 有全量用户，但预览样本未覆盖</strong>
              <dl>
                <div>
                  <dt>全量用户</dt>
                  <dd>{number(selectedCard?.users)}</dd>
                </div>
                <div>
                  <dt>收入贡献</dt>
                  <dd>{money(selectedCard?.revenue)}</dd>
                </div>
                <div>
                  <dt>购买次数</dt>
                  <dd>{number(selectedCard?.purchases)}</dd>
                </div>
                <div>
                  <dt>预览样本池</dt>
                  <dd>{number(previewSampleCount)}</dd>
                </div>
              </dl>
              <p>该表只展示后端导出的代表样本，不等于全量用户清单；左侧卡片才是该分层的全量统计。</p>
            </div>
          ) : null}
          <div className="table-scroll">
            <table aria-label="用户生命周期运营动作队列">
              <thead>
                <tr>
                  <th>用户</th>
                  <th>分层</th>
                  <th>风险</th>
                  <th>偏好类目</th>
                  <th>浏览</th>
                  <th>加购</th>
                  <th>购买</th>
                  <th>收入</th>
                  <th>建议动作</th>
                </tr>
              </thead>
              <tbody>
                {representativeUsers.map((user) => (
                  <tr key={user.user_id}>
                    <td>{user.user_id}</td>
                    <td><span className={`status-pill tone-${segmentTone(user.lifecycle_segment)}`}>{segmentName(user.lifecycle_segment)}</span></td>
                    <td>{label('risk', user.risk_band)}</td>
                    <td>{displayValue(user.preferred_category_level1)}</td>
                    <td>{number(user.views)}</td>
                    <td>{number(user.carts)}</td>
                    <td>{number(user.purchases)}</td>
                    <td>{money(user.revenue)}</td>
                    <td>{algorithmCopy(user.recommended_action)}</td>
                  </tr>
                ))}
                {representativeUsers.length === 0 ? (
                  <tr>
                    <td colSpan={9}>{emptyQueueMessage}</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </article>
      </section>
    </>
  );
}
