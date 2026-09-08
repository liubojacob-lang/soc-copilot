# 任务清单 - Dashboard UI 优化

- [x] 1. 设计令牌系统与 Tailwind 主题扩展
  - 修改 `frontend/tailwind.config.ts`，移除 glow、glass、neumorphic 等廉价科技感阴影配置，移除 pulse-soft、float、glow-pulse、shimmer、wiggle、rotate-slow、morph 等花哨动画
  - 扩展 Slate 主色系（primary-50 至 primary-900），替换现有 `soc` 色系
  - 扩展语义色系列（semantic-success、semantic-warning、semantic-danger、semantic-info），将色值调整为低饱和度版本
  - 扩展字号层级（text-display、text-h1、text-h2、text-h3、text-body、text-small、text-caption）
  - 扩展间距令牌（space-1 至 space-16），采用 8pt/4pt 网格
  - 扩展圆角令牌（radius-sm、radius-md、radius-lg），移除 2xl 以上大圆角
  - 扩展阴影令牌（shadow-subtle、shadow-sm、shadow-md、shadow-lg），全部使用中性色投影
  - 保留并调整简洁动画（fade-in 150ms、fade-in-up 位移 8px/200ms、slide-in-right 位移 8px/200ms）
  - 重写 `frontend/styles/designTokens.ts`，将颜色、间距、圆角、阴影、字体、边框令牌统一为新的 Slate 色系与语义规范
  - 确保子需求可独立运行（Tailwind 配置变更后编译通过）
  - _需求：[FR-002]_

- [x] 2. 原子层与分子层基础组件
  - 新建 `frontend/components/atoms/Typography.tsx`，实现基于设计令牌的文本渲染组件（Display、H1、H2、H3、Body、Small、Caption），支持字号、字重、行高、颜色令牌
  - 新建 `frontend/components/atoms/Divider.tsx`，实现 1px 高度、border-subtle 颜色的分割线原子组件
  - 新建 `frontend/components/molecules/Badge.tsx`，实现状态标签组件：圆角不超过 4px，字号 12px，使用语义色背景+文字色组合，支持 success、warning、danger、info 变体
  - 新建 `frontend/components/molecules/Button.tsx`，实现按钮组件：圆角 8px，hover 仅允许背景色变化，点击时短暂按压效果（scale 0.98，100ms）
  - 新建 `frontend/components/molecules/Tooltip.tsx`，实现简洁卡片样式提示框：背景色 surface-primary，阴影 shadow-sm，圆角 8px，无边框发光
  - 确保子需求可独立运行（组件可在 Storybook 或独立页面中预览）
  - _需求：[FR-001, FR-002]_

- [x] 3. KPI 卡片与信息卡片组件
  - 修改 `frontend/components/common/Card.tsx`，移除 glass、neumorphic、elevated 变体，保留 default 和 outlined 变体
  - 将卡片圆角统一为 8px（radius-md）或 12px（radius-lg），阴影改为 shadow-sm，边框使用 border-subtle
  - 重写 `StatCard` 组件，移除 gradient 文字、-webkit-background-clip、glow 阴影、group-hover:scale-110、group-hover:rotate-5 等花哨效果
  - KPI 卡片数值使用 text-display（32px/500）字号，标签使用 text-small（12px/400），颜色来自设计令牌
  - 卡片 hover 状态仅允许轻微上移（translateY -2px）或边框色变化，移除霓虹灯发光和放大效果
  - 确保子需求可独立运行
  - _需求：[FR-003, FR-007]_

- [x] 4. 图表容器与图表库主题适配器
  - 新建 `frontend/lib/chartThemeAdapter.ts`，实现图表主题适配器：将设计令牌映射到 Recharts/ECharts 配置对象
  - 配置图表配色：Series 1 `#2563eb`、Series 2 `#059669`、Series 3 `#d97706`、Series 4 `#dc2626`、Series 5 `#64748b`、Series 6 `#7c3aed`，超出 6 个分类归为"其他"并使用中性灰色
  - 配置坐标轴样式：轴线颜色 `#cbd5e1`，刻度文字 11px `#64748b`
  - 配置网格线：使用 `#e2e8f0` / `#334155` 虚线样式
  - 配置 Tooltip：背景色 surface-primary，阴影 shadow-sm，圆角 8px，内边距 12px
  - 配置图例：文字 12px，色块 8x8px，圆角 2px
  - 新建 `frontend/components/organisms/ChartCard.tsx`，实现图表容器组件：圆角 8px，标题使用 text-h2，内部通过适配器渲染图表
  - 确保子需求可独立运行
  - _需求：[FR-004]_

