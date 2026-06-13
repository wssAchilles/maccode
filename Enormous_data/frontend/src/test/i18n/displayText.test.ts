import { describe, expect, it } from 'vitest';
import {
  algorithmCopy,
  benchmarkSampleLabel,
  benchmarkVariantLabel,
  displayValue,
  experimentLabel,
  fieldLabel,
  label,
  moduleLabel,
  rawDisplayValue,
  statusLabel,
} from '../../i18n/displayText';

describe('displayText', () => {
  it('localizes status, event, reason, action, model, and metric codes', () => {
    expect(statusLabel('succeeded')).toBe('已成功');
    expect(displayValue('purchase', 'eventType')).toBe('购买');
    expect(label('reason', 'fallback_pressure')).toBe('兜底压力');
    expect(label('action', 'add_cross_sell_slot')).toBe('增加交叉销售位');
    expect(label('model', 'rolling_baseline')).toBe('滚动基线');
    expect(label('model', 'spark_ml_logistic_ranker_v1')).toBe('Spark ML 逻辑回归排序器');
    expect(label('model', 'spark_ml_gbt_ranker_v1')).toBe('Spark ML 梯度提升树排序器');
    expect(fieldLabel('fallback_rate')).toBe('兜底推荐占比');
    expect(fieldLabel('ordering_anomaly_ratio')).toBe('会话顺序异常比例');
    expect(fieldLabel('purchase_missing_price_ratio')).toBe('购买缺价比例');
    expect(fieldLabel('session_fact_rows')).toBe('会话事实行数');
    expect(label('source', 'category_recall')).toBe('品类偏好召回');
    expect(label('source', 'graph_neighbor_recall')).toBe('图谱邻居召回');
    expect(label('source', 'ranked_topk')).toBe('已进入前 K');
    expect(label('source', 'spark_cube')).toBe('Spark 物化指标层');
    expect(label('source', 'detail_scan')).toBe('明细扫描');
    expect(label('reason', 'dashboard_cube_missing')).toBe('物化指标层缺失');
    expect(displayValue('dashboard_metric_cube', 'lineage')).toBe('物化指标层');
    expect(fieldLabel('ranker_score')).toBe('排序分数');
    expect(fieldLabel('event_count')).toBe('事件量');
    expect(fieldLabel('affinity_score')).toBe('亲和分数');
    expect(statusLabel('feasible')).toBe('可满足');
    expect(statusLabel('published')).toBe('已发布');
    expect(statusLabel('fresh')).toBe('新鲜');
    expect(statusLabel('missing')).toBe('缺失');
    expect(statusLabel('degraded')).toBe('已降级');
    expect(label('segment', 'cart_intent')).toBe('加购意图');
    expect(label('action', 'price_band_mix')).toBe('价格带结构');
    expect(label('reason', 'sparse_cohort')).toBe('稀疏留存分群');
  });

  it('does not expose raw English codes unless explicitly requested', () => {
    expect(statusLabel('running')).toBe('运行中');
    expect(label('status', 'running', { includeRaw: true })).toBe('运行中 running');
  });

  it('keeps original data values when no semantic mapping exists', () => {
    expect(displayValue('electronics.smartphone')).toBe('electronics.smartphone');
    expect(displayValue('unknown')).toBe('未知');
    expect(rawDisplayValue('unknown')).toBe('未知');
    expect(rawDisplayValue('samsung')).toBe('samsung');
  });

  it('translates known algorithm copy', () => {
    expect(algorithmCopy('Protect experience quality and avoid excessive fallback recommendations.')).toBe(
      '保护推荐体验，避免兜底推荐占比过高。',
    );
    expect(algorithmCopy('真实 uplift 需要随机曝光、对照组和结果回流后才能判断。')).toBe(
      '真实增量提升需要随机曝光、对照组和结果回流后才能判断。',
    );
  });

  it('localizes experiment, benchmark, and module identifiers', () => {
    expect(experimentLabel('lifecycle_reactivation')).toBe('生命周期再激活策略');
    expect(benchmarkSampleLabel('1pct')).toBe('1% 抽样');
    expect(benchmarkVariantLabel('yarn_only_csv')).toBe('集群 CSV 基线');
    expect(moduleLabel('recommendation')).toBe('推荐系统');
  });
});
