# Phase 4: React 前端大屏

## 目标

实现 4 页面可视化大屏：实时监控、历史分析、区域配置、AI 报告。

复杂度：中 | 风险：低 | 预计时间：3-4 天

## 业务流

```
WebSocket 连接
    ↓
接收 FrameReport JSON
    ↓
React 状态更新
    ↓
组件重新渲染
    ├── VideoPlayer: 视频帧显示
    ├── StatsCard: 实时数据卡片
    ├── StatsChart: ECharts 图表
    └── ZoneStats: 区域统计
```

## 目录结构

```
interfaces/frontend/
├── package.json
├── tsconfig.json
├── vite.config.ts
├── index.html
├── public/
└── src/
    ├── main.tsx                # 入口
    ├── App.tsx                 # 路由配置
    ├── api/
    │   ├── client.ts           # API 客户端
    │   ├── video.ts            # 视频 API
    │   ├── stats.ts            # 统计 API
    │   ├── zones.ts            # 区域 API
    │   └── aiReport.ts         # AI 报告 API
    ├── hooks/
    │   ├── useWebSocket.ts     # WebSocket hook
    │   ├── useVideoStream.ts   # 视频流 hook
    │   └── useStats.ts         # 统计数据 hook
    ├── pages/
    │   ├── RealtimeMonitor.tsx # 实时监控大屏
    │   ├── HistoricalAnalysis.tsx # 历史分析
    │   ├── ZoneConfig.tsx      # 区域配置
    │   └── AIReport.tsx        # AI 报告
    ├── components/
    │   ├── Layout/
    │   │   ├── AppLayout.tsx   # 应用布局
    │   │   ├── Sidebar.tsx     # 侧边栏
    │   │   └── Header.tsx      # 顶部栏
    │   ├── Video/
    │   │   ├── VideoPlayer.tsx # 视频播放器
    │   │   └── VideoControls.tsx # 视频控制
    │   ├── Charts/
    │   │   ├── StatsChart.tsx  # 统计图表
    │   │   ├── FlowChart.tsx   # 流量趋势图
    │   │   ├── SpeedChart.tsx  # 速度分布图
    │   │   └── HeatMap.tsx     # 热力图
    │   ├── Cards/
    │   │   ├── StatsCard.tsx   # 统计卡片
    │   │   └── ZoneStatsCard.tsx # 区域统计卡片
    │   └── Zone/
    │       ├── ZoneEditor.tsx  # 区域编辑器
    │       └── CalibrationTool.tsx # 标定工具
    ├── stores/
    │   ├── websocketStore.ts   # WebSocket 状态
    │   └── statsStore.ts       # 统计数据状态
    ├── types/
    │   ├── frameReport.ts      # FrameReport 类型
    │   ├── zoneConfig.ts       # ZoneConfig 类型
    │   └── stats.ts            # 统计类型
    └── utils/
        ├── formatters.ts       # 数据格式化
        └── constants.ts        # 常量
```

## 页面设计

### 页面 1: 实时监控大屏 (RealtimeMonitor)

**布局**：左侧视频播放器，右侧数据卡片，底部流量趋势图

**组件**：
- VideoPlayer：MJPEG 流显示
- StatsCard：实时数据卡片（总进入/离开/FPS/活跃目标/平均速度）
- ZoneStatsCard：区域统计卡片
- FlowChart：流量趋势图（ECharts 折线图，最近 60 秒）

**数据流**：WebSocket 接收 FrameReport → 更新 statsStore → 组件自动重新渲染

### 页面 2: 历史数据分析 (HistoricalAnalysis)

**功能**：
- 时间范围选择器（日期选择）
- 流量趋势图（ECharts 折线图）
- 速度分布图（ECharts 直方图）
- 热力图（目标密度）
- 数据导出（CSV/JSON）

### 页面 3: 区域配置管理 (ZoneConfig)

**功能**：
- Canvas 上可视化编辑区域
- 拖拽调整线段位置
- 添加/删除区域
- 标定点设置（速度估算）
- 配置保存/加载

### 页面 4: AI 分析报告 (AIReport)

**功能**：
- 一键生成报告按钮
- 报告内容展示（Markdown 渲染）
- 历史报告列表
- 报告导出（PDF）

## 组件清单

### Layout 组件

| 组件 | 作用 | 行数 |
|---|---|---|
| AppLayout | 应用主布局 | ~50 |
| Sidebar | 侧边导航 | ~80 |
| Header | 顶部栏 | ~40 |

### Video 组件

| 组件 | 作用 | 行数 |
|---|---|---|
| VideoPlayer | MJPEG 流显示 | ~100 |
| VideoControls | 播放/暂停/停止 | ~60 |

