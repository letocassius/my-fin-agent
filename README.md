# my-fin-agent

一个基于 OpenAI、FastAPI、React 和本地 RAG 的金融问答系统，支持股票行情类问题与金融知识类问题的统一入口查询。

## 项目概述

系统目标是把两类常见金融问答能力放在一个轻量全栈应用中：

- 市场类问题：查询股票价格、走势、技术指标、财务报表、相关新闻
- 知识类问题：基于本地知识库回答金融概念、技术分析、财报阅读等问题

前端提供聊天式交互界面，后端负责意图路由、工具调用、RAG 检索与答案生成。

## 系统架构图

```text
┌──────────────────────────────────────────────────────────────┐
│                      Frontend (React)                       │
│  ChatInterface                                              │
│  - 输入问题                                                  │
│  - 渲染回答 / 数据卡片 / 错误状态                            │
│  - 调用 POST /api/query                                     │
└───────────────────────────────┬──────────────────────────────┘
                                │ HTTP / JSON
┌───────────────────────────────▼──────────────────────────────┐
│                      Backend (FastAPI)                      │
│  /api/query                                                 │
│  /api/health                                                │
│  /api/providers                                             │
└───────────────────────────────┬──────────────────────────────┘
                                │
                     ┌──────────▼──────────┐
                     │   Query Router      │
                     │   OpenAI 分类意图    │
                     └───────┬───────┬─────┘
                             │       │
                    market   │       │ knowledge
                             │       │
        ┌────────────────────▼─┐   ┌─▼────────────────────────┐
        │ Market Agent         │   │ RAG Pipeline             │
        │ OpenAI + tool calls  │   │ ChromaDB 相似度检索       │
        │                      │   │ OpenAI 生成 grounded 回答 │
        └───────┬──────────────┘   └──────────┬───────────────┘
                │                             │
     ┌──────────▼──────────┐         ┌────────▼───────────────┐
     │ Market Data Sources │         │ Local Knowledge Base   │
     │ - yfinance          │         │ backend/knowledge_base │
     │ - Finnhub(optional) │         │ *.md / *_zh.md         │
     └─────────────────────┘         └────────────────────────┘
```

## 技术选型说明

### 前端

- React 19 + TypeScript
  - 适合构建聊天式单页应用，组件划分清晰，类型约束对接口联调更稳
- Vite
  - 本地开发启动快，适合这种前后端分离的小型项目
- Tailwind CSS
  - 当前 UI 是命令行风格聊天界面，Tailwind 更适合快速控制细粒度样式

### 后端

- FastAPI
  - 天然适合构建 JSON API，类型声明清晰，接口调试效率高
- Pydantic
  - 用于约束请求和响应结构，减少接口层面的隐式错误
- Uvicorn
  - 作为本地开发服务启动简单，和 FastAPI 配合自然

### 模型与智能层

- OpenAI Chat Completions
  - 用于查询分类、市场问答生成、知识问答生成
- OpenAI Embeddings
  - 用于知识库文档向量化，构建本地 RAG 检索能力
- LangChain（`langchain-openai`、`langchain-community`）
  - 知识 Agent 使用 LCEL（LangChain Expression Language）链式调用：`ChatPromptTemplate | ChatOpenAI | StrOutputParser`
  - RAG 使用 `MarkdownHeaderTextSplitter` + `RecursiveCharacterTextSplitter` + `Chroma` 向量库封装

### 数据层

- yfinance
  - 无需 API key，适合快速提供价格、历史走势、基础财务字段等数据
- Finnhub
  - 作为可选增强数据源，用于补充更丰富的新闻与基础财务数据
- ChromaDB
  - 本地持久化向量库，适合当前单机演示和开发场景

## Prompt 设计思路

系统中核心 Prompt 分为三类。

### 1. Router Prompt

目标是把用户问题稳定分类为：

- `market`
- `knowledge`

设计重点：

- 强调意图分类优先于自由生成
- 输出结构化 JSON，便于后端稳定解析
- 抽取可能的 `ticker` 与 `period`
- 对“公司走势/价格”和“概念解释类问题”做明确边界约束

这样做的原因是：路由是整个系统的第一道分流，如果分类不稳定，后续工具调用或 RAG 都会偏离。

### 2. Market Agent Prompt

目标是让模型在市场类问题中主动调用工具，而不是仅凭参数记忆回答。

设计重点：

- 明确允许调用的工具集合（5 个）：`get_stock_price`、`get_price_history`、`get_technical_indicators`、`get_financial_statements`、`search_news`
- 要求把”数据事实”和”分析判断”分开输出（`## DATA` / `## ANALYSIS` 格式）
- 限制模型在缺少数据时胡乱推断
- 让模型优先基于工具结果组织答案，而不是脱离结果自由发挥
- 支持 `parallel_tool_calls`，多个工具可并行执行

这样可以降低金融问答中最常见的问题：把模型印象当成实时市场数据。

### 3. Knowledge Agent Prompt

