# AURA GUIDE

Smart Assistive Hat Android app.

## What is included

- Responsive Android UI for many screen sizes
- Your `logo.png` brand asset
- Splash/loading screen
- Dark/Light theme
- HC-05 Bluetooth Classic connection code
- Arduino protocol parser: `F:80,L:150,R:45,B:200`
- Front / Left / Right / Back sensor dashboard
- Warning / Critical / Very Close logic
- Android Text-to-Speech warning
- No demo mode and no fake data

## Important

The app will show empty sensor values until real HC-05 data is received.

Arduino must send lines like:

```text
F:80,L:150,R:45,B:200
```

Use newline after each line.

## Desktop preview

```bash
python main.py
```

Desktop preview does not connect to HC-05. Bluetooth works on Android APK.
