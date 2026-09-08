# 性能基线（Performance Baseline）

> 测量时间：2026-09-08，开发机（macOS arm64），后端 uvicorn --reload 单进程 + SQLite，
> 前端 Next.js dev。生产（PG + 4 workers）预期显著优于以下数字；本基线用于回归对比而非容量证明。

## 负载基准（backend/scripts/load_baseline.py，20s × 10 并发）

| 端点 | 样本数 | P50 | P95 | P99 | 错误 |
| -- | --: | --: | --: | --: | --: |
| GET /api/v1/health | 956 | 121ms | 205ms | 310ms | 0 |
| GET /api/v1/assets?limit=50 | 956 | 32ms | 100ms | 146ms | 0 |
| GET /api/v1/dashboard/stats | 956 | 28ms | 92ms | 164ms | 0 |

**合计 2868 请求，142.5 RPS，0 错误。** 业务查询 P95 < 105ms——远低于 1s 的 API 超时配置。

## 前端 Bundle（Next.js 16 production build）

- 静态资源总量：**4.2 MB**（134 个 chunk，含按路由代码分割）
- 构建时间：约 3.2s 编译 + 75 个静态页面生成 < 200ms
- 构建命令：`npm run build`（零错误、零警告）

## 运行时行为

- AI chat 真实流式：首 token 延迟 ≈ 1-3s（NVIDIA 端点），逐 token 增量
- 熔断器：5 次失败 → 熔断 30s；LLM 重试指数退避封顶
- 执行队列：playbook 并发上限 3（RUN_QUEUE_MAX）

## 复测方法

```bash
cd backend && ../venv/bin/python scripts/load_baseline.py 20 10
cd frontend && npm run build && du -sh .next/static
```

对比历史数据，P95 劣化 >50% 或出现错误时定位慢查询（EXPLAIN QUERY PLAN）与新增依赖。
