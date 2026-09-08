# SOC Copilot SRE Runbook: 容量规划与弹性扩缩容基线 (Capacity Planning)

## 1. 架构基线与评估指标
- **当前业务量级**：每天 100,000+ 安全告警事件，50+ 并发 SOC 分析师在线协作
- **核心组件**：FastAPI ASGI 服务集群、Next.js 16 SSR/CSR 前端、Redis 7.2 集群、PostgreSQL 15 主从

---

## 2. 容器资源规格推荐基线 (Resource Allocation)

| 服务组件 | 容器副本数 | 最小请求 (Requests) | 最大配额 (Limits) | 扩容指标触发阈值 (HPA Metric) |
| :--- | :---: | :---: | :---: | :--- |
| **Backend API** | 2 ~ 6 Pods | 1.0 Core CPU, 1Gi RAM | 2.0 Core CPU, 2Gi RAM | CPU > 70% 或活跃连接数 > 500 |
| **Alert Worker** | 2 ~ 4 Pods | 0.5 Core CPU, 512Mi RAM| 1.5 Core CPU, 1Gi RAM | Redis Stream 积压量 > 1,000 条 |
| **Frontend SSR** | 2 ~ 4 Pods | 0.5 Core CPU, 512Mi RAM| 1.0 Core CPU, 1Gi RAM | HTTP 请求 QPS > 200/Pod |
| **PostgreSQL** | 1 主 1 备 | 2.0 Core CPU, 4Gi RAM | 4.0 Core CPU, 8Gi RAM | 连接池利用率 > 80% |
| **Redis** | 1 主 1 从 | 1.0 Core CPU, 2Gi RAM | 2.0 Core CPU, 4Gi RAM | 内存使用率 > 75% |

---

## 3. ASGI Uvicorn 并发工作进程配置

根据物理/虚拟机 CPU 核心数推导最佳进程数：
$$\text{Workers} = (2 \times \text{CPU Cores}) + 1$$

在容器化 Kubernetes 环境中，建议**单容器单主进程 (1 Worker per Pod)**，通过 **HPA (Horizontal Pod Autoscaler)** 横向扩容 Pod 副本数：

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: soc-backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: soc-copilot-backend
  minReplicas: 2
  maxReplicas: 8
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## 4. 数据库连接池与连接限制模型

- **SQLAlchemy 异步连接池参数** (`backend/db/session.py`)：
  - `pool_size`: 20
  - `max_overflow`: 10
  - `pool_timeout`: 30 秒
- **PostgreSQL `max_connections` 测算**：
  $$\text{MaxConnections} \ge (\text{Backend Replicas} \times 30) + (\text{Worker Replicas} \times 10) + 20 \text{ (Admin/Migration)}$$
  以 6 个 Backend + 4 个 Worker 预留：至少需要 $6 \times 30 + 4 \times 10 + 20 = 240$ 最大连接数。