目标是让模型只基于检索到的知识片段回答。

设计重点：

- 明确要求 grounded answer
- 没有命中的信息时拒绝编造
- 保留来源信息，方便前端展示 `sources`
- 通过 LangChain LCEL（`ChatPromptTemplate | ChatOpenAI | StrOutputParser`）构建推理链

这类 Prompt 的核心不是”写得更聪明”，而是把可回答范围收窄，确保知识型问答可解释。

## 数据来源说明

### 1. 市场数据来源

主数据源是 `yfinance`：

- 当前价格
- 涨跌幅
- 成交量
- 市值
- 历史 K 线 / OHLCV
- 部分基础财务字段

可选增强数据源是 `Finnhub`：

- 公司新闻
- 基础财务指标
- EPS 等补充字段

当前实现里，`Finnhub` 不是必需项，未配置 API key 时系统仍可运行。

### 2. 知识数据来源

知识问答的数据来自本地 Markdown 文档，路径为 [`backend/knowledge_base`](./backend/knowledge_base)。

当前包括中英文主题文档，例如：

- `financial_basics.md`
- `technical_analysis.md`
- `earnings_reports.md`
- `market_concepts.md`
- 对应的 `_zh.md` 中文版本

这些文档会在后端启动时自动进行：

1. SHA-256 manifest 变更检测（无变更则跳过重建）
2. LangChain `MarkdownHeaderTextSplitter` 按标题结构切块
3. `RecursiveCharacterTextSplitter` 二次切块，chunk_size ≈ 2000 字符（~500 tokens），overlap ≈ 200 字符
4. LangChain `OpenAIEmbeddings` 向量化并写入 ChromaDB（支持确定性 ID upsert）
5. 查询时相似度检索，cosine distance > 0.7 的低相关 chunk 自动过滤
6. 支持语言元数据过滤（中文问题优先检索 `_zh.md` 文档）

### 3. 配置数据来源

环境变量定义在 [`backend/.env.example`](./backend/.env.example) 中，核心包括：

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `EMBEDDING_MODEL`
- `FINNHUB_API_KEY`
- `ALPHA_VANTAGE_API_KEY`

其中 `ALPHA_VANTAGE_API_KEY` 目前保留为扩展位，尚未成为主流程的一部分。

## 接口说明

后端主要接口：

- `GET /`
- `GET /api/health`
- `GET /api/providers`
- `POST /api/query`

示例请求：

```json
{ "query": "How has Tesla performed this year?" }
```

示例响应结构：

```json
{
  "answer": "...",
  "data_section": "...",
  "analysis_section": "...",
  "sources": ["Yahoo Finance (yfinance)"],
  "query_type": "market",
  "ticker": "TSLA",
  "latency_ms": 2140.8
}
```

## 本地运行方式

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

至少需要配置：

```bash
OPENAI_API_KEY=your_key_here
```

### Frontend

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

可选配置：

```bash
VITE_API_URL=http://127.0.0.1:8000
```

未配置时默认请求 `http://localhost:8000`。

### 一键启动

根目录已提供：

```bash
./start.sh
./stop.sh
./restart.sh
```

其中：

- 后端默认启动在 `127.0.0.1:8000`
- 前端默认启动在 `127.0.0.1:5173`
- 日志写入 `.run/` 目录

## 优化与扩展思考

### 1. 路由层优化

当前路由依赖单次 LLM 分类，优点是实现简单，缺点是边界问题仍可能误判。可优化方向：

- 增加规则层预判，例如 ticker / price / earnings 等关键词快速路由
- 对模糊问题引入二次确认或多标签分类
- 记录误分类样本，反向优化 Router Prompt

### 2. 市场数据能力扩展

当前以 `yfinance` 为主，适合开发与演示，但不适合强实时要求场景。可扩展为：

- 引入 Alpha Vantage / Polygon / Finnhub 等多源聚合
- 增加失败回退和数据一致性校验
- 对新闻做时间排序、情绪分析和事件抽取

### 3. RAG 能力优化

当前知识库规模较小，本地 ChromaDB 足够；如果知识库继续扩展，可考虑：

- 更细粒度 chunk 策略
- reranking 提升召回质量
- 文档级元数据过滤，例如按语言、主题、版本过滤
- 引入增量更新机制，而不是仅靠全量重建

### 4. 前端交互优化

目前前端已经支持基本聊天流，但仍可继续增强：

- 支持流式输出
- 支持历史会话持久化
- 支持图表展示历史价格和技术指标
- 对 market / knowledge 两类回答做更明确的可视化分区

### 5. 工程化与部署优化

当前项目适合本地开发。若走向稳定部署，可继续补齐：

- Docker 化
- CI 测试与 lint 流程
- 更完整的异常监控与日志采集
- API 鉴权与限流
- 生产环境配置分层

## 测试

后端：

```bash
cd backend
source .venv/bin/activate
pytest
```

前端：

```bash
cd frontend
npm run lint
npm run build
```
