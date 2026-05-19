from __future__ import annotations

import os
import time
from typing import Dict, Optional

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.storage.jsonstore import JsonStore
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import FadeTransition, Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.slider import Slider
from kivy.utils import platform

from app_config import APP_NAME, APP_SUBTITLE, BLUETOOTH_DEVICE_NAME, TAGLINE, VERSION
from audio_service import AudioService
from bluetooth_service import BluetoothService
from parser import parse_sensor_line
from permissions_helper import request_android_permissions
from warning_engine import WarningEngine

# Desktop preview only. Never force window size on Android.
if platform != "android":
    Window.size = (390, 844)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATHS = [
    os.path.join(BASE_DIR, "logo.png"),
    os.path.join(BASE_DIR, "assets", "logo.png"),
    os.path.join(BASE_DIR, "assets", "icon.png"),
]


def logo_path() -> Optional[str]:
    for path in LOGO_PATHS:
        if os.path.exists(path):
            return path
    return None


def rgba(hex_color: str):
    value = hex_color.replace("#", "").strip()
    return (
        int(value[0:2], 16) / 255.0,
        int(value[2:4], 16) / 255.0,
        int(value[4:6], 16) / 255.0,
        1,
    )


THEMES = {
    "dark": {
        "bg": "#050B18",
        "surface": "#0D1B2A",
        "surface2": "#102235",
        "card": "#111F33",
        "card2": "#162A42",
        "text": "#F8FAFC",
        "muted": "#9CAFC3",
        "primary": "#21D4D0",
        "primary2": "#38BDF8",
        "purple": "#8B5CF6",
        "amber": "#FFC857",
        "coral": "#FF6B6B",
        "danger": "#FF4D5A",
        "white": "#FFFFFF",
    },
    "light": {
        "bg": "#F7FAFC",
        "surface": "#FFFFFF",
        "surface2": "#EEF5F7",
        "card": "#FFFFFF",
        "card2": "#F2F7FA",
        "text": "#0D1B2A",
        "muted": "#526171",
        "primary": "#0EA5A1",
        "primary2": "#0284C7",
        "purple": "#7C3AED",
        "amber": "#F7B731",
        "coral": "#FF6B6B",
        "danger": "#E5484D",
        "white": "#FFFFFF",
    },
}

DIRECTION_LABELS = {"F": "Урд", "L": "Зүүн", "R": "Баруун", "B": "Ард"}
DIRECTION_BADGES = {"F": "F", "L": "L", "R": "R", "B": "B"}


class AuraLabel(Label):
    def __init__(
        self,
        text: str = "",
        font_size: int = 16,
        bold: bool = False,
        color_hex: str = "#FFFFFF",
        halign: str = "left",
        valign: str = "middle",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.text = text
        self.font_size = sp(font_size)
        self.bold = bold
        self.color = rgba(color_hex)
        self.halign = halign
        self.valign = valign
        self.shorten = False
        self.bind(size=self._update_text_size)

    def _update_text_size(self, *_):
        self.text_size = self.size

    def set_color(self, hex_color: str):
        self.color = rgba(hex_color)


class Card(BoxLayout):
    def __init__(self, bg: str = "#111F33", radius: int = 24, **kwargs):
        super().__init__(**kwargs)
        self.bg = bg
        self.radius = radius
        with self.canvas.before:
            self._canvas_color = Color(*rgba(self.bg))
            self._canvas_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(self.radius)],
            )
        self.bind(pos=self._update_canvas, size=self._update_canvas)

    def _update_canvas(self, *_):
        self._canvas_rect.pos = self.pos
        self._canvas_rect.size = self.size

    def set_bg(self, hex_color: str):
        self.bg = hex_color
        self._canvas_color.rgba = rgba(hex_color)


