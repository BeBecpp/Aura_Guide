[app]
title = AURA GUIDE
package.name = auraguide
package.domain = org.auraguide
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,mp3,wav,m4a
source.include_patterns = assets/*,assets/audio/*
version = 1.0.0
requirements = python3,kivy,pyjnius,android
orientation = portrait
fullscreen = 0
icon.filename = assets/icon.png
presplash.filename = assets/splash.png
android.permissions = BLUETOOTH,BLUETOOTH_ADMIN,BLUETOOTH_CONNECT,BLUETOOTH_SCAN,ACCESS_FINE_LOCATION
android.api = 35
android.minapi = 24
android.ndk = 28c
android.archs = arm64-v8a
android.allow_backup = False

[buildozer]
log_level = 2
warn_on_root = 1
