"""上班鼓励器 —— 共用核心邏輯（純 Python，不依賴 tkinter 或 Kivy）。

桌面版 ``work_encourager_v2.py`` 與 Android 版 ``main.py`` 都匯入這支模組，
確保兩邊的計算結果完全一致。
"""

from __future__ import annotations

import calendar
import json
import math
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, time
from functools import lru_cache
from pathlib import Path

APP_DIR_NAME = "WorkEncourager"
TIME_FMT = "%H:%M"
DAY_FMT = "%Y-%m-%d"

DEFAULT_TARGETS = (
    {"name": "一杯咖啡", "amount": 35.0},
    {"name": "一顿午餐", "amount": 75.0},
    {"name": "一顿晚餐", "amount": 150.0},
)


# ==========================================
# 時間與數值工具
# ==========================================
def seconds_of_day(value: time) -> int:
    """把 ``datetime.time`` 轉成當天經過的秒數。"""
    return value.hour * 3600 + value.minute * 60


@lru_cache(maxsize=64)
def month_workdays(year: int, month: int, work_days_per_week: int = 5) -> int:
    """指定年月的週一到週五天數（``work_days_per_week=5`` 即週休二日）。"""
    days_in_month = calendar.monthrange(year, month)[1]
    return sum(
        1
        for day in range(1, days_in_month + 1)
        if calendar.weekday(year, month, day) < work_days_per_week
    )


def passed_workdays(year: int, month: int, day: int) -> int:
    """本月 1 號到「day 的前一天」之間有幾個平日。"""
    return sum(1 for d in range(1, day) if calendar.weekday(year, month, d) < 5)


def parse_hhmm(text: str) -> time:
    """解析 ``HH:MM``，允許前後空白與 ``8:00``。"""
    raw = (text or "").strip()
    if not raw:
        raise ValueError("時間不能留空")
    try:
        return datetime.strptime(raw, TIME_FMT).time()
    except ValueError:
        raise ValueError(f"時間格式應為 HH:MM，收到的是「{raw}」") from None


def parse_positive_float(
    text: str, label: str, *, minimum: float = 0.0, maximum: float = 1e9
) -> float:
    """解析正數，擋掉 nan / inf / 負數 / 爆量數值。"""
    raw = (text or "").strip().replace(",", "")
    if not raw:
        raise ValueError(f"{label}不能留空")
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"{label}必須是數字，收到的是「{raw}」") from None
    if not math.isfinite(value):
        raise ValueError(f"{label}必須是有限的數值")
    if value <= minimum:
        raise ValueError(f"{label}必須大於 {minimum:g}")
    if value > maximum:
        raise ValueError(f"{label}太大，上限為 {maximum:g}")
    return value


def parse_int_in_range(text: str, label: str, low: int, high: int) -> int:
    """解析整數並檢查範圍（``22`` 與 ``22.0`` 都接受）。"""
    raw = (text or "").strip()
    if not raw:
        raise ValueError(f"{label}不能留空")
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"{label}必須是整數，收到的是「{raw}」") from None
    if not math.isfinite(value) or value != int(value):
        raise ValueError(f"{label}必須是整數")
    number = int(value)
    if not low <= number <= high:
        raise ValueError(f"{label}必須介於 {low} 到 {high} 之間")
    return number