class AuraButton(Button):
    def __init__(self, text: str = "", bg: str = "#0EA5A1", fg: str = "#FFFFFF", font_size: int = 14, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.background_normal = ""
        self.background_down = ""
        self.background_color = rgba(bg)
        self.color = rgba(fg)
        self.font_size = sp(font_size)
        self.bold = True

    def set_colors(self, bg: str, fg: str):
        self.background_color = rgba(bg)
        self.color = rgba(fg)


class SensorCard(Card):
    def __init__(self, app_ref, direction: str, **kwargs):
        super().__init__(orientation="vertical", radius=22, **kwargs)
        self.app_ref = app_ref
        self.direction = direction
        self.padding = [dp(14), dp(12), dp(14), dp(12)]
        self.spacing = dp(4)
        self.size_hint_y = None
        self.height = dp(112)

        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(30), spacing=dp(8))
        self.badge = AuraButton(DIRECTION_BADGES[direction], size_hint_x=None, width=dp(34), font_size=14)
        self.title = AuraLabel(DIRECTION_LABELS[direction], font_size=17, bold=True)
        header.add_widget(self.badge)
        header.add_widget(self.title)

        self.value = AuraLabel("— см", font_size=28, bold=True, size_hint_y=None, height=dp(42))
        self.status = AuraLabel("Холболтгүй", font_size=12, bold=True, size_hint_y=None, height=dp(24))

        self.add_widget(header)
        self.add_widget(self.value)
        self.add_widget(self.status)

    def update_theme(self):
        t = self.app_ref.theme
        self.set_bg(t["card"])
        self.badge.set_colors(t["surface2"], t["primary"])
        self.title.set_color(t["text"])
        self.value.set_color(t["text"])
        self.status.set_color(t["muted"])

    def set_state(self, distance: Optional[int], severity: str):
        t = self.app_ref.theme
        if distance is None:
            self.value.text = "— см"
            self.status.text = "Холболтгүй"
            self.status.set_color(t["muted"])
            self.set_bg(t["card"])
            self.badge.set_colors(t["surface2"], t["primary"])
            return

        self.value.text = f"{distance} см"
        if severity == "safe":
            self.status.text = "Аюулгүй"
            self.status.set_color(t["primary"])
            self.set_bg(t["card"])
            self.badge.set_colors(t["surface2"], t["primary"])
        elif severity == "warning":
            self.status.text = "Саад"
            self.status.set_color(t["amber"])
            self.set_bg(t["card2"])
            self.badge.set_colors(t["amber"], t["bg"])
        elif severity == "critical":
            self.status.text = "Ойр"
            self.status.set_color(t["coral"])
            self.set_bg(t["card2"])
            self.badge.set_colors(t["coral"], t["white"])
        elif severity == "very_close":
            self.status.text = "Маш ойр"
            self.status.set_color(t["danger"])
            self.set_bg(t["card2"])
            self.badge.set_colors(t["danger"], t["white"])
        else:
            self.status.text = "Холболтгүй"
            self.status.set_color(t["muted"])
            self.set_bg(t["card"])


class SplashScreen(Screen):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = app_ref
        self.logo_source = logo_path()
        self.root = Card(orientation="vertical", radius=0)
        self.root.padding = [dp(26), dp(42), dp(26), dp(30)]
        self.root.spacing = dp(10)
        self.add_widget(self.root)

        self.root.add_widget(BoxLayout(size_hint_y=0.12))
        if self.logo_source:
            self.logo = Image(source=self.logo_source, size_hint_y=None, height=dp(310), allow_stretch=True, keep_ratio=True)
            self.root.add_widget(self.logo)
        else:
            self.logo_text = AuraLabel("AURA", font_size=52, bold=True, halign="center", size_hint_y=None, height=dp(240))
            self.root.add_widget(self.logo_text)

        self.title = AuraLabel(APP_NAME, font_size=36, bold=True, halign="center", size_hint_y=None, height=dp(52))
        self.subtitle = AuraLabel(APP_SUBTITLE, font_size=16, halign="center", size_hint_y=None, height=dp(28))
        self.tagline = AuraLabel(TAGLINE, font_size=16, halign="center", size_hint_y=None, height=dp(32))
        self.root.add_widget(self.title)
        self.root.add_widget(self.subtitle)
        self.root.add_widget(self.tagline)
        self.root.add_widget(BoxLayout(size_hint_y=1))

        self.loading_text = AuraLabel("Ачаалж байна...", font_size=14, halign="center", size_hint_y=None, height=dp(28))
        self.progress = Card(radius=4, size_hint_y=None, height=dp(8), orientation="horizontal")
        self.progress.padding = 0
        self.progress_fill = Card(radius=4, size_hint_x=0.45)
        self.progress.add_widget(self.progress_fill)
        self.progress.add_widget(BoxLayout())
        self.root.add_widget(self.loading_text)
        self.root.add_widget(self.progress)

    def on_pre_enter(self):
        self.update_theme()
        Clock.schedule_once(lambda *_: self.app_ref.show_dashboard(), 1.25)

    def update_theme(self):
        t = self.app_ref.theme
        self.root.set_bg(t["bg"])
        self.title.set_color(t["text"])
        self.subtitle.set_color(t["muted"])
        self.tagline.set_color(t["primary"])
        self.loading_text.set_color(t["muted"])
        self.progress.set_bg(t["surface2"])
        self.progress_fill.set_bg(t["primary"])
        if hasattr(self, "logo_text"):
            self.logo_text.set_color(t["primary"])


