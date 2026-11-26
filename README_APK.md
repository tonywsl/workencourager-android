# 上班鼓励器 —— Android 版（Kivy）

## 先講清楚一件事

原本的 `work_encourager.py` 用的是 **Tkinter**，而 Tkinter 在 Android 上**沒有可用的執行環境**：
`python-for-android`、`Buildozer`、`BeeWare` 都只支援 Kivy / SDL2 / WebView 這類後端。
所以 `dist\work_encourager.exe` 不可能「改副檔名」或「重新打包」就變成 APK。

要上 Android，只能把介面層換掉。這個資料夾就是用 Kivy 重寫的版本，
**計算與儲存邏輯和桌面版 `work_encourager_v2.py` 完全同一套**（`core.py`），
所以兩邊算出來的錢會一致。

## 這個資料夾有什麼

| 檔案 | 用途 |
|---|---|
| `main.py` | Kivy 介面（主畫面 + 設定畫面），手機與桌面都能跑 |
| `core.py` | 純邏輯：工時曲線、費率、設定與工時帳本（不依賴任何 UI 框架） |
| `selftest_core.py` | 不裝 Android 也能跑的自我檢查（`python selftest_core.py`） |
| `buildozer.spec` | Buildozer 打包設定（Kivy 2.3.1、API 34、arm64 + armv7） |
| `NotoSansSC-Regular.ttf` | 中文字型（10 MB，必須一起打包，否則中文變方塊） |
| `.github/workflows/build-apk.yml` | 用 GitHub Actions 雲端打包的設定 |

## 本機先看畫面（不用 Android）

```powershell
cd C:\Users\tonywang\Desktop\Tony\Python\WorkEncouragerAndroid
python main.py
```

需要 `pip install kivy==2.3.2`（你機器上已經有了）。畫面上會是可縮放的視窗，
按「設置」可以改月薪、工時、心願目標；資料會存在
`%APPDATA%\WorkEncourager\config.json` 與 `ledger.json`。

先跑自我檢查確認邏輯沒問題：

```powershell
python selftest_core.py
```

---

## 方法 A：GitHub Actions 雲端打包（推薦，本機零安裝）

不用在自己電腦裝 Android SDK / NDK（那包要 6–8 GB）。步驟：

1. 到 GitHub 建一個新的 repository（Private 也可以）。
2. 把這個資料夾推上去：
   ```powershell
   cd C:\Users\tonywang\Desktop\Tony\Python\WorkEncouragerAndroid
   git init
   git add .
   git commit -m "work encourager android"
   git branch -M main
   git remote add origin https://github.com/<你的帳號>/workencourager-android.git
   git push -u origin main
   ```
3. 到 repo 的 **Actions** 頁籤，會自動開始 `Build APK`。
4. 等約 20–35 分鐘（第一次要下載 SDK/NDK，之後有快取會快很多）。
5. 進該次執行頁面，最下面 **Artifacts** 下載 `workencourager-debug-apk`，
   解壓後就是 `.apk`。

工作流程檔已經寫好（`.github/workflows/build-apk.yml`），用的是
`ArtemSBulgakov/buildozer-action@v1`，不需要自己寫 Gradle 設定。

---

## 方法 B：WSL2 + Buildozer（本機打包）

你的機器已經有 `Ubuntu-22.04` 的 WSL 發行版。**注意：專案要複製到 WSL 內部的
家目錄，不要放在 `/mnt/c/...`**，因為 buildozer 在 Windows 磁碟上會非常慢，
而且經常因為檔案權限／大小寫問題失敗。

在 WSL 終端機（不是 PowerShell）執行：

```bash
# 1. 系統相依套件（JDK 17 是 Gradle 8 / AGP 8 的必要條件）
sudo apt update
sudo apt install -y python3-pip python3-venv git zip unzip \
    openjdk-17-jdk autoconf libtool pkg-config zlib1g-dev \
    libncurses-dev libncursesw5-dev cmake libffi-dev libssl-dev

# 2. Buildozer
pip3 install --user buildozer cython==0.29.36
echo 'export PATH=$PATH:~/.local/bin' >> ~/.bashrc && source ~/.bashrc

# 3. 把專案複製進 WSL（不是用 /mnt/c 直接建置）
cp -r /mnt/c/Users/tonywang/Desktop/Tony/Python/WorkEncouragerAndroid ~/weandroid
cd ~/weandroid

# 4. 開始打包（第一次 30–60 分鐘，會下載 SDK/NDK）
buildozer -v android debug
```

完成後產物在：

```
~/weandroid/bin/workencourager-1.0.0-arm64-v8a_armeabi-v7a-debug.apk
```

複製回 Windows：

```bash
cp ~/weandroid/bin/*.apk /mnt/c/Users/tonywang/Desktop/
```

## 方法 C：Docker（不想動 WSL 的系統套件）

```powershell
docker run --rm -v "${PWD}:/home/user/hostcwd" -v "${PWD}/.buildozer:/home/user/.buildozer" `
  kivy/buildozer -v android debug
```

需要 Docker Desktop 且有 WSL2 後端。

---

## 安裝到手機

1. 把 `.apk` 傳到手機（USB、雲端硬碟、LINE 傳給自己都可以）。
2. 點開安裝，Android 會要求「允許安裝來自此來源的應用程式」，允許即可。
3. 若之前裝過同名 App，先解除安裝舊版，避免簽章衝突（`INSTALL_FAILED_UPDATE_INCOMPATIBLE`）。

這是 **debug 版**（用 debug keystore 簽章），自己用沒問題；
要上 Google Play 得另外產生 release keystore 並改 `buildozer.spec` 的簽章設定。

## 手機上的資料存在哪

`/data/user/0/org.tony.workencourager/files/`
`config.json`（設定）與 `ledger.json`（每日工時帳本）。
解除安裝 App 會一起清掉，重要資料請自行備份。

---

## 常見錯誤

| 訊息 | 原因與解法 |
|---|---|
| `Command failed: ... Android SDK license` | 第一次建置要先接受授權；`buildozer.spec` 已有 `android.accept_sdk_license = True`，若仍失敗，手動跑一次 `buildozer android debug` 並按 `y` |
| `Aidl not found` / `Java version` 錯誤 | JDK 版本不對，必須是 **17**（`java -version` 確認），Ubuntu 22.04 內建是 11 |
| `Unknown command: buildozer` | `~/.local/bin` 不在 PATH，或要用 `~/.local/bin/buildozer` 全路徑 |
| 建置卡在 `Downloading NDK` 很久 | 正常，NDK 約 1 GB；中斷後重跑會續傳 |
| 中文顯示成方塊 | `NotoSansSC-Regular.ttf` 沒被打包進去；確認它在專案根目錄，且 `source.include_exts` 含 `ttf` |
| App 一開就閃退 | 用 `adb logcat -s python` 看實際錯誤；最常見是 import 失敗或字型路徑錯 |

## 版本與相容性備註

- `buildozer.spec` 指定 `kivy==2.3.1`：這是 python-for-android 目前能穩定編譯的版本。
  本機 Windows 上你裝的是 2.3.2，畫面行為一致，只是打包時會用 2.3.1。
- 打包過程用的是 python-for-android 內建的 Python（3.11），不是你的 3.14；
  `core.py` 沒有用到 3.12+ 語法，兩邊都能跑。
- 想改版本號：`buildozer.spec` 的 `version`，同時 `android.api` 建議維持 34。