### Charts 组件

| 组件 | 作用 | 行数 |
|---|---|---|
| StatsChart | 通用统计图表 | ~120 |
| FlowChart | 流量趋势图 | ~100 |
| SpeedChart | 速度分布图 | ~100 |
| HeatMap | 热力图 | ~100 |

### Cards 组件

| 组件 | 作用 | 行数 |
|---|---|---|
| StatsCard | 实时数据卡片 | ~60 |
| ZoneStatsCard | 区域统计卡片 | ~80 |

### Zone 组件

| 组件 | 作用 | 行数 |
|---|---|---|
| ZoneEditor | 区域可视化编辑器 | ~200 |
| CalibrationTool | 标定工具 | ~150 |

## Hooks 设计

### useWebSocket (~150 行)

功能：建立连接、自动重连、心跳检测、消息解析、状态管理

返回值：
- `report: FrameReport | null` — 最新报告
- `isConnected: boolean` — 连接状态
- `error: string | null` — 错误信息
- `connect()` / `disconnect()`

### useVideoStream (~100 行)

功能：创建视频 URL、加载状态、错误处理

返回值：`videoUrl`, `isLoading`, `error`

### useStats (~100 行)

功能：获取实时/历史/累计统计

返回值：`realtimeStats`, `historyStats`, `cumulativeStats`, `fetchStats()`

## 状态管理

### websocketStore

状态：`connectionStatus`, `lastReport`, `error`

### statsStore

状态：`realtime`, `history`, `cumulative`

## API 客户端

### client.ts — HTTP 客户端封装

功能：基础 URL 配置、请求拦截、响应拦截、错误处理

### video.ts — 视频 API

方法：`uploadVideo`, `startProcessing`, `stopProcessing`, `getVideoStreamUrl`

### stats.ts — 统计 API

方法：`getRealtimeStats`, `getHistoryStats`, `getCumulativeStats`

### zones.ts — 区域 API

方法：`getZones`, `updateZones`

### aiReport.ts — AI 报告 API

方法：`generateReport`, `getReports`

## 类型定义

### frameReport.ts

```typescript
interface Track {
  tracker_id: number
  class_id: number
  class_name: string
  confidence: number
  xyxy: [number, number, number, number]
  speed_kmh: number | null
}

interface ZoneStats {
  name: string
  in_count: number
  out_count: number
}

interface FrameReport {
  frame_index: number
  timestamp_sec: number
  fps: number
  active_tracks: Track[]
  zone_stats: ZoneStats[]
  total_in: number
  total_out: number
}
```

### zoneConfig.ts

```typescript
interface ZoneConfig {
  name: string
  line_start: [number, number]
  line_end: [number, number]
}
```

### stats.ts

```typescript
interface CumulativeStats {
  total_frames: number
  total_unique_tracks: number
  zone_stats: ZoneStats[]
  avg_fps: number
  avg_speed_kmh: number | null
  processing_time_sec: number
}
```

## 测试计划

### 组件测试

- VideoPlayer.test.tsx (~4 tests)
- StatsCard.test.tsx (~3 tests)
- ZoneEditor.test.tsx (~5 tests)
- FlowChart.test.tsx (~3 tests)

### Hook 测试

- useWebSocket.test.ts (~5 tests)
- useVideoStream.test.ts (~3 tests)
- useStats.test.ts (~4 tests)

### E2E 测试

- realtime-monitor.spec.ts — 实时监控页面
- historical-analysis.spec.ts — 历史分析页面
- zone-config.spec.ts — 区域配置页面
- ai-report.spec.ts — AI 报告页面

## 验证清单

- [ ] React 应用启动成功
- [ ] 4 个页面全部可访问
- [ ] WebSocket 连接成功
- [ ] 实时监控页面显示视频流
- [ ] 实时监控页面显示统计数据
- [ ] 历史分析页面显示图表
- [ ] 区域配置页面编辑功能正常
- [ ] AI 报告页面生成功能正常
- [ ] 响应式布局正常
- [ ] 所有组件测试通过
- [ ] E2E 测试通过

## 工作量评估

```yaml
模块: Phase 4 - React 前端大屏
复杂度: 中
预计开发: 3-4 天
依赖模块:
  - React 18
  - TypeScript
  - ECharts
  - Axios
测试成本: 中
风险: 低
未来扩展:
  - 移动端适配
  - 更多图表类型
  - 实时告警
```

## 技术债检查

```yaml
Phase: 4
当前技术债: 无
耦合情况: 组件间通过 props 和状态管理通信
扩展风险: 低
是否需要重构: 否
建议拆分方案: 无
```
