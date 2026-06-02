# Frontend

React + TypeScript 前端用于课设展示大屏。

后续页面按 `RealtimeMonitor`、`HistoricalAnalysis`、`ZoneConfig`、`AIReport` 四个页面推进。

## Anime.js 动效约定

前端使用 `animejs` 做克制式微交互增强，只服务信息指向和操作反馈，不参与 CV 结果计算。

导入方式：

```ts
import { animate, createScope, stagger } from "animejs";
```

React 组件内的 Anime.js 动画必须绑定局部 root，并在卸载或依赖变化时清理：

```ts
const rootRef = useRef<HTMLElement | null>(null);

useAnimeScope(rootRef, () => {
  animate(".metric-tile", {
    opacity: [0, 1],
    y: [6, 0],
    duration: 280,
    ease: "out(3)"
  });
}, [someDependency]);
```

约束：

- 优先动画 `transform`、`opacity`、SVG `strokeWidth` 等低成本属性。
- 必须尊重 `prefers-reduced-motion`；统一通过 `useAnimeScope` 或 `prefersReducedMotion()` 接入。
- 适合目标锁定、Geek Mode 抽屉、KPI 更新、AI 报告进入、空状态提示。
- 禁止用 Anime.js 驱动后端处理视频、CV 真实轨迹、检测框坐标、图表主渲染或布局尺寸动画。