class DashboardScreen(Screen):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = app_ref
        self.logo_source = logo_path()

        self.outer = Card(orientation="vertical", radius=0)
        self.add_widget(self.outer)
        self.scroll = ScrollView(do_scroll_x=False)
        self.content = BoxLayout(orientation="vertical", size_hint_y=None, padding=[dp(16), dp(18), dp(16), dp(16)], spacing=dp(12))
        self.content.bind(minimum_height=self.content.setter("height"))
        self.scroll.add_widget(self.content)
        self.outer.add_widget(self.scroll)

        self._build_header()
        self._build_bluetooth_card()
        self._build_warning_card()
        self._build_sensor_grid()
        self._build_actions()

    def _build_header(self):
        self.header = BoxLayout(size_hint_y=None, height=dp(82), spacing=dp(10))
        left = BoxLayout(orientation="horizontal", spacing=dp(10))
        if self.logo_source:
            self.logo = Image(source=self.logo_source, size_hint_x=None, width=dp(64), allow_stretch=True, keep_ratio=True)
            left.add_widget(self.logo)
        title_box = BoxLayout(orientation="vertical")
        self.title = AuraLabel(APP_NAME, font_size=23, bold=True)
        self.subtitle = AuraLabel(APP_SUBTITLE, font_size=12)
        title_box.add_widget(self.title)
        title_box.add_widget(self.subtitle)
        left.add_widget(title_box)

        right = BoxLayout(orientation="vertical", size_hint_x=None, width=dp(98), spacing=dp(8))
        self.status = AuraButton("OFFLINE", font_size=11, size_hint_y=None, height=dp(34))
        self.theme_button = AuraButton("LIGHT", font_size=11, size_hint_y=None, height=dp(34))
        self.theme_button.bind(on_release=lambda *_: self.app_ref.toggle_theme())
        right.add_widget(self.status)
        right.add_widget(self.theme_button)
        self.header.add_widget(left)
        self.header.add_widget(right)
        self.content.add_widget(self.header)

    def _build_bluetooth_card(self):
        self.bt_card = Card(orientation="horizontal", radius=26, size_hint_y=None, height=dp(92))
        self.bt_card.padding = [dp(16), dp(14), dp(16), dp(14)]
        self.bt_card.spacing = dp(12)
        self.bt_badge = AuraButton("BT", size_hint_x=None, width=dp(58), font_size=16)
        text_box = BoxLayout(orientation="vertical")
        self.bt_title = AuraLabel("Bluetooth", font_size=17, bold=True)
        self.bt_status = AuraLabel("Холбогдоогүй", font_size=14)
        self.bt_note = AuraLabel("HC-05 pair хийгээд холбоно", font_size=12)
        text_box.add_widget(self.bt_title)
        text_box.add_widget(self.bt_status)
        text_box.add_widget(self.bt_note)
        self.bt_card.add_widget(self.bt_badge)
        self.bt_card.add_widget(text_box)
        self.content.add_widget(self.bt_card)

    def _build_warning_card(self):
        self.warning_card = Card(orientation="vertical", radius=30, size_hint_y=None, height=dp(178))
        self.warning_card.padding = [dp(18), dp(16), dp(18), dp(16)]
        self.warning_card.spacing = dp(5)
        self.warning_label = AuraLabel("ОДООГИЙН АНХААРУУЛГА", font_size=12, bold=True, size_hint_y=None, height=dp(24))
        self.warning_message = AuraLabel("Одоогоор Bluetooth\nхолбогдоогүй байна", font_size=25, bold=True)
        self.warning_distance = AuraLabel("—", font_size=45, bold=True, halign="center", size_hint_y=None, height=dp(60))
        self.warning_card.add_widget(self.warning_label)
        self.warning_card.add_widget(self.warning_message)
        self.warning_card.add_widget(self.warning_distance)
        self.content.add_widget(self.warning_card)

    def _build_sensor_grid(self):
        self.sensor_grid = GridLayout(cols=2, spacing=dp(10), size_hint_y=None, height=dp(234))
        self.sensor_cards: Dict[str, SensorCard] = {}
        for key in ["F", "L", "R", "B"]:
            card = SensorCard(self.app_ref, key)
            self.sensor_cards[key] = card
            self.sensor_grid.add_widget(card)
        self.content.add_widget(self.sensor_grid)

    def _build_actions(self):
        self.actions = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None, height=dp(118))
        row = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(54))
        self.connect_btn = AuraButton("HC-05 ХОЛБОХ", font_size=13)
        self.disconnect_btn = AuraButton("САЛГАХ", font_size=13)
        self.connect_btn.bind(on_release=lambda *_: self.app_ref.connect_bluetooth())
        self.disconnect_btn.bind(on_release=lambda *_: self.app_ref.disconnect_bluetooth())
        row.add_widget(self.connect_btn)
        row.add_widget(self.disconnect_btn)
        self.settings_btn = AuraButton("ТОХИРГОО", font_size=14, size_hint_y=None, height=dp(54))
        self.settings_btn.bind(on_release=lambda *_: self.app_ref.show_settings())
        self.actions.add_widget(row)
        self.actions.add_widget(self.settings_btn)
        self.content.add_widget(self.actions)

    def update_theme(self):
        t = self.app_ref.theme
        self.outer.set_bg(t["bg"])
        self.title.set_color(t["text"])
        self.subtitle.set_color(t["muted"])
        self.status.set_colors(t["surface2"], t["primary"] if self.app_ref.connected else t["muted"])
        self.status.text = "LIVE" if self.app_ref.connected else "OFFLINE"
        self.theme_button.text = "LIGHT" if self.app_ref.theme_name == "dark" else "DARK"
        self.theme_button.set_colors(t["surface"], t["primary"])

        self.bt_card.set_bg(t["surface"])
        self.bt_badge.set_colors(t["primary"], t["white"])
        self.bt_title.set_color(t["text"])
        self.bt_status.set_color(t["primary"] if self.app_ref.connected else t["muted"])
        self.bt_note.set_color(t["muted"])

        self.warning_label.set_color(t["primary"])
        self.warning_message.set_color(t["text"])
        self.warning_distance.set_color(t["text"])

        self.connect_btn.set_colors(t["primary"], t["white"])
        self.disconnect_btn.set_colors(t["surface2"], t["danger"])
        self.settings_btn.set_colors(t["surface2"], t["text"])

        for card in self.sensor_cards.values():
            card.update_theme()
        self.refresh()

    def refresh(self):
        t = self.app_ref.theme
        self.status.text = "LIVE" if self.app_ref.connected else "OFFLINE"
        self.status.set_colors(t["primary"] if self.app_ref.connected else t["surface2"], t["white"] if self.app_ref.connected else t["muted"])
        self.bt_status.text = self.app_ref.bluetooth_message
        self.bt_status.set_color(t["primary"] if self.app_ref.connected else t["muted"])

        warning = self.app_ref.current_warning
        sev = str(warning.get("severity", "disconnected"))
        if not self.app_ref.connected:
            self.warning_message.text = "Одоогоор Bluetooth\nхолбогдоогүй байна"
            self.warning_distance.text = "—"
            self.warning_card.set_bg(t["surface2"])
        else:
            self.warning_message.text = str(warning.get("message") or "Одоогоор ойр саад алга")
            dist = warning.get("distance")
            self.warning_distance.text = f"{dist} см" if isinstance(dist, int) else "—"
            if sev == "safe":
                self.warning_card.set_bg(t["primary"])
                self.warning_message.set_color(t["white"])
                self.warning_distance.set_color(t["white"])
            elif sev == "warning":
                self.warning_card.set_bg(t["amber"])
                self.warning_message.set_color(t["bg"])
                self.warning_distance.set_color(t["bg"])
            elif sev in ("critical", "very_close"):
                self.warning_card.set_bg(t["coral"] if sev == "critical" else t["danger"])
                self.warning_message.set_color(t["white"])
                self.warning_distance.set_color(t["white"])
            else:
                self.warning_card.set_bg(t["surface2"])
                self.warning_message.set_color(t["text"])
                self.warning_distance.set_color(t["text"])

        for key, card in self.sensor_cards.items():
            value = self.app_ref.distances.get(key)
            if not self.app_ref.connected or value is None:
                card.set_state(None, "no_data")
            else:
                card.set_state(value, self.app_ref.engine.severity_for_distance(value))


