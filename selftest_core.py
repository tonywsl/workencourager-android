"""不裝 Android 也能跑的自我檢查：驗證 core.py 的關鍵行為。

在專案目錄執行：
    python selftest_core.py
"""

from __future__ import annotations

import shutil
import tempfile
import uuid
from datetime import datetime, time
from pathlib import Path

import core


def main() -> int:
    checks = 0

    def check(label: str, actual, expected) -> None:
        nonlocal checks
        checks += 1
        if actual != expected:
            raise AssertionError(f"{label}: 期望 {expected!r}，實際 {actual!r}")

    # 工時曲線
    schedule = core.WorkSchedule(time(8, 0), time(12, 0), time(13, 0), time(18, 0))
    check("每日有效秒數", schedule.total_seconds, 9 * 3600)
    for (hour, minute), expected in {
        (7, 0): 0,
        (11, 0): 3 * 3600,
        (12, 30): 4 * 3600,
        (17, 0): 8 * 3600,
        (19, 0): 9 * 3600,
    }.items():
        moment = datetime(2026, 11, 26, hour, minute)
        check(f"{hour:02d}:{minute:02d} 已工作秒數", schedule.worked_seconds(moment), expected)

    # 費率
    rates = core.Rates(monthly_salary=3650.0, workdays=22, daily_seconds=32400)
    check("滿 22 天 = 月薪", round(rates.daily * 22, 6), 3650.0)
    check("時薪", round(rates.hourly, 4), round(3650 / 22 / 9, 4))

    # 行事曆
    check("2026-11 工作日", core.month_workdays(2026, 11), 21)

    # 設定往返與帳本（用一般權限的暫存目錄，避免受控環境的權限問題）
    tmp = Path(tempfile.gettempdir()) / f"we_selftest_{uuid.uuid4().hex[:8]}"
    tmp.mkdir()
    try:
        store = core.Store(tmp)
        original = core.Settings(
            monthly_salary=4200.0,
            is_auto_days=False,
            manual_days=23,
            schedule=core.WorkSchedule(time(9, 0), time(12, 0), time(13, 0), time(18, 0)),
            targets=[core.Target("咖啡", 35.0)],
        )
        store.save_settings(original)
        loaded = store.load_settings()
        check("月薪往返", loaded.monthly_salary, 4200.0)
        check("手動天數往返", loaded.manual_days, 23)
        check("目標往返", [t.name for t in loaded.targets], ["咖啡"])

        # 帳本只增不減
        ledger = core.Ledger(store)
        ledger.record("2026-11-26", 3600)
        ledger.record("2026-11-26", 1800)
        check("帳本只增不減", ledger.seconds_in_month(2026, 11), 3600)

        # 本月累計：以整月進度計算（已過平日算滿、今天按時間比例）
        moment = datetime(2026, 11, 27, 14, 16)  # 週五，已過 19 個平日
        progress = core.month_progress(moment, schedule, 21)
        check("整月進度天數", round(progress, 4), round(19 + 18960 / 32400, 4))
        check(
            "本月累計",
            round(core.month_earned(3000.0, moment, schedule, 21), 2),
            round(3000.0 * progress / 21, 2),
        )
        check(
            "月底等於月薪",
            round(core.month_earned(3000.0, datetime(2026, 11, 30, 19, 0), schedule, 21), 2),
            3000.0,
        )
        check("預設月薪", core.Settings().monthly_salary, 3000.0)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"OK：{checks} 項檢查全部通過")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
