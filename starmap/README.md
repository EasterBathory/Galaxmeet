# 星野选点 · 部署说明

## 目录结构
```
starmap/
├── backend/      FastAPI 后端
└── frontend/     前端单页 HTML
```

## 后端启动

```bash
cd starmap/backend

# 1. 复制环境变量
cp .env.example .env
# 编辑 .env，填入 MySQL / 阿里云短信 / Papago / JWT_SECRET

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动（开发）
uvicorn main:app --reload --port 8000

# 4. 启动（生产，推荐用 gunicorn）
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 前端部署

直接用任意静态服务器托管 `frontend/index.html`。

开发时可用 VS Code Live Server 或：
```bash
python -m http.server 5500 --directory starmap/frontend
```

生产环境建议用 Nginx：
```nginx
server {
    listen 80;
    root /var/www/starmap/frontend;
    index index.html;
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }
}
```

## 环境变量说明

| 变量 | 说明 |
|------|------|
| DB_HOST/PORT/USER/PASSWORD/NAME | MySQL 连接信息 |
| JWT_SECRET | 随机长字符串，用于签发 Token |
| ALI_ACCESS_KEY_ID/SECRET | 阿里云 RAM 子账号 AK |
| ALI_SMS_SIGN | 短信签名（需在阿里云审核通过） |
| ALI_SMS_TEMPLATE | 短信模板 CODE（如 SMS_xxxxxxx） |
| PAPAGO_CLIENT_ID/SECRET | Naver Cloud Platform 申请 |
| AMAP_KEY | 高德 REST API Key |
| FRONTEND_ORIGIN | 前端地址，用于 CORS（如 https://yourdomain.com） |

## Papago 申请

1. 注册 [Naver Cloud Platform](https://www.ncloud.com/)
2. 控制台 → AI·NAVER API → Papago Translation → 申请
3. 将 Client ID 和 Client Secret 填入 .env
