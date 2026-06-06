[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
[![Node](https://img.shields.io/badge/Node.js-%3E%3D20-green)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/Python-%3E%3D3.12-blue)](https://python.org/)

AI Agent 驱动的 B站音频播放器。随时随地，想听就听，不止于音乐。

## Features

- **LangGraph ReAct Agent** — LLM 自主决策工具调用，多轮迭代推理，SSE 流式输出
- **双模式切换** — 本地曲库搜索 / B站云端搜索，一键切换
- **B站全链路** — 视频搜索（WBI 签名）→ 转 MP3 下载 → 弹幕叠加播放 → 自动入库知识库
- **分层记忆系统** — 短期（对话）/ 中期（JSONL 历史）/ 长期（用户画像），Dream 引擎自动沉淀
- **LLM-Wiki 知识库** — 基于 Karpathy llm-wiki 方法论，自动消化入库歌曲为结构化知识库
- **场景感知推荐** — 自定义场景（编程/跑步/睡觉等），每个场景独立维护偏好
- **知识库检索子 Agent** — 独立 LangGraph 子图，硬编码检索流程 + 用户画像上下文感知
- **斜杠命令** — 聊天中输入 `/reset-wiki`、`/help` 等管理命令
- **复古终端 UI** — 赛博朋克风格，Atomic Design 组件体系，频谱可视化

## Tech Stack

| 层     | 技术                                              |
| ------ | ------------------------------------------------- |
| 前端   | Next.js 16 (App Router) / React 19 / TypeScript 5 |
| 样式   | Tailwind CSS 4 + CSS Variables                    |
| 后端   | Python FastAPI + LangGraph                        |
| AI     | LangGraph React Agent（OpenAI 兼容 API）          |
| 记忆   | JSONL 历史 + Markdown 用户画像 + Dream 引擎       |
| 知识库 | LLM-Wiki（本地 Markdown wiki + grep 检索）        |

## Architecture

```
┌─────────────────┐     HTTP/SSE      ┌─────────────────────────────────┐
│   Next.js 前端   │ ◄──────────────► │  FastAPI 后端                    │
│   localhost:3002 │                   │  localhost:8000                 │
└─────────────────┘                   └─────────────────────────────────┘
                                              │
                                    ┌─────────┴─────────┐
                                    │   LangGraph Agent  │
                                    │  ┌──────────────┐  │
                                    │  │   AgentNode  │  │
                                    │  │  (LLM 决策)  │  │
                                    │  └──────┬───────┘  │
                                    │         │          │
                                    │  ┌──────▼───────┐  │
                                    │  │   ToolNode   │  │
                                    │  └──────────────┘  │
                                    └─────────────────────┘
                                              │
                          ┌───────────────────┼───────────────────┐
                          ▼                   ▼                   ▼
                   ┌─────────────┐   ┌──────────────┐   ┌──────────────┐
                   │ 本地曲库     │   │ B站云端搜索   │   │ LLM-Wiki     │
                   │ local_search│   │ bili_search  │   │ wiki_search  │
                   └─────────────┘   └──────────────┘   └──────────────┘
                                              │
                                              ▼
                                   ┌──────────────────┐
                                   │  分层记忆系统      │
                                   │  ├ 短期: 对话上下文 │
                                   │  ├ 中期: history   │
                                   │  └ 长期: profile   │
                                   └──────────────────┘
```

## Getting Started

### 前置条件

- Node.js >= 20
- Python >= 3.12（推荐使用 [uv](https://docs.astral.sh/uv/) 管理）
- AI API Key（推荐 [DeepSeek](https://platform.deepseek.com/api_keys)）

### 1. 克隆项目

```bash
git clone https://github.com/pstrm-dev/musicer.git
cd musicer
```

### 2. 配置环境变量

前后端配置已分离，各自读取自己目录下的配置文件：

```env
# frontend/.env — 前端配置（Next.js 自动加载）
BACKEND_URL=http://localhost:8000
MUSIC_DIR=Documents/bili

# backend/.env — 后端配置（Python FastAPI）
OPENAI_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-chat
MUSIC_DIR=Documents/bili
BACKEND_PORT=8000

# backend/.env.local — 后端私密配置（git 自动忽略）
OPENAI_API_KEY=your-api-key-here
```

> 前后端的 `MUSIC_DIR` 需保持一致，指向同一个音乐目录。

### 3. 安装依赖

```bash
# 前端依赖
npm install

# 后端依赖（推荐使用 uv）
cd backend
uv venv .venv --python 3.12
uv pip install -r requirements.txt
cd ..
```

### 4. 启动服务

需要同时运行前后端两个服务（开两个终端窗口）：

**终端 1 — 后端：**

```bash
cd backend
.\.venv\Scripts\python.exe -m uvicorn main:app --reload        # Windows PowerShell
.venv/Scripts/python.exe -m uvicorn main:app --reload           # Git Bash / macOS / Linux
```

**终端 2 — 前端：**

```bash
npm run dev
```

### 5. 打开浏览器

访问 http://localhost:3002

## Port Configuration

| 服务   | 默认端口 | 配置位置                              |
| ------ | -------- | ------------------------------------- |
| 前端   | 3002     | `package.json` → `scripts.dev` 中的 `-p` 参数 |
| 后端   | 8000     | `backend/.env` → `BACKEND_PORT=8000` |

修改前端端口：编辑 `package.json` 中 `dev` 脚本的 `-p` 参数。
修改后端端口：修改 `backend/.env` 中的 `BACKEND_PORT`，重启后端。

## Project Structure

```
Musicer/
├── frontend/                   # Next.js 前端
│   ├── app/                    # Next.js App Router
│   │   ├── api/                # API 路由代理（chat, bili, history, scenarios, wiki...）
│   │   ├── components/         # UI 组件（Atomic Design）
│   │   │   ├── atoms/          # 原子组件
│   │   │   ├── molecules/      # 分子组件
│   │   │   └── organisms/      # 有机体组件
│   │   ├── context/            # React Context 状态管理
│   │   ├── hooks/              # 自定义 Hooks
│   │   └── lib/                # 共享逻辑（API、类型、工具函数）
│   ├── .env                    # 前端环境变量（BACKEND_URL）
│   ├── tsconfig.json
│   ├── next.config.ts
│   └── package.json
├── backend/                    # Python 后端
│   ├── routers/                # API 路由（chat, bili, search, tracks, dream, scenario, wiki, history）
│   ├── services/               # 业务逻辑
│   │   ├── ai_agent.py         # LangGraph Agent（核心）
│   │   ├── bili_client.py      # B站 API 客户端（WBI 签名）
│   │   ├── music_manager.py    # 本地音乐管理
│   │   ├── memory_manager.py   # 分层记忆管理
│   │   ├── dream_engine.py     # Dream 引擎（画像总结）
│   │   ├── scenario_manager.py # 场景管理
│   │   ├── skill_loader.py     # Agent 技能加载器
│   │   ├── wiki_ingest.py      # LLM-Wiki 入库
│   │   ├── wiki_manager.py     # LLM-Wiki 状态管理
│   │   └── system_init.py      # 启动初始化
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置管理
│   ├── .env                    # 后端配置
│   └── .env.local              # 后端私密配置（API Key）
├── skills/                     # Agent 技能（SKILL.md）
│   ├── cloud-search/           # B站云端搜索
│   ├── convert/                # 视频转音频
│   ├── local-search/           # 本地曲库搜索
│   └── slash-commands/         # 斜杠命令（/reset-wiki, /help）
├── memory/                     # 记忆系统
│   ├── template/               # 模板文件
│   └── data/                   # 运行时数据（gitignore）
├── LLM-Wiki/                   # 知识库（gitignore，运行时生成）
├── db/                         # 配置数据
│   └── scenario.yml            # 场景列表
├── package.json                # npm 工作区配置
└── docker-compose.yml
```

## Slash Commands

在聊天中输入 `/命令名` 执行管理操作：

| 命令          | 说明                          |
| ------------- | ----------------------------- |
| `/reset-wiki` | 重置 LLM-Wiki 知识库          |
| `/help`       | 显示所有可用命令              |

扩展新命令：在 `skills/slash-commands/SKILL.md` 中添加命令说明，在 `backend/services/ai_agent.py` 中添加对应的 `@tool` 函数。

## API Endpoints

| 方法 | 路径                                 | 说明                            |
| ---- | ------------------------------------ | ------------------------------- |
| POST | `/api/chat`                        | AI Agent 聊天（SSE 流式响应）   |
| GET  | `/api/search?q=关键词`             | 本地曲库搜索                    |
| GET  | `/api/bili/search?keyword=关键词`  | B站视频搜索                     |
| GET  | `/api/bili/danmaku?bvid=BVxxx`     | 获取视频弹幕                    |
| GET  | `/api/tracks/scan?subDir=20250430` | 扫描指定日期目录                |
| GET  | `/api/tracks/{path}`               | 服务音频文件（支持 Range 请求） |
| POST | `/api/dream/run`                   | 手动触发 Dream 引擎             |
| GET/POST | `/api/scenarios`                 | 场景列表 / 创建场景             |
| DELETE | `/api/scenarios/{name}`           | 删除场景                        |
| GET  | `/api/history`                     | 获取对话历史                    |
| GET  | `/api/wiki/status`                 | LLM-Wiki 状态                   |
| POST | `/api/wiki/init`                   | 初始化 LLM-Wiki                 |
| POST | `/api/wiki/query`                  | LLM-Wiki 检索                   |

## Usage

### 本地模式

搜索 `MUSIC_DIR` 目录下的 MP3 文件。支持按标题、作者、文件名模糊匹配。

### 云端模式

1. 切换到 CLOUD 模式
2. 告诉 AI 你想听什么（如"听周杰伦的演唱会"）
3. AI 在 B站搜索相关视频并推荐
4. 点击 ADD 转换为音频，自动加入播放列表
5. 转换后的音频保存在本地，下次可在本地模式直接搜索

### AI 对话示例

- "推荐一些适合编程的歌" — AI 结合用户画像和知识库推荐
- "播放晴天" — 直接搜索本地/云端并播放
- "我平时喜欢听什么" — 从长期记忆中查询偏好
- "云端搜一首摇滚" — B站搜索 + 自动入库到 LLM-Wiki

## Platform

| 平台    | 支持情况                        |
| ------- | ------------------------------- |
| macOS   | 完全支持                        |
| Linux   | 完全支持                        |
| Windows | 完全支持（Python 后端无需 WSL） |

## Docker

```bash
docker-compose up
```

## License

本项目采用 [CC BY-NC-SA 4.0](LICENSE) 协议。

你可以自由地查看、修改和分享本项目代码，但 **禁止用于商业用途**。衍生作品须以相同协议分发。
