from __future__ import annotations

import threading
from typing import Callable, Optional

from kivy.clock import Clock
from kivy.utils import platform

SPP_UUID = "00001101-0000-1000-8000-00805F9B34FB"


class BluetoothService:
    def __init__(
        self,
        on_data: Optional[Callable[[str], None]] = None,
        on_status: Optional[Callable[[str, str], None]] = None,
        device_name: str = "HC-05",
    ):
        self.on_data = on_data
        self.on_status = on_status
        self.device_name = device_name
        self.socket = None
        self.input_stream = None
        self.thread = None
        self.running = False

    def _status(self, status: str, message: str):
        if self.on_status:
            Clock.schedule_once(lambda *_: self.on_status(status, message), 0)

    def _data(self, line: str):
        if self.on_data:
            Clock.schedule_once(lambda *_: self.on_data(line), 0)

    def connect(self):
        if platform != "android":
            self._status("disconnected", "Bluetooth зөвхөн Android дээр ажиллана")
            return
        if self.running:
            self._status("connected", f"{self.device_name} холбогдсон")
            return
        threading.Thread(target=self._connect_thread, daemon=True).start()

    def _connect_thread(self):
        try:
            from jnius import autoclass
            BluetoothAdapter = autoclass("android.bluetooth.BluetoothAdapter")
            UUID = autoclass("java.util.UUID")

            adapter = BluetoothAdapter.getDefaultAdapter()
            if adapter is None:
                self._status("error", "Bluetooth adapter олдсонгүй")
                return
            if not adapter.isEnabled():
                self._status("error", "Утасны Bluetooth асаана уу")
                return

            self._status("connecting", f"{self.device_name} хайж байна...")
            bonded = adapter.getBondedDevices().toArray()
            target = None
            for device in bonded:
                try:
                    name = device.getName() or ""
                    if self.device_name.upper() in name.upper() or "HC-05" in name.upper():
                        target = device
                        break
                except Exception:
                    pass

            if target is None:
                self._status("error", "HC-05 pair хийгдээгүй байна")
                return

            adapter.cancelDiscovery()
            uuid = UUID.fromString(SPP_UUID)
            self.socket = target.createRfcommSocketToServiceRecord(uuid)
            self.socket.connect()
            self.input_stream = self.socket.getInputStream()
            self.running = True
            self._status("connected", f"{target.getName()} холбогдсон")
            self._read_loop()
        except Exception as exc:
            self.running = False
            self._status("error", f"Bluetooth алдаа: {exc}")
            self.disconnect()

    def _read_loop(self):
        buffer = ""
        while self.running:
            try:
                byte_value = self.input_stream.read()
                if byte_value == -1:
                    continue
                ch = chr(byte_value & 0xFF)
                if ch in "\r\n":
                    line = buffer.strip()
                    buffer = ""
                    if line:
                        self._data(line)
                else:
                    buffer += ch
                    if len(buffer) > 128:
                        buffer = ""
            except Exception:
                break
        self.running = False
        self._status("disconnected", "Bluetooth холболт тасарсан")

    def disconnect(self):
        self.running = False
        try:
            if self.input_stream:
                self.input_stream.close()
        except Exception:
            pass
        try:
            if self.socket:
                self.socket.close()
        except Exception:
            pass
        self.input_stream = None
        self.socket = None
        self._status("disconnected", "Холбогдоогүй")
