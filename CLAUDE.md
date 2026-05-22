# CLAUDE.md — qianzhu 的 kiro-gateway 项目上下文

> 这份文档是给 AI（Claude Code 或其他 AI 助手）看的。
> 目的：让 AI 在新对话中能立刻理解这个项目是什么、现在在哪个阶段、下一步要做什么，不需要用户重复解释。

---

## 项目是什么

**kiro-gateway** 是一个开源反向代理服务器（Python FastAPI），把 Kiro IDE（Amazon Q Developer / AWS CodeWhisperer）的 API 转换成 OpenAI 和 Anthropic 兼容格式，让 Claude Code、Cursor、Windsurf、Codex 等工具可以直接调用。

- 上游项目：https://github.com/jwadow/kiro-gateway
- 本地路径：`/Users/mac/qianzhu Vault/project/kiro-proxy/kiro-gateway`
- 运行方式：Docker（`docker-compose.yml`），容器名 `kiro-gateway`，端口 8000

---

## qianzhu 的使用目的

**核心目标：用 Kiro 免费/Pro 账号的 token，通过这个 gateway 中转，给 Claude Code 等工具提供免费的 Claude API 访问。**

具体来说：
1. 通过 QQ 群工具（一键换号脚本）获取 Kiro Pro 账号的 refresh token
2. 把 token 配置进 gateway，gateway 负责认证和 API 格式转换
3. Claude Code 等工具指向 `http://localhost:8000`，使用 `qianzhu-kiro-gw-2026` 作为 API key
4. 当账号 token 耗尽或过期，换新号，更新配置，继续使用
5. 长期目标：维护一个号池，多账号自动 failover，减少手动干预

---

## 当前配置状态（2026-05-22）

### 运行状态
- Docker 容器正常运行，健康检查通过
- 已验证 `claude-sonnet-4.6` 可正常调用（新换号账号支持）

### 认证配置
- **模式**：`ACCOUNT_SYSTEM=true`（号池模式，已启用）
- **配置文件**：`credentials.json`（项目根目录）
- **代理**：`VPN_PROXY_URL=http://host.docker.internal:7897`（走本机代理访问 AWS 端点）
- **API Key**：`qianzhu-kiro-gw-2026`

### 当前号池（credentials.json）
- 账号1：2026-05-22 存档，支持 claude-sonnet-4.6（Pro 级别账号）

### 可用模型（实测）
| 模型 | 可用 | 备注 |
|------|------|------|
| claude-sonnet-4.6 | ✅ | 当前主力，接近 Opus 4.6 智能 |
| claude-sonnet-4.5 | ✅ | 免费层可用 |
| claude-sonnet-4 | ✅ | 免费层可用 |
| claude-haiku-4.5 | ✅ | 快速/省 token |
| claude-opus-4.5/4.6/4.7 | 列表有 | 需付费账号 |
| deepseek-3.2、glm-5、minimax 系列、qwen3-coder-next | ✅ | 免费层可用 |

---

## 号池管理流程

### 添加新账号
1. 从 QQ 群工具换号，获取新 refresh token
2. 编辑 `credentials.json`，追加：
```json
{
  "type": "refresh_token",
  "refresh_token": "<新token>",
  "region": "us-east-1",
  "comment": "账号N - YYYY-MM-DD"
}
```
3. `docker restart kiro-gateway`

### 禁用账号（不删除，保留备用）
在对应条目加 `"enabled": false`

### 验证账号是否正常
```bash
curl -s -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer qianzhu-kiro-gw-2026" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-sonnet-4.6","messages":[{"role":"user","content":"hi"}],"max_tokens":20}'
```

### 查看 gateway 日志
```bash
docker logs kiro-gateway --tail 50
```

---

## 号池调度机制（内置，无需手动干预）

- **Sticky**：优先用上次成功的账号
- **Circuit Breaker**：账号失败后指数退避冷却（1分钟 → 最长1天）
- **Failover**：当前账号失败自动切下一个，对调用方透明
- **10% 概率探活**：冷却中的账号有 10% 机会被重试，防止永久卡死

---

## 常见操作

### 重启 gateway
```bash
docker restart kiro-gateway
```

### 查看所有可用模型
```bash
curl -s http://localhost:8000/v1/models \
  -H "Authorization: Bearer qianzhu-kiro-gw-2026" | python3 -m json.tool
```

### 重建镜像（代码有变更时）
```bash
cd "/Users/mac/qianzhu Vault/project/kiro-proxy/kiro-gateway"
docker-compose up -d --build
```

---

## 注意事项

1. **token 有效期**：Kiro refresh token 有效期约数周到数月，过期后 gateway 报 401，需换新号
2. **不要挂港澳节点**：换号时代理节点选其他地区，否则容易封号
3. **credentials.json 不要提交到 git**：里面有真实 token
4. **docker-compose.yml 已挂载 credentials.json**：容器内路径 `/app/credentials.json`，修改宿主机文件后重启生效

---

## 监控面板（2026-05-22 新增）

访问 `http://localhost:8000/stats` 查看实时 dashboard，无需 API key。

功能：
- 今日 / 近7天 / 近30天 token 消耗统计（input + output 分开）
- 每日用量柱状图（近7天）
- 账号池健康状态（Active / Cooling Down、成功率、失败次数）
- 模型纯度检测：高亮非 `claude-*` 模型，确认是否在跑正确模型
- 手动刷新按钮 + 每1小时自动刷新

API 端点：`GET /stats/api` 返回原始 JSON 数据。

Token 统计持久化到 `stats_data.json`（宿主机挂载，重建容器不丢失）。

### 注意：stats_data.json 必须提前创建

首次部署前需在宿主机创建空文件，否则 Docker 会把它当目录挂载：
```bash
echo '{"daily":{}}' > stats_data.json
```

---

## 项目文件结构（关键文件）

```
kiro-gateway/
├── .env                    # 环境变量（含 PROXY_API_KEY、ACCOUNT_SYSTEM=true）
├── credentials.json        # 号池配置（账号列表，不提交 git）
├── state.json              # 运行时状态（自动生成，记录账号健康状态）
├── stats_data.json         # Token 消耗统计（宿主机持久化，重建不丢失）
├── docker-compose.yml      # Docker 配置（已挂载上述三个文件）
├── kiro/
│   ├── config.py           # 所有配置项定义
│   ├── account_manager.py  # 号池核心逻辑（Circuit Breaker、Sticky、Failover）
│   ├── auth.py             # Token 认证和刷新
│   ├── stats_tracker.py    # Token 统计追踪器（单例，每次请求写盘）
│   └── routes_dashboard.py # /stats 面板路由
└── CLAUDE.md               # 本文件
```

---

## AI 助手行为指引

- 用户说"加新账号"→ 帮写入 `credentials.json` 并执行 `docker restart kiro-gateway`
- 用户说"token 过期了"或"gateway 报 401"→ 引导用户提供新 token，更新 `credentials.json`
- 用户说"验证一下"→ 执行上方的 curl 测试命令
- 账号 token 存档在 memory 文件：`~/.claude/projects/.../memory/kiro_account.md`
- 不要把 token 明文输出到对话里，引用时用"账号1 的 token"等描述
