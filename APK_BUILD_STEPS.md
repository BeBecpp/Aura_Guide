# APK build steps

Run all commands inside WSL Ubuntu, not PowerShell.

## 1. Install build tools

```bash
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip python3-venv python3-full autoconf libtool pkg-config zlib1g-dev libncurses-dev cmake libffi-dev libssl-dev wget curl ca-certificates build-essential
```

## 2. Buildozer virtualenv

```bash
python3 -m venv ~/.venvs/buildozer
source ~/.venvs/buildozer/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install Cython==0.29.19 virtualenv buildozer
```

## 3. Copy project into Linux home

Do not build from `/mnt/d/...`.

```bash
mkdir -p ~/projects
rm -rf ~/projects/aura_guide_app
cp -r /mnt/d/bebe_personal/aura_guide_final/aura_guide_app ~/projects/aura_guide_app
cd ~/projects/aura_guide_app
```

## 4. Build debug APK

```bash
source ~/.venvs/buildozer/bin/activate
buildozer -v android debug
```

## 5. Copy APK to Windows

```bash
cp bin/*.apk /mnt/d/bebe_personal/
```

## If UI looks tiny on Android

This project already fixes that by not forcing `Window.size` on Android.

## If you change code and rebuild

```bash
buildozer -v android debug
```

Use `buildozer android clean` only if the build system is stuck.