def format_seconds(total_seconds: float) -> str:
    """把秒數格式化成 ``HH:MM:SS``；負數視為 0。"""
    seconds = max(0, int(total_seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


# ==========================================
# 資料模型
# ==========================================
@dataclass(frozen=True)
class WorkSchedule:
    """一天的工時設定，負責回答「到此刻為止工作了幾秒」。"""

    start: time = time(8, 0)
    lunch_start: time = time(12, 0)
    lunch_end: time = time(13, 0)
    end: time = time(18, 0)

    def __post_init__(self) -> None:
        if not (self.start < self.lunch_start < self.lunch_end < self.end):
            raise ValueError("時間順序應為：上班 < 午休開始 < 午休結束 < 下班")
        _ = self.total_seconds

    @property
    def total_seconds(self) -> int:
        """每日有效工作秒數 =（下班 - 上班）-（午休結束 - 午休開始）。"""
        gross = seconds_of_day(self.end) - seconds_of_day(self.start)
        break_seconds = seconds_of_day(self.lunch_end) - seconds_of_day(self.lunch_start)
        total = gross - break_seconds
        if total <= 0:
            raise ValueError("每日有效工作時間必須大於 0")
        return total

    def phase(self, now: datetime) -> str:
        """before / am / lunch / pm / after。"""
        if now < datetime.combine(now.date(), self.start):
            return "before"
        if now < datetime.combine(now.date(), self.lunch_start):
            return "am"
        if now < datetime.combine(now.date(), self.lunch_end):
            return "lunch"
        if now < datetime.combine(now.date(), self.end):
            return "pm"
        return "after"

    def worked_seconds(self, now: datetime) -> int:
        """當天到 ``now`` 為止的有效工作秒數（午休不計、下班後鎖定滿勤）。"""
        today = now.date()
        start = datetime.combine(today, self.start)
        lunch_start = datetime.combine(today, self.lunch_start)
        lunch_end = datetime.combine(today, self.lunch_end)
        end = datetime.combine(today, self.end)

        if now < start:
            return 0
        morning = int((lunch_start - start).total_seconds())
        if now < lunch_start:
            return int((now - start).total_seconds())
        if now < lunch_end:
            return morning
        if now < end:
            return morning + int((now - lunch_end).total_seconds())
        return self.total_seconds

    @property
    def start_str(self) -> str:
        return self.start.strftime(TIME_FMT)

    @property
    def lunch_start_str(self) -> str:
        return self.lunch_start.strftime(TIME_FMT)

    @property
    def lunch_end_str(self) -> str:
        return self.lunch_end.strftime(TIME_FMT)

    @property
    def end_str(self) -> str:
        return self.end.strftime(TIME_FMT)


@dataclass(frozen=True)
class Rates:
    """由月薪與工時推導出來的費率。"""

    monthly_salary: float
    workdays: int
    daily_seconds: int

    def __post_init__(self) -> None:
        if self.workdays <= 0:
            raise ValueError("當月工作天數必須大於 0")
        if self.daily_seconds <= 0:
            raise ValueError("每日有效工作秒數必須大於 0")

    @property
    def daily(self) -> float:
        return self.monthly_salary / self.workdays

    @property
    def hourly(self) -> float:
        return self.daily / (self.daily_seconds / 3600)

    @property
    def per_second(self) -> float:
        return self.daily / self.daily_seconds


@dataclass(frozen=True)
class Target:
    """一個心願目標。"""

    name: str
    amount: float


# ==========================================
# 持久化
# ==========================================
def app_data_dir() -> Path:
    """設定與帳本的預設目錄；Android 由 App 傳入 user_data_dir 覆蓋。"""
    override = os.environ.get("WE_DATA_DIR")
    if override:
        return Path(override)
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / APP_DIR_NAME
    return Path.home() / f".{APP_DIR_NAME.lower()}"


def _atomic_write_json(path: Path, payload: dict) -> None:
    """先寫 tmp 再 os.replace，避免斷電留下半個 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _as_float(value: object, default: float) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _as_int(value: object, default: int) -> int:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    if not math.isfinite(number) or number != int(number):
        return default
    return int(number)


def _as_time(value: object, default: time) -> time:
    if not isinstance(value, str):
        return default
    try:
        return parse_hhmm(value)
    except ValueError:
        return default


@dataclass
class Settings:
    """所有可調整的設定；載入時壞欄位退回預設，不讓程式開不起來。"""

    monthly_salary: float = 3650.0
    is_auto_days: bool = True
    manual_days: int = 22
    schedule: WorkSchedule = field(default_factory=WorkSchedule)
    targets: list = field(default_factory=lambda: [Target(**item) for item in DEFAULT_TARGETS])

    def to_dict(self) -> dict:
        return {
            "monthly_salary": self.monthly_salary,
            "is_auto_days": self.is_auto_days,
            "manual_days": self.manual_days,
            "schedule": {
                "start": self.schedule.start_str,
                "lunch_start": self.schedule.lunch_start_str,
                "lunch_end": self.schedule.lunch_end_str,
                "end": self.schedule.end_str,
            },
            "targets": [{"name": t.name, "amount": t.amount} for t in self.targets],
        }

    @classmethod
    def from_dict(cls, raw: object) -> "Settings":
        settings = cls()
        if not isinstance(raw, dict):
            return settings

        settings.monthly_salary = _as_float(raw.get("monthly_salary"), settings.monthly_salary)
        if not math.isfinite(settings.monthly_salary) or settings.monthly_salary <= 0:
            settings.monthly_salary = cls().monthly_salary

        auto = raw.get("is_auto_days")
        if isinstance(auto, bool):
            settings.is_auto_days = auto

        settings.manual_days = _as_int(raw.get("manual_days"), settings.manual_days)
        if not 1 <= settings.manual_days <= 31:
            settings.manual_days = cls().manual_days

        schedule_raw = raw.get("schedule")
        if isinstance(schedule_raw, dict):
            current = settings.schedule
            try:
                settings.schedule = WorkSchedule(
                    start=_as_time(schedule_raw.get("start"), current.start),
                    lunch_start=_as_time(schedule_raw.get("lunch_start"), current.lunch_start),
                    lunch_end=_as_time(schedule_raw.get("lunch_end"), current.lunch_end),
                    end=_as_time(schedule_raw.get("end"), current.end),
                )
            except ValueError:
                pass  # 壞掉的時間設定整組退回預設

        targets_raw = raw.get("targets")
        if isinstance(targets_raw, list):
            targets = []
            for item in targets_raw:
                if not isinstance(item, dict):
                    continue
                name = item.get("name")
                amount = _as_float(item.get("amount"), -1.0)
                if isinstance(name, str) and name.strip() and amount > 0:
                    targets.append(Target(name.strip(), amount))
            settings.targets = sorted(targets, key=lambda t: t.amount)

        return settings


class Store:
    """config.json 與 ledger.json 的讀寫。"""

    def __init__(self, base: Path | None = None) -> None:
        self.base = Path(base) if base is not None else app_data_dir()
        self.config_path = self.base / "config.json"
        self.ledger_path = self.base / "ledger.json"

    def load_settings(self) -> Settings:
        try:
            with open(self.config_path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return Settings()
        return Settings.from_dict(raw)

    def save_settings(self, settings: Settings) -> None:
        _atomic_write_json(self.config_path, settings.to_dict())

    def load_ledger(self) -> dict:
        try:
            with open(self.ledger_path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return {}
        if not isinstance(raw, dict):
            return {}
        ledger = {}
        for key, value in raw.items():
            seconds = _as_int(value, -1)
            if isinstance(key, str) and len(key) == 10 and seconds >= 0:
                ledger[key] = seconds
        return ledger

    def save_ledger(self, ledger: dict) -> None:
        _atomic_write_json(self.ledger_path, ledger)


class Ledger:
    """每日實際工作秒數，key 為 ``YYYY-MM-DD``。

    採「只增不減」：同一天重複寫入取最大值，關掉程式再開會接續，
    改工時設定也不會讓已記錄的金額倒退。
    """

    def __init__(self, store: Store) -> None:
        self.store = store
        self._data = store.load_ledger()
        self._dirty = False

    def record(self, day: str, seconds: int) -> bool:
        seconds = max(0, int(seconds))
        if seconds > self._data.get(day, 0):
            self._data[day] = seconds
            self._dirty = True
            return True
        return False

    def seconds_in_month(self, year: int, month: int) -> int:
        prefix = f"{year:04d}-{month:02d}-"
        return sum(value for key, value in self._data.items() if key.startswith(prefix))

    def has(self, day: str) -> bool:
        """這一天有沒有任何記錄。"""
        return day in self._data

    def days_in_month(self, year: int, month: int) -> int:
        prefix = f"{year:04d}-{month:02d}-"
        return sum(1 for key in self._data if key.startswith(prefix))

    def first_record_in_month(self, year: int, month: int):
        prefix = f"{year:04d}-{month:02d}-"
        keys = [key for key in self._data if key.startswith(prefix)]
        return min(keys) if keys else None

    def flush(self) -> bool:
        if not self._dirty:
            return False
        self.store.save_ledger(self._data)
        self._dirty = False
        return True

    def __len__(self) -> int:
        return len(self._data)


def month_seconds_estimate(
    ledger: "Ledger", schedule: "WorkSchedule", now: datetime, workdays: int
) -> tuple:
    """以「月」為單位估算本月累計秒數。

    規則：
    * 已有記錄的日子，用實際秒數；
    * 今天以前、沒有記錄的平日，按「滿勤」補上；
    * 補上的天數不超過本月設定的工作天數。

    這樣一開程式看到的就是整月累計（約等於月薪的進度），
    而不是只從今天開始算。回傳 ``(總秒數, 被估算的天數)``。
    """
    year, month = now.year, now.month
    recorded = ledger.seconds_in_month(year, month)
    recorded_days = ledger.days_in_month(year, month)

    missing = 0
    for day in range(1, now.day):
        if calendar.weekday(year, month, day) >= 5:
            continue
        if not ledger.has(f"{year:04d}-{month:02d}-{day:02d}"):
            missing += 1

    budget = max(0, workdays - recorded_days)
    estimated_days = min(missing, budget)
    total = recorded + estimated_days * schedule.total_seconds
    return min(total, workdays * schedule.total_seconds), estimated_days


def seed_past_workdays(ledger: Ledger, settings: Settings, now: datetime, workdays: int) -> int:
    """把本月到昨天為止的平日補登為滿勤，回傳補登天數。"""
    schedule = settings.schedule
    pending = [
        day for day in range(1, now.day) if calendar.weekday(now.year, now.month, day) < 5
    ]
    capped = pending[:workdays]
    for day in capped:
        ledger.record(f"{now.year:04d}-{now.month:02d}-{day:02d}", schedule.total_seconds)
    return len(capped)
