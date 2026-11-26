"""檢查 Android 專案是否可以直接推上 GitHub 給 Actions 建置。"""

from __future__ import annotations

import configparser
import sys
from pathlib import Path

import yaml

BASE = Path(__file__).parent
problems = []

# 1. 工作流程 YAML
workflow_path = BASE / ".github" / "workflows" / "build-apk.yml"
doc = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
jobs = doc.get("jobs", {})
if "build-android" not in jobs:
    problems.append("workflow 缺少 build-android job")
steps = jobs.get("build-android", {}).get("steps", [])
uses = [s.get("uses") for s in steps if s.get("uses")]
print("workflow  steps :", [s.get("name") or s.get("uses") for s in steps])
print("workflow  uses  :", uses)
triggers = doc.get("on") or doc.get(True)
print("workflow  on    :", triggers)

# 2. buildozer.spec
spec_path = BASE / "buildozer.spec"
parser = configparser.ConfigParser()
parser.read_string(spec_path.read_text(encoding="utf-8"))
app = parser["app"]
print("spec      app   :", len(app), "keys")

known_required = ["title", "package.name", "package.domain", "source.dir",
                  "source.include_exts", "version", "requirements"]
for key in known_required:
    if not app.get(key):
        problems.append(f"buildozer.spec 缺少 {key}")

# 3. 必要檔案
required_files = ["main.py", "core.py", "NotoSansSC-Regular.ttf", "buildozer.spec",
                  "README.md", "README_APK.md", ".gitignore", "selftest_core.py",
                  "screenshots/main.png"]
for name in required_files:
    path = BASE / name
    if not path.exists():
        problems.append(f"缺少檔案 {name}")
    else:
        print(f"file      {name:<28} {path.stat().st_size:>9} bytes")

# 4. 不能進版控的東西
ignored = (BASE / ".gitignore").read_text(encoding="utf-8")
for pattern in ("bin/", ".buildozer/", "__pycache__/"):
    if pattern not in ignored:
        problems.append(f".gitignore 少了 {pattern}")

# 5. main.py 依賴檢查（import 的模組都要存在）
main_src = (BASE / "main.py").read_text(encoding="utf-8")
for module in ("import core", "from kivy"):
    if module not in main_src:
        problems.append(f"main.py 缺少 {module}")

print()
if problems:
    print("發現問題：")
    for item in problems:
        print("  -", item)
    sys.exit(1)
print("OK：專案結構與工作流程檢查通過，可以推上 GitHub")
