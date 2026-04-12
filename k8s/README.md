# SOC Copilot - Kubernetes Deployment

## Prerequisites

- Kubernetes 1.27+
- kubectl configured
- cert-manager (for TLS)
- NGINX Ingress Controller
- StorageClass for persistent volumes

## Quick Start

```bash
# 1. Update secrets (IMPORTANT!)
# Edit k8s/00-config.yaml and replace CHANGE_ME values

# 2. Create namespace
kubectl apply -f k8s/00-namespace.yaml

# 3. Apply config and secrets
kubectl apply -f k8s/00-config.yaml

# 4. Deploy dependencies first
kubectl apply -f k8s/01-postgres.yaml
kubectl apply -f k8s/02-redis.yaml

# 5. Wait for DB readiness
kubectl -n soc-copilot rollout status statefulset/postgres

# 6. Deploy applications
kubectl apply -f k8s/03-backend.yaml
kubectl apply -f k8s/04-frontend.yaml

# 7. Apply ingress and autoscaling
kubectl apply -f k8s/05-ingress.yaml
kubectl apply -f k8s/06-hpa.yaml

# 8. Verify
kubectl -n soc-copilot get pods
kubectl -n soc-copilot get ingress
```

## Building Images

```bash
# Backend
docker build -t soc-copilot-backend:0.9.0 ./backend

# Frontend
docker build -t soc-copilot-frontend:0.9.0 ./frontend
```

## Configuration

| Parameter           | ConfigMap Key       | Default             | Description         |
| ------------------- | ------------------- | ------------------- | ------------------- |
| DB_USER             | DB_USER             | soc_copilot         | PostgreSQL user     |
| DB_NAME             | DB_NAME             | soc_copilot         | Database name       |
| ENVIRONMENT         | ENVIRONMENT         | production          | Runtime environment |
| NEXT_PUBLIC_API_URL | NEXT_PUBLIC_API_URL | http://backend:8000 | Backend API URL     |

Secrets (must be changed):

| Secret         | Description         |
| -------------- | ------------------- |
| DB_PASSWORD    | PostgreSQL password |
| REDIS_PASSWORD | Redis password      |
| SECRET_KEY     | JWT signing key     |

## Monitoring

```bash
# Check pod health
kubectl -n soc-copilot top pods

# View backend logs
kubectl -n soc-copilot logs -l app=backend -f

# Scale backend manually
kubectl -n soc-copilot scale deployment/backend --replicas=3
```

## Updating

```bash
# Rolling update (zero downtime)
kubectl set image deployment/backend backend=soc-copilot-backend:0.9.1 -n soc-copilot
kubectl rollout status deployment/backend -n soc-copilot

# Rollback if issues
kubectl rollout undo deployment/backend -n soc-copilot
```
