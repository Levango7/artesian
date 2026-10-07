"""发布前对**产物**的校验（不是对源码）——包内容、py.typed、版本一致三件事。

为什么单独一个脚本而不是"能 pip install 就行"：这三类缺陷都不会让源码测试变红，
只在装出来的包上才现形，而现形时已经在用户机器上了。

- 内容对齐源码目录：新增模块忘了进包（packages/package-data 口径漂移）当场红；
- `py.typed` 必须在 wheel 与 sdist 里都在：它丢了消费方 mypy **不会报错**，
  只是把返回值静默退化成 Any（2026-10-07 真踩过，见 doc-pipeline CHANGELOG 续6）；
- 版本三处一致：产物文件名、`pyproject.toml` 的 `project.version`、
  装好之后 `artesian.__version__` 与包元数据版本——不一致就是 tag/版本号改漏了一处。

用法：
    python tools/verify_dist.py [dist目录] [期望版本] [--installed]
`--installed` 只有在把产物装进当前环境后才该加（发布流水线里由干净 venv 那步带上）。
"""
from __future__ import annotations

import re
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC_DIR = REPO / "src" / "artesian"
SRC_MODULES = sorted(p.name for p in SRC_DIR.glob("*.py"))
EXPECT_IN_WHEEL = SRC_MODULES + ["py.typed"]          # py.typed 是 package-data，必须显式在


def fail(msg: str) -> None:
    raise SystemExit(f"[verify_dist] 失败：{msg}")


def pyproject_version() -> str:
    data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    return data["project"]["version"]


def check(dist: Path, want: str | None) -> str:
    ver = pyproject_version()
    if want is not None and want != ver:
        fail(f"tag 要发 {want}，但 pyproject 的 version 是 {ver}（先改 pyproject 再打 tag）")

    wheels = sorted(dist.glob("*.whl"))
    sdists = sorted(dist.glob("*.tar.gz"))
    if len(wheels) != 1:
        fail(f"期望 dist/ 里恰好 1 个 wheel，实际 {len(wheels)} 个：{[w.name for w in wheels]}")
    if len(sdists) != 1:
        fail(f"期望 dist/ 里恰好 1 个 sdist，实际 {len(sdists)} 个：{[s.name for s in sdists]}")
    wheel, sdist = wheels[0], sdists[0]
    for art in (wheel, sdist):
        if ver not in art.name:
            fail(f"产物文件名里没有 version {ver}：{art.name}")

    names = set(zipfile.ZipFile(wheel).namelist())
    shipped = sorted(n.split("/", 1)[1] for n in names
                     if n.startswith("artesian/")
                     and (n.endswith(".py") or n.endswith("py.typed")))
    if shipped != sorted(EXPECT_IN_WHEEL):
        miss = sorted(set(EXPECT_IN_WHEEL) - set(shipped))
        extra = sorted(set(shipped) - set(EXPECT_IN_WHEEL))
        fail(f"wheel 内容与 src/artesian 不符：缺 {miss}，多 {extra}")

    with tarfile.open(sdist) as t:
        members = [m.name for m in t.getmembers() if m.isfile()]

    def has(suffix: str) -> bool:
        return any(m.endswith(suffix) for m in members)

    for req in ("PKG-INFO", "README.md", "pyproject.toml"):
        if not has(req):
            fail(f"sdist 里没有 {req}（发布页说明与许可就来自这些文件）")
    for mod in EXPECT_IN_WHEEL:
        if not has(f"src/artesian/{mod}"):
            fail(f"sdist 里缺 src/artesian/{mod}")
    return ver


def check_installed(ver: str) -> None:
    import importlib.metadata

    import artesian
    if artesian.__version__ != ver:
        fail(f"装出来的 artesian.__version__={artesian.__version__} 与 pyproject 的 {ver} 不符")
    meta = importlib.metadata.version("artesian")
    if meta != ver:
        fail(f"包元数据版本 {meta} 与 pyproject 的 {ver} 不符")
    marker = Path(artesian.__file__).parent / "py.typed"
    if not marker.exists():
        fail(f"安装后的包目录里没有 py.typed（在 {marker.parent}）——消费方 mypy 会静默退化成 Any")


def main(argv: list[str]) -> int:
    installed = "--installed" in argv
    pos = [a for a in argv[1:] if not a.startswith("--")]
    dist = Path(pos[0]) if pos else REPO / "dist"
    want = re.sub(r"^v", "", pos[1]) if len(pos) > 1 else None
    if not dist.is_dir():
        fail(f"dist 目录不存在：{dist}（先跑 python -m build）")

    ver = check(dist, want)
    if installed:
        check_installed(ver)
    print(f"[verify_dist] OK：wheel/sdist 内容齐全、py.typed 在两处、版本={ver}"
          + ("；安装态三项一致" if installed else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
