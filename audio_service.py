from __future__ import annotations

from kivy.utils import platform


class AudioService:
    def __init__(self):
        self.ready = False
        self.tts = None
        self.locale = None
        self.volume = 1.0
        if platform == "android":
            self._init_android_tts()

    def _init_android_tts(self):
        try:
            from jnius import autoclass, PythonJavaClass, java_method
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
            Locale = autoclass("java.util.Locale")

            service = self

            class InitListener(PythonJavaClass):
                __javainterfaces__ = ["android/speech/tts/TextToSpeech$OnInitListener"]
                __javacontext__ = "app"

                @java_method("(I)V")
                def onInit(self, status):
                    try:
                        if status == TextToSpeech.SUCCESS:
                            service.locale = Locale("mn", "MN")
                            service.tts.setLanguage(service.locale)
                            service.ready = True
                    except Exception:
                        service.ready = True

            self.tts = TextToSpeech(PythonActivity.mActivity, InitListener())
        except Exception:
            self.ready = False
            self.tts = None

    def set_volume(self, volume: float):
        self.volume = max(0.0, min(1.0, float(volume)))

    def speak(self, text: str):
        if not text:
            return
        if platform != "android":
            print("TTS:", text)
            return
        if not self.tts:
            return
        try:
            from jnius import autoclass
            TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
            Bundle = autoclass("android.os.Bundle")
            bundle = Bundle()
            bundle.putFloat(TextToSpeech.Engine.KEY_PARAM_VOLUME, float(self.volume))
            self.tts.speak(text, TextToSpeech.QUEUE_FLUSH, bundle, "aura_warning")
        except Exception:
            try:
                from jnius import autoclass
                TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
                self.tts.speak(text, TextToSpeech.QUEUE_FLUSH, None)
            except Exception:
                pass

    def shutdown(self):
        try:
            if self.tts:
                self.tts.stop()
                self.tts.shutdown()
        except Exception:
            pass
