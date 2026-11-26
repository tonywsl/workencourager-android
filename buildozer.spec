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
# minapi 刻意設 21：p4a 解析純 Python 依賴時，平台標籤會是 android_<minapi>_<abi>。
# charset-normalizer 3.5.x 有發佈 android_24_arm64_v8a 的二進位 wheel，
# 但 minapi=21 對不上那個標籤，pip 就會退回通用的 py3-none-any wheel，
# 避免 "is not a supported wheel on this platform" 讓建置失敗。
android.minapi = 21
android.ndk = 25b
# 只編 arm64-v8a：涵蓋 2017 年後幾乎所有 Android 手機，建置時間與檔案大小都減半
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
# 在容器／CI 裡是以 root 執行，設 0 才不會跳出互動確認（CI 沒有 stdin，會 EOFError）
warn_on_root = 0
