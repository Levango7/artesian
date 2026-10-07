# artesian

自流井——接通即涌的取数/知识底座。

从 doc-pipeline 抽离的独立库：JSON 序列化、HTML 解析后端兼容层、
嵌入层、知识库与搜索引擎统一接口。第三波（search_engines）落地后，
先前规划的迁出边界（fast_json / selectolax_compat / embeddings /
knowledge_base / search_engines）已全部在这里。

## 模块

| 模块 | 职责 |
|---|---|
| `fast_json` | orjson 优先、标准库回退的 JSON 序列化（`dumps` / `loads` / `dumps_bytes` / `HAS_ORJSON`） |
| `selectolax_compat` | selectolax 内核（modest/lexbor）探测与显式降级（`resolve_backend` / `get_parser` / `requested_backend`） |
| `embeddings` | 文本 → 稠密向量：hash（内置兜底）/ local（sentence-transformers）/ api（OpenAI 兼容）三后端，按可用性自动选并如实记录降级原因，含离线探测保护 |
| `knowledge_base` | 文档切块（结构感知）→ 向量化 → SQLite 持久化 → 暴力余弦检索；含换嵌入器的向量空间保护与重建 |
| `search_engines` | 10 个引擎统一接口（API：bocha/tavily/serper/metaso；HTML：bing/baidu/sogou/360；另 duckduckgo、prosearch、mock 桩），失败自动 fallback、结果标准化、跨查询 LRU+TTL 缓存、Firecrawl 网页提取；异步路径需 `.[search]` |
| `cache` | 进程内线程安全 LRU+TTL（`LRUCache`），TTL 三档语义见模块 docstring |
| `env` | `.env` 读取与系统环境合并（`load_env`），搜索层与消费方路由层共用同一实现 |

## 安装

```
pip install -e ".[html,dev]"        # 本地语义嵌入（local 后端）另加 .[embed]
                                    # API 引擎的异步 search_async 另加 .[search]
```

`prosearch` 引擎需要宿主上的 Node 脚本，库里不内置任何机器路径：
`PROSEARCH_PATH` 给单条、`ARTESIAN_PROSEARCH_PATHS` 给 os.pathsep 分隔的候选、
`ProSearchEngine(script_paths=[...])` 由调用方注入。

## 兼容承诺

以下符号视为公开 API，0.x 内不做破坏性变更。doc-pipeline 是当前唯一消费方：

- `artesian.fast_json`：`dumps`、`loads`、`dumps_bytes`、`HAS_ORJSON`
- `artesian.selectolax_compat`：`resolve_backend`、`requested_backend`、`get_parser`、`MODULES`、`ENV_OVERRIDE`
- `artesian.embeddings`：`extract_features`、`Embedder`、`HashEmbedder`、`LocalEmbedder`、`APIEmbedder`、`available_embedders`、`auto_fallback_reasons`、`model_is_cached`、`get_embedder`、`pack_vector`、`unpack_vector`、`cosine`、`DEFAULT_HASH_DIM`、`DEFAULT_LOCAL_MODEL`
- `artesian.knowledge_base`：`KnowledgeBase`、`chunk_markdown`、`DEFAULT_DB`、`DEFAULT_CHUNK_CHARS`、`DEFAULT_CHUNK_OVERLAP`
- `artesian.search_engines`：`SearchItem`、`SearchEngineBase`、`SearchEngineManager`、`create_engine`、`MockEngine`、`BochaEngine`、`TavilyEngine`、`SerperEngine`、`MetasoEngine`、`DuckDuckGoEngine`、`HtmlSearchEngine`、`BingEngine`、`BaiduEngine`、`SogouEngine`、`So360Engine`、`ProSearchEngine`、`FirecrawlExtractor`
- `artesian.cache`：`LRUCache`
- `artesian.env`：`load_env`

其中 doc-pipeline 产品代码与测试实际引用：`fast_json.dumps` / `loads`、
`selectolax_compat` 全部条目、`embeddings` 的 `get_embedder` / `available_embedders` /
`auto_fallback_reasons` / `model_is_cached` / `LocalEmbedder` / `Embedder` / `cosine` /
`pack_vector` / `unpack_vector`（含实例面 `embed` / `embed_one` / `dim` / `name`）、
`knowledge_base` 的 `KnowledgeBase` / `chunk_markdown`、
`search_engines` 的 `SearchEngineManager` / `FirecrawlExtractor`（产品码）与
`SearchItem` / `create_engine` / `_ENGINE_REGISTRY` / 各引擎类（判据），
`env.load_env`（`llm_router._load_env` 现为它的别名）
（2026-10-07 按引用点实测；`dumps_bytes` / `HAS_ORJSON` / `HashEmbedder` / `APIEmbedder` /
`cache.LRUCache` 等其余条目为库完整 API 的一部分）。

注：`selectolax_compat._load` 是私有实现，但消费方测试直接引用它做探测断言
（`MODULES` × `_load`），重命名时必须同步两仓；如有真实外部需求再提升为公开。

## 测试

**248 个测试本机全绿**（2026-10-07 本机实测：`247 passed, 1 skipped`——orjson 回退
模拟用例在装有 orjson 时按设计跳过；`python -m pytest tests/ -q`）
