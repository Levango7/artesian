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

以下符号视为公开 API，0.x 内不做破坏性变更。doc-pipeline 是当前唯一消费方，
其中 `fast_json.dumps` / `fast_json.loads` 与 `selectolax_compat` 的全部条目已被
其产品代码或测试实际引用；`dumps_bytes` / `HAS_ORJSON` 为库完整 API 的一部分：

- `artesian.fast_json`：`dumps`、`loads`、`dumps_bytes`、`HAS_ORJSON`
- `artesian.selectolax_compat`：`resolve_backend`、`requested_backend`、`get_parser`、`MODULES`、`ENV_OVERRIDE`

注：`selectolax_compat._load` 是私有实现，但消费方测试直接引用它做探测断言
（`MODULES` × `_load`），重命名时必须同步两仓；如有真实外部需求再提升为公开。

## 测试

**35 个测试本机全绿**（2026-10-07 本机实测：`34 passed, 1 skipped`——orjson 回退
模拟用例在装有 orjson 时按设计跳过；`python -m pytest tests/ -q`）
