from __future__ import annotations

from kivy.utils import platform


def request_android_permissions():
    if platform != "android":
        return
    try:
        from android.permissions import Permission, request_permissions
        permissions = [
            Permission.BLUETOOTH,
            Permission.BLUETOOTH_ADMIN,
            Permission.ACCESS_FINE_LOCATION,
        ]
        # Android 12+
        for name in ("BLUETOOTH_CONNECT", "BLUETOOTH_SCAN"):
            if hasattr(Permission, name):
                permissions.append(getattr(Permission, name))
        request_permissions(list(dict.fromkeys(permissions)))
    except Exception:
        # UI must not crash if permission helper is unavailable on desktop/build tests.
        pass
