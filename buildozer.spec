[app]

# 應用程式基本資料
title = 上班鼓励器
package.name = workencourager
package.domain = org.tony

# 原始碼
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,json
source.exclude_dirs = _testdata,_kivy,__pycache__,.github,bin,.buildozer,screenshots
source.exclude_patterns = *.pyc

version = 1.0.0

# Kivy 2.3.1 是 python-for-android 目前支援的穩定版本
requirements = python3,kivy==2.3.1

# 直式視窗
orientation = portrait
fullscreen = 0

android.api = 34
android.minapi = 24
android.ndk = 25b
# 只編 arm64-v8a：涵蓋 2017 年後幾乎所有 Android 手機，建置時間與檔案大小都減半
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
# 在容器／CI 裡是以 root 執行，設 0 才不會跳出互動確認（CI 沒有 stdin，會 EOFError）
warn_on_root = 0