class SettingsScreen(Screen):
    def __init__(self, app_ref, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = app_ref
        self.outer = Card(orientation="vertical", radius=0)
        self.add_widget(self.outer)
        self.scroll = ScrollView(do_scroll_x=False)
        self.content = BoxLayout(orientation="vertical", size_hint_y=None, padding=[dp(16), dp(18), dp(16), dp(16)], spacing=dp(12))
        self.content.bind(minimum_height=self.content.setter("height"))
        self.scroll.add_widget(self.content)
        self.outer.add_widget(self.scroll)
        self._build()

    def _build(self):
        header = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(10))
        self.back_btn = AuraButton("Буцах", size_hint_x=None, width=dp(94), font_size=13)
        self.back_btn.bind(on_release=lambda *_: self.app_ref.show_dashboard())
        self.title = AuraLabel("Тохиргоо", font_size=25, bold=True)
        header.add_widget(self.back_btn)
        header.add_widget(self.title)
        self.content.add_widget(header)

        self.theme_card = self._card(118)
        self.theme_title = AuraLabel("Горим", font_size=18, bold=True, size_hint_y=None, height=dp(30))
        row = BoxLayout(spacing=dp(8))
        self.dark_btn = AuraButton("Dark mode", font_size=13)
        self.light_btn = AuraButton("Light mode", font_size=13)
        self.dark_btn.bind(on_release=lambda *_: self.app_ref.set_theme("dark"))
        self.light_btn.bind(on_release=lambda *_: self.app_ref.set_theme("light"))
        row.add_widget(self.dark_btn)
        row.add_widget(self.light_btn)
        self.theme_card.add_widget(self.theme_title)
        self.theme_card.add_widget(row)

        self.audio_card = self._card(132)
        top = BoxLayout(size_hint_y=None, height=dp(32))
        self.audio_title = AuraLabel("Дууны тохиргоо", font_size=18, bold=True)
        self.audio_value = AuraLabel("80%", font_size=14, bold=True, halign="right", size_hint_x=None, width=dp(64))
        top.add_widget(self.audio_title)
        top.add_widget(self.audio_value)
        self.audio_sub = AuraLabel("Дууны түвшин", font_size=14, size_hint_y=None, height=dp(26))
        self.audio_slider = Slider(min=0, max=100, value=80)
        self.audio_slider.bind(value=self._volume_changed)
        self.audio_card.add_widget(top)
        self.audio_card.add_widget(self.audio_sub)
        self.audio_card.add_widget(self.audio_slider)

        self.sens_card = self._card(118)
        self.sens_title = AuraLabel("Анхааруулгын мэдрэмж", font_size=18, bold=True, size_hint_y=None, height=dp(30))
        sens_row = BoxLayout(spacing=dp(8))
        self.low_btn = AuraButton("Бага", font_size=13)
        self.mid_btn = AuraButton("Дундаж", font_size=13)
        self.high_btn = AuraButton("Өндөр", font_size=13)
        self.low_btn.bind(on_release=lambda *_: self.app_ref.set_sensitivity("low"))
        self.mid_btn.bind(on_release=lambda *_: self.app_ref.set_sensitivity("normal"))
        self.high_btn.bind(on_release=lambda *_: self.app_ref.set_sensitivity("high"))
        sens_row.add_widget(self.low_btn)
        sens_row.add_widget(self.mid_btn)
        sens_row.add_widget(self.high_btn)
        self.sens_card.add_widget(self.sens_title)
        self.sens_card.add_widget(sens_row)

        self.bt_card = self._card(126)
        self.bt_title = AuraLabel("Bluetooth төхөөрөмж", font_size=18, bold=True, size_hint_y=None, height=dp(30))
        self.bt_status = AuraLabel("Холбогдоогүй", font_size=14, size_hint_y=None, height=dp(28))
        self.reconnect_btn = AuraButton("Дахин холбох", font_size=13, size_hint_y=None, height=dp(48))
        self.reconnect_btn.bind(on_release=lambda *_: self.app_ref.connect_bluetooth())
        self.bt_card.add_widget(self.bt_title)
        self.bt_card.add_widget(self.bt_status)
        self.bt_card.add_widget(self.reconnect_btn)

        self.info_card = self._card(168)
        self.info_title = AuraLabel("Апп мэдээлэл", font_size=18, bold=True, size_hint_y=None, height=dp(30))
        self.info_1 = AuraLabel(APP_NAME, font_size=20, bold=True, size_hint_y=None, height=dp(32))
        self.info_2 = AuraLabel(APP_SUBTITLE, font_size=14, size_hint_y=None, height=dp(26))
        self.info_3 = AuraLabel(TAGLINE, font_size=14, size_hint_y=None, height=dp(26))
        self.info_4 = AuraLabel(f"Version {VERSION}", font_size=13, size_hint_y=None, height=dp(24))
        for w in [self.info_title, self.info_1, self.info_2, self.info_3, self.info_4]:
            self.info_card.add_widget(w)

    def _card(self, height: int) -> Card:
        card = Card(orientation="vertical", radius=24, size_hint_y=None, height=dp(height))
        card.padding = [dp(16), dp(14), dp(16), dp(14)]
        card.spacing = dp(8)
        self.content.add_widget(card)
        return card

    def _volume_changed(self, _slider, value):
        self.app_ref.volume = int(value)
        self.audio_value.text = f"{int(value)}%"
        self.app_ref.audio.set_volume(value / 100.0)

    def update_theme(self):
        t = self.app_ref.theme
        self.outer.set_bg(t["bg"])
        self.back_btn.set_colors(t["surface2"], t["text"])
        self.title.set_color(t["text"])
        for card in [self.theme_card, self.audio_card, self.sens_card, self.bt_card, self.info_card]:
            card.set_bg(t["surface"])
        for label in [self.theme_title, self.audio_title, self.audio_value, self.sens_title, self.bt_title, self.info_title, self.info_1]:
            label.set_color(t["text"])
        for label in [self.audio_sub, self.bt_status, self.info_2, self.info_4]:
            label.set_color(t["muted"])
        self.info_3.set_color(t["primary"])
        self.bt_status.text = self.app_ref.bluetooth_message
        self.bt_status.set_color(t["primary"] if self.app_ref.connected else t["muted"])
        self.reconnect_btn.set_colors(t["primary"], t["white"])
        self._update_segment_buttons()

    def _update_segment_buttons(self):
        t = self.app_ref.theme
        self.dark_btn.set_colors(t["primary"] if self.app_ref.theme_name == "dark" else t["surface2"], t["white"] if self.app_ref.theme_name == "dark" else t["muted"])
        self.light_btn.set_colors(t["primary"] if self.app_ref.theme_name == "light" else t["surface2"], t["white"] if self.app_ref.theme_name == "light" else t["muted"])
        for name, btn in [("low", self.low_btn), ("normal", self.mid_btn), ("high", self.high_btn)]:
            btn.set_colors(t["primary"] if self.app_ref.sensitivity == name else t["surface2"], t["white"] if self.app_ref.sensitivity == name else t["muted"])


class AuraGuideApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = APP_NAME
        self.theme_name = "dark"
        self.theme = THEMES[self.theme_name]
        self.connected = False
        self.bluetooth_message = "Холбогдоогүй"
        self.distances: Dict[str, Optional[int]] = {"F": None, "L": None, "R": None, "B": None}
        self.current_warning = {"direction": None, "distance": None, "severity": "disconnected", "message": "Одоогоор Bluetooth холбогдоогүй байна"}
        self.last_audio_time = 0.0
        self.volume = 80
        self.sensitivity = "normal"
        self.store: Optional[JsonStore] = None
        self.engine = WarningEngine()
        self.audio = AudioService()
        self.bluetooth = BluetoothService(on_data=self.on_bluetooth_data, on_status=self.on_bluetooth_status, device_name=BLUETOOTH_DEVICE_NAME)

    def build(self):
        request_android_permissions()
        self._load_settings()
        self.sm = ScreenManager(transition=FadeTransition(duration=0.16))
        self.splash = SplashScreen(self, name="splash")
        self.dashboard = DashboardScreen(self, name="dashboard")
        self.settings = SettingsScreen(self, name="settings")
        self.sm.add_widget(self.splash)
        self.sm.add_widget(self.dashboard)
        self.sm.add_widget(self.settings)
        self.apply_theme()
        return self.sm

    def _load_settings(self):
        try:
            self.store = JsonStore(os.path.join(BASE_DIR, "aura_settings.json"))
            if self.store.exists("ui"):
                data = self.store.get("ui")
                if data.get("theme") in THEMES:
                    self.theme_name = data.get("theme")
                if data.get("sensitivity") in {"low", "normal", "high"}:
                    self.sensitivity = data.get("sensitivity")
        except Exception:
            pass
        self.theme = THEMES[self.theme_name]
        self.engine.set_sensitivity(self.sensitivity)

    def _save_settings(self):
        try:
            if self.store:
                self.store.put("ui", theme=self.theme_name, sensitivity=self.sensitivity)
        except Exception:
            pass

    def show_dashboard(self):
        self.sm.current = "dashboard"
        self.dashboard.update_theme()

    def show_settings(self):
        self.sm.current = "settings"
        self.settings.update_theme()

    def set_theme(self, theme_name: str):
        if theme_name not in THEMES:
            return
        self.theme_name = theme_name
        self.theme = THEMES[theme_name]
        self._save_settings()
        self.apply_theme()

    def toggle_theme(self):
        self.set_theme("light" if self.theme_name == "dark" else "dark")

    def apply_theme(self):
        self.theme = THEMES[self.theme_name]
        Window.clearcolor = rgba(self.theme["bg"])
        if hasattr(self, "splash"):
            self.splash.update_theme()
        if hasattr(self, "dashboard"):
            self.dashboard.update_theme()
        if hasattr(self, "settings"):
            self.settings.update_theme()

    def set_sensitivity(self, value: str):
        self.sensitivity = value
        self.engine.set_sensitivity(value)
        self._save_settings()
        self._recalculate_warning()
        if hasattr(self, "dashboard"):
            self.dashboard.refresh()
        if hasattr(self, "settings"):
            self.settings.update_theme()

    def connect_bluetooth(self):
        self.bluetooth_message = "Холбогдож байна..."
        if hasattr(self, "dashboard"):
            self.dashboard.refresh()
        try:
            self.bluetooth.connect()
        except Exception as exc:
            self.on_bluetooth_status("error", f"Bluetooth алдаа: {exc}")

    def disconnect_bluetooth(self):
        try:
            self.bluetooth.disconnect()
        except Exception:
            pass
        self.on_bluetooth_status("disconnected", "Холбогдоогүй")

    def on_bluetooth_status(self, status: str, message: str = ""):
        self.connected = status == "connected"
        self.bluetooth_message = message or ("HC-05 холбогдсон" if self.connected else "Холбогдоогүй")
        if not self.connected:
            self.distances = {"F": None, "L": None, "R": None, "B": None}
        self._recalculate_warning()
        if hasattr(self, "dashboard"):
            self.dashboard.refresh()
        if hasattr(self, "settings"):
            self.settings.update_theme()

    def on_bluetooth_data(self, line: str):
        values = parse_sensor_line(line)
        if not values:
            return
        for key in ["F", "L", "R", "B"]:
            if key in values:
                self.distances[key] = values[key]
        self.connected = True
        self.bluetooth_message = "HC-05 холбогдсон"
        self._recalculate_warning()
        if hasattr(self, "dashboard"):
            self.dashboard.refresh()
        self._maybe_speak()

    def _recalculate_warning(self):
        if not self.connected:
            self.current_warning = {"direction": None, "distance": None, "severity": "disconnected", "message": "Одоогоор Bluetooth холбогдоогүй байна"}
            return
        self.current_warning = self.engine.evaluate(self.distances)

    def _maybe_speak(self):
        severity = self.current_warning.get("severity")
        if severity not in {"warning", "critical", "very_close"}:
            return
        now = time.time()
        cooldown = 2.0 if severity == "warning" else 1.2 if severity == "critical" else 0.8
        if now - self.last_audio_time < cooldown:
            return
        self.last_audio_time = now
        self.audio.speak(str(self.current_warning.get("message") or ""))

    def on_stop(self):
        try:
            self.bluetooth.disconnect()
        except Exception:
            pass
        try:
            self.audio.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    AuraGuideApp().run()
