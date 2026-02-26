# 部署与运维

## 适用对象

运维工程师、SRE、需要部署/维护系统的管理员。

## 目标

掌握开发环境部署、Docker 部署、生产环境配置。

## 本地部署

```bash
# 后端
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd frontend
npm install
npm run dev
```

## Docker 部署

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///data/app.db
      - OTX_API_KEY=${OTX_API_KEY}
    volumes:
      - ./data:/app/data
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "3003:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - frontend
      - backend
```

### 构建部署

```bash
docker-compose build
docker-compose up -d
docker-compose logs -f
```

## 生产环境建议

### HTTPS 配置

```bash
certbot --nginx -d soc.company.com
```

### 备份策略

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)

# 备份数据库
sqlite3 data/app.db ".backup backup/app.db.$DATE"

# 备份配置
tar -czf backup/config.$DATE.tar.gz .env*

# 上传到对象存储
aws s3 cp backup/ s3://soc-backup/ --recursive

# 保留最近 7 天
find backup -name "*.db.*" -mtime +7 -delete
```

### PostgreSQL 迁移（可选）

```bash
pip install asyncpg psycopg2-binary

# 修改配置
DATABASE_URL=postgresql://user:pass@localhost:5432/soc_copilot
```
