# OnlyOffice 集成配置与部署指南

本项目已支持使用 OnlyOffice Document Server 直接在线编辑模板（保持原始排版样式），本指南说明如何部署 Document Server 并完成与后端/前端的联通配置。

## 1. 核心原理
- 前端在模板编辑页切换到 “OnlyOffice 模式” 后，通过 `/templates/{id}/onlyoffice/config` 获取配置与 `api.js` 地址，并在页面内创建 OnlyOffice DocEditor。
- Document Server 通过下载地址读取原始 DOCX：`{PUBLIC_BASE_URL}{API_PREFIX}/templates/{id}/download`
- 保存时，Document Server 调用回调：`{PUBLIC_BASE_URL}{API_PREFIX}/templates/{id}/onlyoffice/callback`
- 回调会备份原文件、写入新 DOCX，并尝试生成 HTML 快照写入版本历史。

## 2. 环境变量（后端 .env）
```
# 服务对外可访问的完整根地址（供下载/回调使用，建议公网或反代地址）
PUBLIC_BASE_URL=https://your-backend.example.com

# OnlyOffice Document Server 对外地址（前端加载 api.js、DocEditor 所用）
ONLYOFFICE_DOCS_URL=https://docs.example.com

# 如在 Document Server 启用 JWT（推荐），需与其 JWT_SECRET 一致
ONLYOFFICE_JWT_SECRET=replace-with-strong-secret
```
> 说明：`PUBLIC_BASE_URL` 必须是 Document Server 能直接访问到的地址；如果后端在内网，请通过反向代理或内网穿透保证可访问。

## 3. 前端配置
```
VITE_API_BASE_URL=https://your-backend.example.com/api
```
保持与实际访问后端的入口一致。OnlyOffice 模式自动加载 `ONLYOFFICE_DOCS_URL/web-apps/apps/api/documents/api.js`。

## 4. 部署 OnlyOffice Document Server（Docker 示例）
```bash
docker run -d --name onlyoffice-document-server \
  -p 8080:80 \
  -e JWT_ENABLED=true \
  -e JWT_SECRET=replace-with-strong-secret \
  -e JWT_HEADER=Authorization \
  --restart=always \
  onlyoffice/documentserver
```
- 访问 `http://<host>:8080/welcome` 确认服务正常。
- 若使用 HTTPS，请在反向代理层（如 Nginx）配置证书并反代到容器 80 端口。

## 5. 反向代理建议（示例 Nginx 片段）
```nginx
server {
  listen 443 ssl;
  server_name docs.example.com;

  ssl_certificate     /path/to/fullchain.pem;
  ssl_certificate_key /path/to/privkey.pem;

  client_max_body_size 100m;

  location / {
    proxy_pass http://127.0.0.1:8080;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```
确保 `docs.example.com` 与 `.env` 中的 `ONLYOFFICE_DOCS_URL` 匹配。

## 6. JWT 配置对应关系
- Document Server 环境变量：
  - `JWT_ENABLED=true`
  - `JWT_SECRET=<同后端 ONLYOFFICE_JWT_SECRET>`
  - `JWT_HEADER=Authorization`（或 `AuthorizationJwt`，与服务端保持一致）
- 后端 `.env`：`ONLYOFFICE_JWT_SECRET` 必须相同。
- 如未启用 JWT，可将 `JWT_ENABLED=false` 并留空后端 `ONLYOFFICE_JWT_SECRET`，但不推荐用于公网环境。

## 7. 模板字段插件（高亮/占位符下拉）
插件源码位于 `docs/onlyoffice-plugin/template-fields/`，用于在 OnlyOffice 编辑时高亮模板占位符并提供字段下拉替换/插入。

安装到 Document Server（Docker 示例）：
```bash
# 宿主机：将插件目录拷贝到容器内
docker cp docs/onlyoffice-plugin/template-fields onlyoffice-document-server:/var/www/onlyoffice/documentserver/sdkjs-plugins/template-fields

# 容器内：将插件注册到 plugins.json（不存在则新建）
docker exec -it onlyoffice-document-server bash
cd /var/www/onlyoffice/documentserver/sdkjs-plugins
cat plugins.json
# 确保 pluginsData 数组包含：
# "/sdkjs-plugins/template-fields/config.json"

# 重启容器或重启 docservice
exit
docker restart onlyoffice-document-server
```
说明：
- 后端配置会在 `editorConfig.plugins.autostart` 中自动启动插件，并通过 `editorConfig.plugins.options` 传入 `templateId` 与 `apiBaseUrl`。
- 插件使用 Document Server 域名请求后端接口，需确保后端 CORS 包含 `ONLYOFFICE_DOCS_URL` 对应域名（已在 `backend/main.py` 添加）。

## 8. 网络连通性检查
1) 在 Document Server 机器上访问 `curl -I {PUBLIC_BASE_URL}/api/health`，确保可通。
2) 浏览器访问 `{ONLYOFFICE_DOCS_URL}/web-apps/apps/api/documents/api.js`，确认脚本可加载。
3) 登录前端，打开模板编辑页 → OnlyOffice 模式；如加载失败，检查浏览器网络面板中的脚本 200/404/CORS 情况。

## 9. 常见问题
- **回调失败 / 文档未保存**：确认 `PUBLIC_BASE_URL` 可被 Document Server 直接访问；检查后端日志与 Nginx 反代是否放行 POST。
- **JWT 校验错误**：确保 Document Server 与后端的密钥一致，且请求头名称一致。
- **跨域问题**：OnlyOffice 使用自身 iframe，不依赖后端 CORS。前端访问后端仍需在 FastAPI CORS 列表添加前端域名（`backend/main.py`）。
- **样式丢失**：OnlyOffice 直接编辑 DOCX，可最大化保留样式。如需 HTML 模式，请切换到 “HTML 模式”。
- **inspector.js 404 / InvalidStateError**（9.2.x 常见）：刷新静态资源缓存并补一个占位脚本，避免浏览器在加载调试脚本时抛错：
  ```bash
  # 在 Document Server 容器内
  echo 'set $cache_tag "fix1";' > /etc/nginx/includes/ds-cache.conf
  sed -i 's#/9.2.1-[^'\"'']*#/9.2.1-fix1#' /var/www/onlyoffice/documentserver/web-apps/apps/api/documents/api.js
  gzip -c /var/www/onlyoffice/documentserver/web-apps/apps/api/documents/api.js > /var/www/onlyoffice/documentserver/web-apps/apps/api/documents/api.js.gz
  echo '// Inspector disabled' > /var/www/onlyoffice/documentserver/web-apps/apps/debug/inspector.js
  nginx -s reload
  # 验证
  curl -s https://docs.example.com/web-apps/apps/api/documents/api.js | grep 9.2.1-fix1
  curl -I https://docs.example.com/web-apps/apps/debug/inspector.js
  ```
  如容器重建需重跑上述命令，可将其写成宿主机脚本以便快速执行。

## 10. 验证流程
1) 填写 `.env` 并重启后端（或 docker-compose）。
2) 部署/启动 Document Server 并确保对外可访问。
3) 前端设置 `VITE_API_BASE_URL`，重新构建或 `npm run dev`。
4) 打开模板 → OnlyOffice 模式，修改并在工具栏点击保存，预期：
   - 后端 `storage/templates/<id>_*.docx` 被更新；
   - 版本历史新增一条 “OnlyOffice 保存” 记录。
