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
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
