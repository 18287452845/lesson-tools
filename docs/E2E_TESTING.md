# 端到端测试指南

## Chrome DevTools MCP 无头浏览器配置

本项目已配置 Chrome DevTools MCP 在无头模式下进行自动化测试。

### 配置详情

- **模式**: 无头浏览器（Headless）
- **视口大小**: 1920x1080
- **隔离环境**: 启用（自动清理临时文件）
- **配置文件**: `.mcp.json`（项目级）、`~/.claude.json`（本地级）

### 快速验证

检查 MCP 服务器状态：

```bash
# 列出所有 MCP 服务器
claude mcp list

# 查看 Chrome DevTools 详细配置
claude mcp get chrome-devtools
```

### 使用 Claude Code 进行自动化测试

您可以直接与 Claude Code 交互来执行浏览器自动化任务：

#### 示例 1：测试前端页面加载

```
> "打开无头浏览器，访问 http://localhost:5173，等待页面加载完成后截图"
```

#### 示例 2：测试模板上传功能

```
> "使用无头浏览器测试模板上传功能：
   1. 访问 http://localhost:5173/templates
   2. 点击上传按钮
   3. 检查页面是否正确显示
   4. 截图保存结果"
```

#### 示例 3：端到端课程生成测试

```
> "执行完整的课程生成流程测试：
   1. 访问首页
   2. 导航到新建课程页
   3. 填写课程信息表单
   4. 提交生成请求
   5. 验证生成结果
   6. 检查控制台是否有错误"
```

#### 示例 4：批量生成功能测试

```
> "测试批量生成功能：
   1. 访问批量生成页面
   2. 填写课程信息和章节数量
   3. 提交任务
   4. 监控任务进度
   5. 验证 ZIP 下载功能"
```

### Python 测试脚本集成

虽然主要通过 Claude Code 交互进行测试，但您也可以编写 pytest 测试脚本：

```python
# backend/tests/test_e2e_browser.py
import pytest
import asyncio
from pathlib import Path

class TestE2EWithBrowser:
    """使用 Claude Code + 无头浏览器的端到端测试"""

    @pytest.mark.asyncio
    async def test_frontend_loads(self):
        """测试前端页面加载"""
        # 通过 Claude Code 执行浏览器测试
        # 实际执行通过 MCP 协议完成
        pass

    @pytest.mark.asyncio
    async def test_template_upload_workflow(self):
        """测试模板上传完整流程"""
        pass

    @pytest.mark.asyncio
    async def test_lesson_generation_e2e(self):
        """测试课程生成端到端流程"""
        pass
```

### 调试和日志

启用详细日志（如需调试）：

```bash
# 修改 .mcp.json，添加 DEBUG 环境变量
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": [...],
      "env": {
        "DEBUG": "chrome-devtools-mcp:*"
      }
    }
  }
}
```

### 性能分析

使用无头浏览器进行性能测试：

```
> "访问 http://localhost:5173，记录网络请求，分析页面加载性能"
```

### 截图和快照

所有截图和快照都会自动保存到临时目录，Claude Code 会展示给您。

### 常见问题

**Q: 如何在 CI/CD 环境中使用？**

A: 确保 CI 环境安装了 Node.js 和 Chrome/Chromium：

```yaml
# GitHub Actions 示例
- name: Install Chrome
  run: |
    sudo apt-get update
    sudo apt-get install -y chromium-browser

- name: Run E2E tests
  run: |
    export CHROME_PATH=/usr/bin/chromium-browser
    claude mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest --headless=true
```

**Q: 如何切换回可视模式？**

A: 移除 `--headless=true` 参数：

```bash
claude mcp remove chrome-devtools -s local
claude mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest --viewport 1920x1080
```

**Q: 无头浏览器启动失败？**

A: 检查系统是否缺少依赖：

```bash
# Ubuntu/Debian
sudo apt-get install -y \
  libnss3 \
  libatk1.0-0 \
  libatk-bridge2.0-0 \
  libcups2 \
  libdrm2 \
  libxkbcommon0 \
  libxcomposite1 \
  libxdamage1 \
  libxrandr2 \
  libgbm1 \
  libasound2
```

### 相关文档

- [Chrome DevTools MCP 官方文档](https://github.com/ChromeDevTools/chrome-devtools-mcp)
- [Claude Code MCP 文档](https://code.claude.com/docs/en/mcp.md)
- [项目 README](../README.md)

### 更新配置

如需修改配置：

```bash
# 方法 1: 直接编辑配置文件
nano /opt/prj/lesson-tools/.mcp.json

# 方法 2: 移除并重新添加
claude mcp remove chrome-devtools -s local
claude mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest [新参数]
```

### 最后更新

配置日期: 2026-01-09
MCP 版本: chrome-devtools-mcp@latest
