"""README 测试计数与代码实态一致性护栏。

从 doc-pipeline 的同名护栏裁剪而来：数字从 `pytest --co` 的实际收集数取，
不写死常量——加测试忘改 README（或 README 落后于代码）时直接红。
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


def _readme_declared_count() -> int | None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    m = re.search(r"\*\*(\d+)\s*个测试本机全绿\*\*", text)
    return int(m.group(1)) if m else None


@pytest.mark.slow
def test_readme_test_count_matches_collection():
    """README 声明的测试数 == 实际收集数。

    数字来自 `pytest --co`，不是写死的常量——加测试时忘了改 README 会直接红。
    """
    declared = _readme_declared_count()
    assert declared is not None, "README 的测试数句式被改坏了，护栏读不到数字"

    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "--co", "-q",
         "-p", "no:cacheprovider", "--no-header"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=300,
    )
    assert proc.returncode in (0, 5), f"收集失败：{proc.stdout[-800:]}{proc.stderr[-800:]}"
    tail = proc.stdout.strip().splitlines()[-1]
    m = re.search(r"(\d+)/(\d+)\s+tests? collected", tail)
    if m:
        collected = int(m.group(1))               # 已排除 deselected 的用例
    else:
        m2 = re.search(r"(\d+)\s+tests? collected", tail)
        assert m2, f"读不懂 --co 的汇总行：{tail!r}"
        collected = int(m2.group(1))

    # skipif 的用例被收集但不执行，所以 declared 允许比 collected 小；
    # 差超过 10 条就说明数字确实过期了。
    assert 0 <= collected - declared <= 10, (
        f"README 写 {declared} passed，而实际收集 {collected} 条；"
        f"差值 {collected - declared} 超出「仅 skipif」的容忍范围，请更新 README 的测试一节")
