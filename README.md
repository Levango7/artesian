# artesian

自流井——接通即涌的取数/知识底座。

从 doc-pipeline 抽离的独立库：JSON 序列化、HTML 解析后端兼容层、
嵌入层与知识库。当前为迁移期第二波（搜索引擎统一接口在后续波次迁入）。

## 模块

| 模块 | 职责 |
|---|---|
| `fast_json` | orjson 优先、标准库回退的 JSON 序列化（`dumps` / `loads` / `dumps_bytes` / `HAS_ORJSON`） |
| `selectolax_compat` | selectolax 内核（modest/lexbor）探测与显式降级（`resolve_backend` / `get_parser` / `requested_backend`） |
| `embeddings` | 文本 → 稠密向量：hash（内置兜底）/ local（sentence-transformers）/ api（OpenAI 兼容）三后端，按可用性自动选并如实记录降级原因，含离线探测保护 |
| `knowledge_base` | 文档切块（结构感知）→ 向量化 → SQLite 持久化 → 暴力余弦检索；含换嵌入器的向量空间保护与重建 |

## 安装

```
pip install -e ".[html,dev]"        # 本地语义嵌入（local 后端）另加 .[embed]
```

## 兼容承诺

以下符号视为公开 API，0.x 内不做破坏性变更。doc-pipeline 是当前唯一消费方：

- `artesian.fast_json`：`dumps`、`loads`、`dumps_bytes`、`HAS_ORJSON`
- `artesian.selectolax_compat`：`resolve_backend`、`requested_backend`、`get_parser`、`MODULES`、`ENV_OVERRIDE`
- `artesian.embeddings`：`extract_features`、`Embedder`、`HashEmbedder`、`LocalEmbedder`、`APIEmbedder`、`available_embedders`、`auto_fallback_reasons`、`model_is_cached`、`get_embedder`、`pack_vector`、`unpack_vector`、`cosine`、`DEFAULT_HASH_DIM`、`DEFAULT_LOCAL_MODEL`
- `artesian.knowledge_base`：`KnowledgeBase`、`chunk_markdown`、`DEFAULT_DB`、`DEFAULT_CHUNK_CHARS`、`DEFAULT_CHUNK_OVERLAP`

其中 doc-pipeline 产品代码与测试实际引用：`fast_json.dumps` / `loads`、
`selectolax_compat` 全部条目、`embeddings` 的 `get_embedder` / `available_embedders` /
`auto_fallback_reasons` / `model_is_cached` / `LocalEmbedder` / `Embedder` / `cosine` /
`pack_vector` / `unpack_vector`（含实例面 `embed` / `embed_one` / `dim` / `name`）、
`knowledge_base` 的 `KnowledgeBase` / `chunk_markdown`
（2026-10-07 按引用点实测；`dumps_bytes` / `HAS_ORJSON` / `HashEmbedder` / `APIEmbedder`
等其余条目为库完整 API 的一部分）。

注：`selectolax_compat._load` 是私有实现，但消费方测试直接引用它做探测断言
（`MODULES` × `_load`），重命名时必须同步两仓；如有真实外部需求再提升为公开。

## 测试

**126 个测试本机全绿**（2026-10-07 本机实测：`125 passed, 1 skipped`——orjson 回退
模拟用例在装有 orjson 时按设计跳过；`python -m pytest tests/ -q`）