- [x] 5. 数据表格与状态标签组件
  - 新建 `frontend/components/organisms/DataTable.tsx`，实现数据表格组件
  - 表头：字号略大于正文（14px/15px），字重 500-600，颜色 text-secondary，底部 1px 分割线 border-subtle
  - 表格行高统一 48-52px，行与行之间使用 1px border-subtle 分割线或斑马纹背景
  - 行 hover 状态使用极浅背景色（`#f8fafc` / `#1e293b`），禁止行变色、发光
  - 状态列使用 Badge 组件展示（来自任务2），圆角不超过 4px，字号 12px
  - 操作列按钮采用图标+文字或纯图标，图标风格统一为线框风格（stroke-width 1.5-2px）
  - 分页器样式简洁，页码按钮圆角不超过 4px，当前页使用主色背景+白字
  - 筛选面板样式与整体设计语言一致，使用 shadow-md 下拉面板，边框 border-subtle
  - 确保子需求可独立运行
  - _需求：[FR-005]_

- [x] 6. 导航组件
  - 修改 `frontend/components/Navigation.tsx`，调整顶部导航栏：高度统一为 56-64px，背景色使用纯色（白色或深色模式 `#1e293b`），移除渐变背景和 glass 效果
  - 导航栏阴影改为 shadow-subtle（`0 1px 2px rgba(0,0,0,0.05)`），移除发光阴影和 shadow-elevated
  - 菜单项图标统一使用线框风格（stroke-width 1.5-2px），移除填充风格图标和彩色图标
  - 导航项 active 状态左侧使用 3-4px 宽的主色指示条，hover 状态背景变浅灰/浅蓝灰、文字变主色
  - 用户头像、通知图标使用中性色，hover 时圆形背景变灰
  - 修改 `frontend/components/common/Breadcrumbs.tsx`，使用 14px 字号，分隔符 `/` 或 `>`，颜色为中性灰
  - 确保子需求可独立运行
  - _需求：[FR-006]_

- [x] 7. 数据展示专用组件
  - 新建 `frontend/components/organisms/RiskScore.tsx`，实现风险评分组件：数字使用 text-display（32px），进度条高度 4-6px，圆角 radius-full，颜色随分数变化（低=绿、中=黄、高=橙、严重=红），颜色来自语义色规范
  - 新建 `frontend/components/molecules/TimeDisplay.tsx`，实现时间展示组件：相对时间（如"2 小时前"）+ 绝对时间 Tooltip
  - 新建 `frontend/components/molecules/IocDisplay.tsx`，实现 IOC 数据展示组件：IP/域名/Hash 使用等宽字体（font-mono），背景色 code-bg，圆角 4px，支持一键复制
  - 新建 `frontend/components/organisms/StatusTimeline.tsx`，实现状态流转组件：步骤节点圆形 24px，已完成填充中性灰或绿色，当前填充主色，未完成空心浅灰；连线 1px，已完成实线，未完成虚线
  - 修改 `frontend/components/EmptyState.tsx`，使用简洁的线框图标（Outline style），尺寸 64x64px 或 96x96px，颜色 text-tertiary，标题 16px，描述 14px，禁止使用动态插图或鲜艳色彩
  - 确保子需求可独立运行
  - _需求：[FR-007]_

- [x] 8. Dashboard 页面布局与模块整合
  - 修改 `frontend/app/[locale]/admin/dashboard/page.tsx`，重构页面布局
  - 采用 8pt/4pt 基础间距网格系统，页面边距 space-12（48px），模块间距 space-6 或 space-8
  - 首屏顶部展示 4-6 个 KPI 卡片（Critical 告警数、High 告警数、今日新增告警、待处理事件数、平均响应时间、当前风险评分），使用 KpiCard 组件
  - 告警趋势折线图展示最近 7 天数据，Critical/High 使用语义色区分，使用 ChartCard 组件
  - 最新告警表格展示前 5-10 条，包含级别、类型、来源、时间，使用 DataTable 组件
  - 关键安全指标在首屏可见，无需滚动
  - 页面加载状态使用极简骨架屏（Skeleton），禁止使用旋转的菊花 Loading
  - 确保子需求可独立运行
  - _需求：[FR-001, FR-007]_
  - _测试：[Dashboard 页面加载 /api/system/dashboard 接口返回数据正常渲染，KPI 卡片数据与 API 响应一致，图表数据通过 API 获取并正确映射到图表配置]_

- [x] 9. 深色模式映射与主题切换
  - 修改 `frontend/stores/themeStore.ts`，实现基于 CSS 变量或 dark 类名的主题切换机制
  - 修改 `frontend/components/ThemeToggle.tsx`，切换按钮样式与新的设计令牌一致
  - 修改 `frontend/app/[locale]/layout.tsx`，确保根元素支持 dark 类名切换
  - 修改 `frontend/app/globals.css`，定义深色模式背景色层级（页面 `#0f172a`、卡片 `#1e293b`、悬浮 `#334155`、激活 `#475569`），文字色层级（主文字 `#f1f5f9`、次要 `#94a3b8`、辅助 `#64748b`、禁用 `#475569`）
  - 确保图表库适配器监听主题变化并动态更新图表配置
  - 确保所有组件支持 `dark:` 前缀变体
  - 确保子需求可独立运行
  - _需求：[FR-002]_
