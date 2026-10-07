# artesian

自流井——接通即涌的取数/知识底座。

从 doc-pipeline 抽离的独立库：JSON 序列化、HTML 解析后端兼容层、嵌入层、知识库、
搜索引擎统一接口，外加它们共用的三件底座（`cache` / `env` / `url_guard`）。

规划的迁出边界（`fast_json` / `selectolax_compat` / `embeddings` /
`knowledge_base` / `search_engines`）已全部落地；之后又把 `url_guard` 一起归位——
搜索层出网要用它做 SSRF 校验，留在消费方就成了"库回头够本仓"的反向耦合。

当前发布 **v0.1.0**（GitHub Release）。尚未上 PyPI，消费方按提交直接引用安装，
所以库侧每次改动都要由消费方更新那个提交号——这不是疏忽，是未发布的代价。

## 模块

| 模块 | 职责 |
|---|---|
| `fast_json` | orjson 优先、标准库回退的 JSON 序列化（`dumps` / `loads` / `dumps_bytes` / `HAS_ORJSON`） |
| `selectolax_compat` | selectolax 内核（modest/lexbor）探测与显式降级（`resolve_backend` / `get_parser` / `requested_backend`） |
| `embeddings` | 文本 → 稠密向量：hash（内置兜底）/ local（sentence-transformers）/ api（OpenAI 兼容）三后端，按可用性自动选并如实记录降级原因，含离线探测保护 |
| `knowledge_base` | 文档切块（结构感知）→ 向量化 → SQLite 持久化 → 暴力余弦检索；含换嵌入器的向量空间保护与重建 |
| `search_engines` | 10 个引擎统一接口（API：bocha/tavily/serper/metaso；HTML：bing/baidu/sogou/360；另 duckduckgo、prosearch、mock 桩），失败自动 fallback、结果标准化、跨查询 LRU+TTL 缓存、Firecrawl 网页提取；异步路径需 `.[search]`。出网都走 `url_guard`（重定向逐跳复验），Firecrawl 的**目标 URL 视为不可信输入**先校验再发 |
| `cache` | 进程内线程安全 LRU+TTL（`LRUCache`），TTL 三档语义见模块 docstring |
| `env` | `.env` 读取与系统环境合并（`load_env`），搜索层与消费方路由层共用同一实现 |
| `url_guard` | SSRF 校验（`validate_public_http_url`）：仅 http/https，拒私网/保留/链路本地/组播/`localhost`，域名解析全部 A/AAAA 逐条判定；解析结果带 TTL 正/负缓存（300s/60s），策略判定不入缓存 |

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
- `artesian.url_guard`：`validate_public_http_url`、`clear_dns_cache`

其中 doc-pipeline 产品代码与测试实际引用：`fast_json.dumps` / `loads`、
`selectolax_compat` 全部条目、`embeddings` 的 `get_embedder` / `available_embedders` /
`auto_fallback_reasons` / `model_is_cached` / `LocalEmbedder` / `Embedder` / `cosine` /
`pack_vector` / `unpack_vector`（含实例面 `embed` / `embed_one` / `dim` / `name`）、
`knowledge_base` 的 `KnowledgeBase` / `chunk_markdown`、
`search_engines` 的 `SearchEngineManager` / `FirecrawlExtractor`（产品码）与
`SearchItem` / `create_engine` / `_ENGINE_REGISTRY` / 各引擎类（判据），
`env.load_env`（`llm_router._load_env` 现为它的别名）、
`url_guard.validate_public_http_url`（fetcher / http_request / event_hook 三处产品码，
库内搜索层也用它做逐跳复验；`clear_dns_cache` 只有本库判据与运行时刷新用）
（2026-10-07 按引用点实测；`dumps_bytes` / `HAS_ORJSON` / `HashEmbedder` / `APIEmbedder` /
`cache.LRUCache` 等其余条目为库完整 API 的一部分）。

注：`selectolax_compat._load` 是私有实现，但消费方测试直接引用它做探测断言
（`MODULES` × `_load`），重命名时必须同步两仓；如有真实外部需求再提升为公开。

## 测试

**317 个测试本机全绿**（2026-10-08 本机实测：`316 passed, 1 skipped`——orjson 回退
模拟用例在装有 orjson 时按设计跳过；`python -m pytest tests/ -q`）。
其中 `tests/test_verify_dist.py` 是**发布门禁自己的判据**：8 条里有 7 条反向对照
（版本对不上／wheel 少 `py.typed`／新模块没进包／sdist 缺 README／产物多于一个／
dist 为空／空串版本参数），空串那条是 2026-10-08 干跑抓到并修掉的真 bug。

## 发布（PyPI）

流水线在 `.github/workflows/release.yml`：**只在 GitHub Release 被"published"时才真上传**，
误推 tag 不会发包。要干跑就 `workflow_dispatch`（默认 `dry_run=true`，只构建与校验）。

`verify` 这一步跑四件事，任何一件不过就不会上传：

1. `python -m build` 出 sdist + wheel；
2. `tools/verify_dist.py dist <tag 版本>`：产物文件名 / `pyproject` 的 version /
   装好之后的 `__version__` 与包元数据四处必须相等；wheel 内容必须与 `src/artesian/`
   **逐个文件对齐**（新增模块忘了进包会当场红）；`py.typed` 必须在 wheel 与 sdist
   里都在——它丢了消费方 mypy 不报错，只会静默退化成 `Any`；
3. `twine check --strict`；
4. **把 wheel 装进干净 venv，再从仓库外面跑一遍测试**（源码全绿不代表 wheel 里那份能用）。

`publish` 用 Trusted Publishing（OIDC），**仓库里不存长期 token**；它搬运 `verify`
那份产物字节，不重新构建。

### 一次性配置（缺这一步，publish 会红）

1. PyPI 上确认包名 `artesian` 归你（2026-10-07 实测该名字未被占用，返回 404）；
   若需要，先在 PyPI 建 project（可不传包，只占名）。
2. PyPI → 该 Project → **Publishing → Trusted Publisher**：
   provider 选 GitHub，仓库 `Levango7/artesian`，
   workflow 名 `release.yml`，environment 填 `pypi`（与流水线里的
   `environment: pypi` 必须逐字一致；不填就选"不绑定 environment"）。
3. GitHub → Settings → Secrets and variables → Actions → Environments → 新建 `pypi`；
   想要人工闸门就勾 "Required reviewers"（发布时会等你批准）。

### 每次发版

```bash
# 1. 先改版本号，再打 tag——顺序反了会被上面第 2 条判红
python - <<'PY'
import pathlib, re
p = pathlib.Path("pyproject.toml")
p.write_text(re.sub(r'^version = ".*"', 'version = "0.1.1"',
                    p.read_text(encoding="utf-8"), count=1, flags=re.M), encoding="utf-8")
PY
git commit -am "chore: 版本 0.1.1" && git push

# 2. 打 tag 并发布 Release（发布动作本身触发上传）
git tag v0.1.1 && git push origin v0.1.1
gh release create v0.1.1 --generate-notes --target v0.1.1
```

发完之后，消费方（doc-pipeline）就可以把 `artesian @ git+…@<sha>` 换成
`artesian>=0.1.1`，"每次库改动都要手改 sha"这条成本随之消失；
它的分层判据两种形态都认（见 doc-pipeline `tests/test_layering.py`）。
