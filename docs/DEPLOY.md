# DEPLOY — 国内 Demo 部署

## 1. 本地运行

```bash
cp .env.example .env
docker-compose up --build
```

- 前端：http://localhost:3000
- 后端：http://localhost:8000
- MCP：http://localhost:8100

## 2. 阿里云轻量服务器

1. 开放安全组：80、3000、8000、8100。
2. 安装 Docker 与 Docker Compose。
3. 设置 `.env` 中 `OPENAI_API_KEY`（DeepSeek Key）与 `OPENAI_BASE_URL=https://api.deepseek.com/v1`。
4. 执行 `docker-compose up -d --build`。
5. 可选：Nginx 反向代理到前端与 API。

## 3. 故障排查

- DeepSeek 调用失败：检查 `OPENAI_API_KEY` / `OPENAI_BASE_URL`，系统会自动使用模拟兜底以保证演示不断。
- 前端无法连接后端：检查 `VITE_API_BASE`。
- GPU 显存不足：调小 `finetune/config.yaml` 的 batch size，启用 4-bit QLoRA。
- Docker 构建失败：检查镜像源和网络。
