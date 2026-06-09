import {
  Activity,
  BarChart3,
  Boxes,
  Database,
  Files,
  FlaskConical,
  Gauge,
  GitCompareArrows,
  Network,
  PackageCheck,
  BadgeDollarSign,
  Repeat2,
  Route,
  Radar,
  Search,
  ShieldAlert,
  Siren,
  ShoppingCart,
  TrendingUpDown,
  UsersRound,
  type LucideIcon,
} from 'lucide-react';

export type NavItem = {
  to: string;
  label: string;
  detail: string;
  group: '核心驾驶舱' | '智能分析' | '数据与运维';
  icon: LucideIcon;
};

export const navItems: NavItem[] = [
  { to: '/', label: '总览', detail: '核心指标、趋势和关键排行', group: '核心驾驶舱', icon: Gauge },
  { to: '/behavior', label: '行为分析', detail: '事件分布与行为趋势', group: '核心驾驶舱', icon: Activity },
  { to: '/conversion', label: '转化分析', detail: '漏斗、分日转化和商品路径', group: '核心驾驶舱', icon: GitCompareArrows },
  { to: '/cart-recovery', label: '购物车召回', detail: '流失价值、显式移除和召回优先级', group: '核心驾驶舱', icon: ShoppingCart },
  { to: '/attribution', label: '营收归因', detail: '多触点归因、辅助营收和转化机会', group: '核心驾驶舱', icon: BadgeDollarSign },
  { to: '/journey', label: '旅程路径', detail: '高频路径、事件转移、退出点和购买前路径', group: '核心驾驶舱', icon: Route },
  { to: '/optimization', label: '优化决策', detail: '促销预算和推荐位方案', group: '智能分析', icon: PackageCheck },
  { to: '/recommendations', label: '推荐守护', detail: '推荐快照、门禁和回滚证据', group: '智能分析', icon: Radar },
  { to: '/anomalies', label: '异常雷达', detail: '运营告警、稳健基线和处置证据', group: '智能分析', icon: Siren },
  { to: '/lifecycle', label: '用户分层', detail: '生命周期、RFM、风险队列和偏好类目', group: '智能分析', icon: UsersRound },
  { to: '/cohorts', label: '留存复购', detail: 'Cohort 留存、复购间隔、价值曲线和类目风险', group: '智能分析', icon: Repeat2 },
  { to: '/experiments', label: '策略实验', detail: 'A/B 分流、uplift 先验、实验护栏和执行清单', group: '智能分析', icon: FlaskConical },
  { to: '/forecasting', label: '需求预测', detail: 'GMV 预测、稀疏回退、回测和营收风险', group: '智能分析', icon: TrendingUpDown },
  { to: '/affinity', label: '商品图谱', detail: '共看、共购、搭配替代和商品社群', group: '智能分析', icon: Network },
  { to: '/portfolio', label: '组合经营', detail: '品类、品牌、价格带和商品集中度', group: '智能分析', icon: Boxes },
  { to: '/feature-mart', label: '特征集市', detail: '行为事实、分区水位和特征预览', group: '数据与运维', icon: Files },
  { to: '/quality', label: '数据质量', detail: '清洗、异常和质量门禁', group: '数据与运维', icon: ShieldAlert },
  { to: '/rankings', label: '排行洞察', detail: '类目和品牌表现', group: '数据与运维', icon: BarChart3 },
  { to: '/table', label: '明细查询', detail: '原始事件分页检索', group: '数据与运维', icon: Search },
  { to: '/ops', label: '作业状态', detail: 'Spark 运行、血缘和 manifest', group: '数据与运维', icon: Database },
];

export const navGroups = Array.from(new Set(navItems.map((item) => item.group)));
