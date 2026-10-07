"""`tools/verify_dist.py` 的判据——发布门禁自己也得有牙齿。

这个脚本是"发出去的包对不对"的最后一道，所以它的用例不靠真构建（慢且要网络），
而是在 tmp 里造 wheel/sdist 喂给它。**必须包含反向对照**：
少了这些，"门禁一直在绿"可能只是它从来没真的看过任何东西。

空串参数那条是 2026-10-07 的真 bug 回归：CI 的 dispatch 没有 tag，
`${WANT}` 展开成空参数，脚本把空串当成"给了版本号"，于是
"tag 要发 ，但 pyproject 的 version 是 0.1.0" 直接把干跑打红——
本机手测时传了显式版本，正好绕过了这条。
"""
from __future__ import annotations

import importlib.util
import io
import tarfile
import zipfile
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent / "tools" / "verify_dist.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("verify_dist", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_dist(tmp: Path, expect: list[str], ver: str, *, with_pytyped: bool = True,
              with_readme: bool = True) -> Path:
    """造一个看起来像 build 产物的 dist 目录。"""
    dist = tmp / "dist"
    dist.mkdir(parents=True, exist_ok=True)

    wheel = dist / f"artesian-{ver}-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as z:
        for name in [m for m in expect if m != "py.typed"]:
            z.writestr(f"artesian/{name}", "# fake\n")
        if with_pytyped and "py.typed" in expect:
            z.writestr("artesian/py.typed", "")
        z.writestr(f"artesian-{ver}.dist-info/METADATA", "Metadata-Version: 2.4\n")

    sdist = dist / f"artesian-{ver}.tar.gz"
    with tarfile.open(sdist, "w:gz") as t:

        def add(name: str, body: str = "x\n") -> None:
            data = body.encode("utf-8")
            info = tarfile.TarInfo(f"artesian-{ver}/{name}")
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))

        add("PKG-INFO")
        if with_readme:
            add("README.md")
        add("pyproject.toml")
        for name in expect:
            add(f"src/artesian/{name}")
    return dist


def test_正例_产物齐全时通过(tmp_path, monkeypatch):
    mod = load_tool()
    ver = mod.pyproject_version()
    monkeypatch.setattr(mod, "EXPECT_IN_WHEEL", list(mod.SRC_MODULES) + ["py.typed"])
    dist = make_dist(tmp_path, mod.EXPECT_IN_WHEEL, ver)
    assert mod.main(["verify_dist.py", str(dist)]) == 0


def test_空串版本参数等于没给(tmp_path, monkeypatch):
    """回归：CI 里 dispatch 没有 tag，`${WANT}` 会展开成一个空字符串参数。"""
    mod = load_tool()
    ver = mod.pyproject_version()
    monkeypatch.setattr(mod, "EXPECT_IN_WHEEL", list(mod.SRC_MODULES) + ["py.typed"])
    dist = make_dist(tmp_path, mod.EXPECT_IN_WHEEL, ver)
    assert mod.main(["verify_dist.py", str(dist), ""]) == 0
    assert mod.main(["verify_dist.py", str(dist), f"v{ver}"]) == 0   # 带 v 前缀也要认


def test_tag版本与pyproject不一致必须红(tmp_path, monkeypatch):
    mod = load_tool()
    monkeypatch.setattr(mod, "EXPECT_IN_WHEEL", list(mod.SRC_MODULES) + ["py.typed"])
    dist = make_dist(tmp_path, mod.EXPECT_IN_WHEEL, mod.pyproject_version())
    with pytest.raises(SystemExit) as ei:
        mod.main(["verify_dist.py", str(dist), "9.9.9"])
    assert "9.9.9" in str(ei.value.code)


def test_wheel少py_typed必须红(tmp_path, monkeypatch):
    """py.typed 丢了不会让源码测试变红，只会让消费方 mypy 静默退化成 Any。"""
    mod = load_tool()
    ver = mod.pyproject_version()
    expect = list(mod.SRC_MODULES) + ["py.typed"]
    monkeypatch.setattr(mod, "EXPECT_IN_WHEEL", expect)
    dist = make_dist(tmp_path, expect, ver, with_pytyped=False)
    with pytest.raises(SystemExit) as ei:
        mod.main(["verify_dist.py", str(dist)])
    assert "py.typed" in str(ei.value.code)


def test_新模块没进包必须红(tmp_path, monkeypatch):
    """模拟"加了模块但打包口径忘了改"——期望来自 src 目录，产物里没有就该红。"""
    mod = load_tool()
    ver = mod.pyproject_version()
    real = list(mod.SRC_MODULES) + ["py.typed"]
    dist = make_dist(tmp_path, real, ver)
    monkeypatch.setattr(mod, "EXPECT_IN_WHEEL", real + ["_brand_new.py"])
    with pytest.raises(SystemExit) as ei:
        mod.main(["verify_dist.py", str(dist)])
    assert "_brand_new.py" in str(ei.value.code)


def test_sdist缺README必须红(tmp_path, monkeypatch):
    mod = load_tool()
    ver = mod.pyproject_version()
    monkeypatch.setattr(mod, "EXPECT_IN_WHEEL", list(mod.SRC_MODULES) + ["py.typed"])
    dist = make_dist(tmp_path, mod.EXPECT_IN_WHEEL, ver, with_readme=False)
    with pytest.raises(SystemExit) as ei:
        mod.main(["verify_dist.py", str(dist)])
    assert "README.md" in str(ei.value.code)


def test_dist目录不存在必须红(tmp_path):
    mod = load_tool()
    with pytest.raises(SystemExit) as ei:
        mod.main(["verify_dist.py", str(tmp_path / "nope")])
    assert "python -m build" in str(ei.value.code)


def test_产物多于一个也要红(tmp_path, monkeypatch):
    """两个 wheel 说明有人手搓过 dist：上传哪个是不确定的，不能默认绿。"""
    mod = load_tool()
    ver = mod.pyproject_version()
    monkeypatch.setattr(mod, "EXPECT_IN_WHEEL", list(mod.SRC_MODULES) + ["py.typed"])
    dist = make_dist(tmp_path, mod.EXPECT_IN_WHEEL, ver)
    (dist / f"artesian-{ver}-py3-none-any.whl").rename(dist / f"extra-{ver}.whl")
    (dist / f"extra2-{ver}-py3-none-any.whl").write_bytes(
        (dist / f"extra-{ver}.whl").read_bytes())
    with pytest.raises(SystemExit) as ei:
        mod.main(["verify_dist.py", str(dist)])
    assert "wheel" in str(ei.value.code)
