"""上班鼓励器 —— Android / Kivy 版。

與桌面版 ``work_encourager_v2.py`` 共用同一套計算與儲存邏輯（``core.py``），
差別只在 UI 框架：Tkinter 無法打包成 APK，Kivy 可以。

本機預覽：``python main.py``
打包 APK：見同目錄 ``README_APK.md``
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp, sp
from kivy.properties import ListProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

import core

# ---------- 中文字型 ----------
# NotoSansSC-Regular.ttf 必須與本檔同目錄；缺少時退回 Roboto（中文會變方塊）
_FONT_FILE = Path(__file__).with_name("NotoSansSC-Regular.ttf")
if _FONT_FILE.exists():
    LabelBase.register(name="CJK", fn_regular=str(_FONT_FILE))
    FONT = "CJK"
else:  # pragma: no cover - 只在字型檔遺失時發生
    FONT = "Roboto"


# ---------- 配色（與桌面版一致） ----------
BG = (0.169, 0.169, 0.169, 1)        # #2B2B2B
CARD = (0.118, 0.118, 0.118, 1)      # #1E1E1E
FIELD = (0.235, 0.235, 0.235, 1)     # #3C3C3C
TEXT = (0.878, 0.878, 0.878, 1)      # #E0E0E0
WHITE = (1, 1, 1, 1)
MUTED = (0.667, 0.667, 0.667, 1)     # #AAAAAA
DIM = (0.467, 0.467, 0.467, 1)       # #777777
ACCENT = (0.392, 0.710, 0.965, 1)    # #64B5F6
OK = (0.506, 0.780, 0.522, 1)        # #81C784
WARN = (1.0, 0.718, 0.302, 1)        # #FFB74D
MONEY = (1.0, 0.835, 0.310, 1)       # #FFD54F
REST = (0.565, 0.792, 0.976, 1)      # #90CAF9
PRIMARY = (0.098, 0.463, 0.824, 1)   # #1976D2
BTN = (0.259, 0.259, 0.259, 1)       # #424242


class BgBox(BoxLayout):
    """帶純色背景的 BoxLayout（模擬卡片）。"""

    bg_color = ListProperty(CARD)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        with self.canvas.before:
            self._bg = Color(*self.bg_color)
            self._rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync, size=self._sync, bg_color=self._sync_color)

    def _sync(self, *_args) -> None:
        self._rect.pos = self.pos
        self._rect.size = self.size

    def _sync_color(self, *_args) -> None:
        self._bg.rgba = self.bg_color


class WrapLabel(Label):
    """自動換行且高度隨內容生長的標籤。"""

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("font_name", FONT)
        kwargs.setdefault("color", TEXT)
        kwargs.setdefault("halign", "center")
        kwargs.setdefault("valign", "middle")
        super().__init__(**kwargs)
        self.bind(width=self._sync_width, texture_size=self._sync_height)
        self._sync_width()

    def _sync_width(self, *_args) -> None:
        self.text_size = (max(dp(80), self.width * 0.94), None)

    def _sync_height(self, *_args) -> None:
        if self.size_hint_y is None:
            self.height = self.texture_size[1]


class LeftLabel(Label):
    """靠左對齊且垂直置中的標籤（Kivy 的 Label 要設 text_size 才會對齊）。"""

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("font_name", FONT)
        kwargs.setdefault("color", TEXT)
        kwargs.setdefault("halign", "left")
        kwargs.setdefault("valign", "middle")
        super().__init__(**kwargs)
        self.bind(size=self._sync)

    def _sync(self, *_args) -> None:
        self.text_size = (self.width, self.height)


class Bar(Widget):
    """細長的進度條（自繪，行動裝置上比預設 ProgressBar 好控制）。"""

    value = NumericProperty(0.0)  # 0.0 - 1.0

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(8))
        super().__init__(**kwargs)
        with self.canvas:
            Color(*CARD)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
            Color(*ACCENT)
            self._fg_rect = Rectangle(pos=self.pos, size=(0, self.height))
        self.bind(pos=self._redraw, size=self._redraw, value=self._redraw)

    def _redraw(self, *_args) -> None:
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
        ratio = min(1.0, max(0.0, self.value))
        self._fg_rect.pos = self.pos
        self._fg_rect.size = (self.width * ratio, self.height)


def text_input(input_filter: str | None = None, **kwargs) -> TextInput:
    kwargs.setdefault("font_name", FONT)
    kwargs.setdefault("font_size", sp(15))
    kwargs.setdefault("multiline", False)
    kwargs.setdefault("size_hint_y", None)
    kwargs.setdefault("height", dp(42))
    kwargs.setdefault("background_normal", "")
    kwargs.setdefault("background_active", "")
    kwargs.setdefault("background_color", FIELD)
    kwargs.setdefault("foreground_color", WHITE)
    kwargs.setdefault("cursor_color", WHITE)
    kwargs.setdefault("hint_text_color", DIM)
    kwargs.setdefault("padding", [dp(8), dp(10), dp(8), dp(8)])
    if input_filter:
        kwargs["input_filter"] = input_filter
    return TextInput(**kwargs)


def action_button(label: str, on_release, *, primary: bool = True, **kwargs) -> Button:
    kwargs.setdefault("size_hint_y", None)
    kwargs.setdefault("height", dp(46))
    kwargs.setdefault("font_name", FONT)
    kwargs.setdefault("font_size", sp(15))
    kwargs.setdefault("background_normal", "")
    kwargs.setdefault("background_down", "")
    kwargs.setdefault("background_color", PRIMARY if primary else BTN)
    kwargs.setdefault("color", WHITE)
    button = Button(text=label, **kwargs)
    button.bind(on_release=on_release)
    return button


def show_popup(title: str, message: str, *, confirm=None) -> None:
    """訊息／確認對話框；``confirm`` 為回呼時顯示「是／否」。"""
    content = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
    content.add_widget(WrapLabel(text=message, color=TEXT))
    popup = Popup(
        title=title,
        title_font=FONT,
        content=content,
        size_hint=(0.88, None),
        height=dp(220),
        background="",
        background_color=(0.15, 0.15, 0.15, 1),
        separator_color=PRIMARY,
    )

    if confirm is None:
        content.add_widget(action_button("好", lambda *_: popup.dismiss(), primary=True))
    else:
        row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
        row.add_widget(action_button("取消", lambda *_: popup.dismiss(), primary=False))

        def _yes(*_args) -> None:
            popup.dismiss()
            confirm()

        row.add_widget(action_button("確定", _yes, primary=True))
        content.add_widget(row)

    popup.open()


def form_row(label_text: str, widget: Widget) -> BoxLayout:
    """左標籤 + 右輸入框的一列。"""
    row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
    row.add_widget(
        LeftLabel(text=label_text, font_size=sp(14), size_hint_x=None, width=dp(104))
    )
    row.add_widget(widget)
    return row


def section_title(text: str) -> Label:
    return LeftLabel(
        text=text,
        font_size=sp(13),
        bold=True,
        color=ACCENT,
        size_hint_y=None,
        height=dp(34),
    )


class MainScreen(Screen):
    """主畫面：狀態、今日已賺、進度、本月累計。"""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(6))
        root.add_widget(
            Label(
                text="上班鼓励器",
                font_name=FONT,
                font_size=sp(24),
                bold=True,
                color=WHITE,
                size_hint_y=None,
                height=dp(46),
            )
        )

        top = BoxLayout(size_hint_y=None, height=dp(32), spacing=dp(8))
        self.date_label = Label(
            text="", font_name=FONT, font_size=sp(12), color=MUTED, halign="left", valign="middle"
        )
        self.time_label = Label(
            text="", font_name=FONT, font_size=sp(13), bold=True, color=WHITE,
            size_hint_x=None, width=dp(90), halign="center", valign="middle",
        )
        top.add_widget(self.date_label)
        top.add_widget(self.time_label)
        top.add_widget(
            action_button(
                "设置", self._open_settings, primary=False,
                size_hint_x=None, width=dp(84), height=dp(32), font_size=sp(12),
            )
        )
        root.add_widget(top)

        self.status_label = Label(
            text="上班中", font_name=FONT, font_size=sp(26), bold=True, color=ACCENT,
            size_hint_y=None, height=dp(44),
        )
        root.add_widget(self.status_label)

        self.countdown_label = Label(
            text="", font_name=FONT, font_size=sp(14), color=MUTED,
            size_hint_y=None, height=dp(26),
        )
        root.add_widget(self.countdown_label)

        card = BgBox(orientation="vertical", padding=[dp(10), dp(12)], spacing=dp(2),
                     size_hint_y=None, height=dp(150))
        card.add_widget(
            Label(text="今日已赚取", font_name=FONT, font_size=sp(15), color=MUTED,
                  size_hint_y=None, height=dp(24))
        )
        self.today_label = Label(
            text="$0.0000", font_name=FONT, font_size=sp(38), bold=True, color=MONEY,
            size_hint_y=None, height=dp(58),
        )
        card.add_widget(self.today_label)
        rates_row = BoxLayout(size_hint_y=None, height=dp(26), spacing=dp(10))
        self.speed_label = Label(text="速度: $0.000000/秒", font_name=FONT, font_size=sp(11),
                                 color=DIM)
        self.hourly_label = Label(text="时薪: $0.00", font_name=FONT, font_size=sp(11),
                                  bold=True, color=OK)
        rates_row.add_widget(self.speed_label)
        rates_row.add_widget(self.hourly_label)
        card.add_widget(rates_row)
        root.add_widget(card)

        self.target_label = WrapLabel(
            text="目标：暂无", font_size=sp(14), bold=True, color=WARN, size_hint_y=None,
            height=dp(28),
        )
        root.add_widget(self.target_label)

        self.progress_bar = Bar()
        root.add_widget(self.progress_bar)

        self.progress_label = Label(
            text="今日工时进度 0%", font_name=FONT, font_size=sp(11), color=MUTED,
            size_hint_y=None, height=dp(24),
        )
        root.add_widget(self.progress_label)

        month_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        month_row.add_widget(
            Label(text="本月累计", font_name=FONT, font_size=sp(15), color=TEXT,
                  size_hint_x=0.4, halign="left", valign="middle")
        )
        self.month_label = Label(
            text="$0.00", font_name=FONT, font_size=sp(22), bold=True, color=ACCENT,
            halign="left", valign="middle",
        )
        month_row.add_widget(self.month_label)
        root.add_widget(month_row)

        self.note_label = Label(
            text="(工時帳本)", font_name=FONT, font_size=sp(10), color=DIM,
            size_hint_y=None, height=dp(18),
        )
        root.add_widget(self.note_label)

        root.add_widget(
            action_button(
                "＋ 補登本月已過工作日", self._seed, primary=False,
                height=dp(36), font_size=sp(12),
            )
        )
        self.add_widget(root)

    # ---------- 事件 ----------
    def _open_settings(self, *_args) -> None:
        App.get_running_app().open_settings()

    def _seed(self, *_args) -> None:
        App.get_running_app().ask_seed()

    # ---------- 更新畫面 ----------
    def set_state(
        self,
        *,
        date_text: str,
        time_text: str,
        status: str,
        status_color,
        countdown: str,
        today_text: str,
        progress: float,
        progress_text: str,
        month_text: str,
        note_text: str,
        speed_text: str,
        hourly_text: str,
        target_text: str,
        target_color,
    ) -> None:
        self.date_label.text = date_text
        self.time_label.text = time_text
        self.status_label.text = status
        self.status_label.color = status_color
        self.countdown_label.text = countdown
        self.today_label.text = today_text
        self.progress_bar.value = progress
        self.progress_label.text = progress_text
        self.month_label.text = month_text
        self.note_label.text = note_text
        self.speed_label.text = speed_text
        self.hourly_label.text = hourly_text
        self.target_label.text = target_text
        self.target_label.color = target_color


class SettingsScreen(Screen):
    """設定畫面：月薪、工作天數、工時、五個心願目標。"""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.name = "settings"
        shell = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        shell.add_widget(
            Label(
                text="设置", font_name=FONT, font_size=sp(22), bold=True, color=WHITE,
                size_hint_y=None, height=dp(42),
            )
        )

        scroll = ScrollView(do_scroll_x=False)
        form = GridLayout(cols=1, spacing=dp(6), padding=[dp(4), dp(4)], size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))

        form.add_widget(section_title("薪資與天數"))
        self.salary_input = text_input(input_filter="float", hint_text="月薪 ($)")
        form.add_widget(form_row("月薪 ($)", self.salary_input))

        self.auto_check = CheckBox(
            active=True, size_hint=(None, None), size=(dp(30), dp(30)), color=ACCENT
        )
        self.auto_check.bind(active=self._toggle_auto)
        auto_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        auto_row.add_widget(self.auto_check)
        auto_row.add_widget(
            LeftLabel(text="自动计算当月工作日", font_size=sp(14))
        )
        form.add_widget(auto_row)

        self.days_input = text_input(input_filter="int", hint_text="当月工作天数")
        form.add_widget(form_row("工作天数", self.days_input))

        form.add_widget(section_title("時間設置 (HH:MM)"))
        self.start_input = text_input(hint_text="08:00")
        self.lunch_start_input = text_input(hint_text="12:00")
        self.lunch_end_input = text_input(hint_text="13:00")
        self.end_input = text_input(hint_text="18:00")
        form.add_widget(form_row("上班时间", self.start_input))
        form.add_widget(form_row("午休开始", self.lunch_start_input))
        form.add_widget(form_row("午休结束", self.lunch_end_input))
        form.add_widget(form_row("下班时间", self.end_input))

        form.add_widget(section_title("心願目標"))
        self.target_names = []
        self.target_amounts = []
        for index in range(5):
            row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
            name_input = text_input(hint_text=f"目標 {index + 1}")
            amount_input = text_input(input_filter="float", hint_text="金額")
            amount_input.size_hint_x = None
            amount_input.width = dp(96)
            self.target_names.append(name_input)
            self.target_amounts.append(amount_input)
            row.add_widget(name_input)
            row.add_widget(amount_input)
            form.add_widget(row)

        scroll.add_widget(form)
        shell.add_widget(scroll)

        bottom = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(8))
        bottom.add_widget(action_button("保存并应用", self._save))
        bottom.add_widget(action_button("返回", self._back, primary=False))
        shell.add_widget(bottom)
        self.add_widget(shell)
        self._auto_mode = True

    # ---------- 載入／收集 ----------
    def load_from(self, settings: core.Settings) -> None:
        self.salary_input.text = f"{settings.monthly_salary:g}"
        self.auto_check.active = settings.is_auto_days
        self._auto_mode = settings.is_auto_days
        now = datetime.now()
        if settings.is_auto_days:
            self.days_input.text = str(core.month_workdays(now.year, now.month))
            self.days_input.disabled = True
        else:
            self.days_input.text = str(settings.manual_days)
            self.days_input.disabled = False

        schedule = settings.schedule
        self.start_input.text = schedule.start_str
        self.lunch_start_input.text = schedule.lunch_start_str
        self.lunch_end_input.text = schedule.lunch_end_str
        self.end_input.text = schedule.end_str

        for index in range(5):
            if index < len(settings.targets):
                self.target_names[index].text = settings.targets[index].name
                self.target_amounts[index].text = f"{settings.targets[index].amount:g}"
            else:
                self.target_names[index].text = ""
                self.target_amounts[index].text = ""

    def _collect_targets(self):
        targets = []
        errors = []
        for index in range(5):
            name = self.target_names[index].text.strip()
            amount_text = self.target_amounts[index].text.strip()
            if not name and not amount_text:
                continue
            if not name:
                errors.append(f"第 {index + 1} 個目標填了金額但沒有名稱")
                continue
            if not amount_text:
                errors.append(f"第 {index + 1} 個目標「{name}」沒有填金額")
                continue
            try:
                amount = core.parse_positive_float(amount_text, f"第 {index + 1} 個目標的金額")
            except ValueError as exc:
                errors.append(str(exc))
                continue
            targets.append(core.Target(name, amount))
        return sorted(targets, key=lambda t: t.amount), errors

    # ---------- 事件 ----------
    def _toggle_auto(self, _checkbox, active: bool) -> None:
        self._auto_mode = active
        self.days_input.disabled = active
        if active:
            now = datetime.now()
            self.days_input.text = str(core.month_workdays(now.year, now.month))

    def _back(self, *_args) -> None:
        App.get_running_app().show_main()

    def _save(self, *_args) -> None:
        app = App.get_running_app()
        errors = []

        salary = app.settings.monthly_salary
        try:
            salary = core.parse_positive_float(self.salary_input.text, "月薪")
        except ValueError as exc:
            errors.append(str(exc))

        is_auto = bool(self.auto_check.active)
        work_days = app.settings.manual_days
        if is_auto:
            now = datetime.now()
            work_days = core.month_workdays(now.year, now.month)
        else:
            try:
                work_days = core.parse_int_in_range(self.days_input.text, "工作天數", 1, 31)
            except ValueError as exc:
                errors.append(str(exc))

        try:
            schedule = core.WorkSchedule(
                start=core.parse_hhmm(self.start_input.text),
                lunch_start=core.parse_hhmm(self.lunch_start_input.text),
                lunch_end=core.parse_hhmm(self.lunch_end_input.text),
                end=core.parse_hhmm(self.end_input.text),
            )
        except ValueError as exc:
            errors.append(str(exc))
            schedule = app.settings.schedule

        targets, target_errors = self._collect_targets()
        errors.extend(target_errors)

        if errors:
            show_popup("輸入錯誤", "請修正以下問題：\n\n" + "\n".join(f"• {e}" for e in errors))
            return

        app.apply_settings(
            core.Settings(
                monthly_salary=salary,
                is_auto_days=is_auto,
                manual_days=app.settings.manual_days if is_auto else work_days,
                schedule=schedule,
                targets=targets,
            )
        )
        app.show_main()
        show_popup("成功", "設置已更新！")


class WorkEncouragerApp(App):
    """應用程式本體：持有設定與帳本，每秒對齊整秒刷新。"""

    title = "上班鼓励器"
    FLUSH_INTERVAL_SECONDS = 60.0

    def __init__(self, data_dir: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._data_dir = data_dir
        self.store: core.Store | None = None
        self.settings: core.Settings | None = None
        self.ledger: core.Ledger | None = None
        self.sm: ScreenManager | None = None
        self.main_screen: MainScreen | None = None
        self.settings_screen: SettingsScreen | None = None
        self._event = None
        self._last_flush = datetime.now()
        self._rates_cache = None

    # ---------- 生命週期 ----------
    def build(self) -> ScreenManager:
        Window.clearcolor = BG
        base = Path(self._data_dir) if self._data_dir else Path(self.user_data_dir)
        self.store = core.Store(base)
        self.settings = self.store.load_settings()
        self.ledger = core.Ledger(self.store)

        self.sm = ScreenManager(transition=SlideTransition(duration=0.12))
        self.main_screen = MainScreen(name="main")
        self.settings_screen = SettingsScreen()
        self.sm.add_widget(self.main_screen)
        self.sm.add_widget(self.settings_screen)
        return self.sm

    def on_start(self) -> None:
        Window.bind(on_keyboard=self._on_keyboard)
        self._tick(0)
        shot = os.environ.get("WE_SHOT")
        if shot:
            if os.environ.get("WE_SHOT_SCREEN") == "settings":
                Clock.schedule_once(lambda _dt: self.open_settings(), 0.4)
            Clock.schedule_once(lambda _dt: self._screenshot(shot), 1.2)

    def on_stop(self) -> None:
        self._flush()

    def _screenshot(self, path: str) -> None:
        try:
            Clock.schedule_once(lambda _dt: self.stop(), 0.3)
            Window.screenshot(name=path)
        except Exception:  # pragma: no cover - 僅測試用
            self.stop()

    def _on_keyboard(self, _window, key, *_args) -> bool:
        if key == 27 and self.sm.current != "main":  # Android 返回鍵
            self.show_main()
            return True
        return False

    # ---------- 畫面切換 ----------
    def show_main(self) -> None:
        self.sm.current = "main"

    def open_settings(self) -> None:
        self.settings_screen.load_from(self.settings)
        self.sm.current = "settings"

    # ---------- 設定套用 ----------
    def apply_settings(self, settings: core.Settings) -> None:
        self.settings = settings
        self._rates_cache = None
        try:
            self.store.save_settings(settings)
        except OSError as exc:
            show_popup("設定未保存", f"設定已套用，但寫入設定檔失敗：\n{exc}")
        self._refresh(datetime.now())

    # ---------- 補登 ----------
    def ask_seed(self) -> None:
        now = datetime.now()
        pending = [
            day for day in range(1, now.day) if datetime(now.year, now.month, day).weekday() < 5
        ]
        if not pending:
            show_popup("補登", "本月目前沒有需要補登的已過工作日。")
            return
        count = min(len(pending), self._workdays(now))
        hours = self.settings.schedule.total_seconds / 3600

        def _do_seed() -> None:
            core.seed_past_workdays(self.ledger, self.settings, now, self._workdays(now))
            self._flush()
            self._refresh(datetime.now())

        show_popup(
            "補登本月工時",
            f"將把 {now.month} 月的 {count} 個已過工作日補登為滿勤（每日 {hours:.1f} 小時）。\n"
            "之後仍以實際記錄為準。",
            confirm=_do_seed,
        )

    # ---------- 計算 ----------
    def _workdays(self, now: datetime) -> int:
        if self.settings.is_auto_days:
            return core.month_workdays(now.year, now.month)
        return self.settings.manual_days

    def _rates(self, now: datetime) -> core.Rates:
        key = (
            round(self.settings.monthly_salary, 6),
            self._workdays(now),
            self.settings.schedule.total_seconds,
        )
        if self._rates_cache and self._rates_cache[0] == key:
            return self._rates_cache[1]
        rates = core.Rates(
            monthly_salary=self.settings.monthly_salary,
            workdays=key[1],
            daily_seconds=key[2],
        )
        self._rates_cache = (key, rates)
        return rates

    def _phase_display(self, now: datetime):
        schedule = self.settings.schedule
        phase = schedule.phase(now)
        if phase == "before":
            remaining = datetime.combine(now.date(), schedule.start) - now
            return "还未上班", WARN, f"距离上班还有 {core.format_seconds(remaining.total_seconds())}"
        if phase in ("am", "pm"):
            remaining = datetime.combine(now.date(), schedule.end) - now
            return "上班中", OK, f"距离下班还有 {core.format_seconds(remaining.total_seconds())}"
        if phase == "lunch":
            remaining = datetime.combine(now.date(), schedule.lunch_end) - now
            return "午休中", ACCENT, f"距离下午上班还有 {core.format_seconds(remaining.total_seconds())}"
        return "已下班", OK, "今日任务已完成！"

    def _target_display(self, today_earned: float):
        targets = self.settings.targets
        if not targets:
            return "目标：暂无，请在设置中添加", DIM
        affordable = None
        upcoming = None
        for target in targets:
            if today_earned >= target.amount:
                affordable = target
            else:
                upcoming = target
                break
        if upcoming is not None:
            return f"距离买入 [{upcoming.name}] 还差 ${upcoming.amount - today_earned:.2f}", WARN
        if affordable is not None:
            return f"恭喜！今日已赚够买入：{affordable.name}", OK
        return "目标：暂无", DIM

    # ---------- 更新迴圈 ----------
    def _tick(self, _dt) -> None:
        self._refresh(datetime.now())
        now = datetime.now()
        delay = max(0.05, 1.0 - now.microsecond / 1_000_000)
        self._event = Clock.schedule_once(self._tick, delay)

    def _refresh(self, now: datetime) -> None:
        schedule = self.settings.schedule
        rates = self._rates(now)
        weekdays = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")

        if now.weekday() < 5:
            worked = schedule.worked_seconds(now)
            self.ledger.record(now.strftime(core.DAY_FMT), worked)
            status, status_color, countdown = self._phase_display(now)
            today_earned = worked * rates.per_second
            ratio = worked / schedule.total_seconds
            progress_text = (
                f"今日工时进度 {ratio * 100:.1f}% "
                f"(已工作 {worked / 3600:.2f}h / {schedule.total_seconds / 3600:.2f}h)"
            )
            today_text = f"${today_earned:.4f}"
            target_text, target_color = self._target_display(today_earned)
        else:
            worked = 0
            today_earned = 0.0
            status, status_color, countdown = "休息日", REST, "好好休息，享受生活！"
            ratio = 0.0
            progress_text = "今日工时进度 0%"
            today_text = "$0.0000"
            target_text, target_color = "休息日不計工資", DIM

        month_seconds, estimated_days = core.month_seconds_estimate(
            self.ledger, schedule, now, self._workdays(now)
        )
        month_text = f"${month_seconds * rates.per_second:.2f}"
        if estimated_days:
            note_text = f"(工時帳本 · 含 {estimated_days} 天滿勤估算)"
        elif self.ledger.first_record_in_month(now.year, now.month) is None:
            note_text = "(工時帳本 · 尚無記錄)"
        else:
            note_text = "(工時帳本 · 本月完整記錄)"

        self.main_screen.set_state(
            date_text=now.strftime(f"%Y-%m-%d {weekdays[now.weekday()]}"),
            time_text=now.strftime("%H:%M:%S"),
            status=status,
            status_color=status_color,
            countdown=countdown,
            today_text=today_text,
            progress=ratio,
            progress_text=progress_text,
            month_text=month_text,
            note_text=note_text,
            speed_text=f"速度: ${rates.per_second:.6f}/秒",
            hourly_text=f"时薪: ${rates.hourly:.2f}",
            target_text=target_text,
            target_color=target_color,
        )

        if (now - self._last_flush).total_seconds() >= self.FLUSH_INTERVAL_SECONDS:
            self._last_flush = now
            self._flush()

    def _flush(self) -> None:
        try:
            self.ledger.flush()
        except OSError:
            pass


if __name__ == "__main__":
    if hasattr(Window, "softinput_mode"):
        Window.softinput_mode = "below_target"
    WorkEncouragerApp(data_dir=os.environ.get("WE_DATA_DIR")).run()
