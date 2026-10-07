# artesian

自流井——接通即涌的取数/知识底座。

从 doc-pipeline 抽离的独立库：搜索引擎统一接口、HTML 解析后端兼容层、
嵌入层与知识库。当前为迁移期第一波。

## 模块

| 模块 | 职责 |
|---|---|
| `fast_json` | orjson 优先、标准库回退的 JSON 序列化（`dumps` / `loads` / `dumps_bytes` / `HAS_ORJSON`） |
| `selectolax_compat` | selectolax 内核（modest/lexbor）探测与显式降级（`resolve_backend` / `get_parser` / `requested_backend`） |

## 安装

```
pip install -e ".[html,dev]"
```

## 兼容承诺

以下符号被消费方（doc-pipeline）实际引用，视为公开 API，0.x 内不做破坏性变更：

- `artesian.fast_json`：`dumps`、`loads`、`dumps_bytes`、`HAS_ORJSON`
- `artesian.selectolax_compat`：`resolve_backend`、`requested_backend`、`get_parser`、`MODULES`、`ENV_OVERRIDE`

## 测试

**35 个测试本机全绿**（2026-10-07 本机实测：`34 passed, 1 skipped`——orjson 回退
模拟用例在装有 orjson 时按设计跳过；`python -m pytest tests/ -q`）
