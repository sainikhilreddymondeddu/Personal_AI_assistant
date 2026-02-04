import asyncio
import os
import subprocess
import json
from datetime import datetime
import speech_recognition as sr
import pyttsx3
import pyautogui
from playwright.async_api import async_playwright

# =======================
# MEMORY
# =======================
MEMORY_FILE = "memory.json"

def load_memory():
    base = {
        "profile": {"name": None, "preferences": {}},
        "recent_activity": {"last_opened_app": None, "last_opened_site": None},
        "conversation_history": []
    }
    if not os.path.exists(MEMORY_FILE):
        return base
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        return base
    for k in base:
        if k not in data:
            data[k] = base[k]
    return data

def save_memory(mem):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(mem, f, indent=2)

memory = load_memory()

# =======================
# 🔊 SPEAK (WORKING VERSION — DO NOT GLOBALIZE)
# =======================
def speak(text):
    if not text or not text.strip():
        return
    print("AI:", text)
    engine = pyttsx3.init()
    engine.setProperty("rate", 165)
    engine.say(text)
    engine.runAndWait()
    engine.stop()

# =======================
# DESKTOP APPS
# =======================
APP_PROCESSES = {
    "settings": ["SystemSettings.exe"],
    "notepad": ["notepad.exe"],
    "calculator": ["Calculator.exe", "ApplicationFrameHost.exe"]
}

def open_desktop_app(app):
    if app == "settings":
        os.system("start ms-settings:")
    elif app == "notepad":
        os.system('start "" notepad')
    elif app == "calculator":
        os.system("calc")
    memory["recent_activity"]["last_opened_app"] = app
    save_memory(memory)

def close_desktop_app(app):
    for p in APP_PROCESSES.get(app, []):
        os.system(f"taskkill /IM {p} /F")

# =======================
# WEB APPS
# =======================
WEB_URLS = {
    "youtube": "https://www.youtube.com",
    "spotify": "https://open.spotify.com",
    "whatsapp": "https://web.whatsapp.com"
}

class BrowserController:
    def __init__(self):
        self.playwright = None
        self.context = None
        self.tabs = {}

    async def start(self):
        if self.context:
            return
        self.playwright = await async_playwright().start()
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir="ai_browser_profile",
            headless=False
        )

    async def open_app(self, app):
        await self.start()
        page = self.tabs.get(app)
        if page and not page.is_closed():
            await page.bring_to_front()
        else:
            page = await self.context.new_page()
            await page.goto(WEB_URLS[app])
            self.tabs[app] = page
        memory["recent_activity"]["last_opened_site"] = app
        save_memory(memory)

    async def close_app(self, app):
        page = self.tabs.get(app)
        if page and not page.is_closed():
            await page.close()
            self.tabs.pop(app, None)
            speak(f"Closed {app}")

    async def close_browser(self):
        if self.context:
            await self.context.close()
            self.context = None
            self.tabs.clear()
            speak("Browser closed")

browser = BrowserController()

# =======================
# AI
# =======================
def ask_ai(q):
    try:
        r = subprocess.run(
            ["ollama", "run", "phi", q],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=20
        )
        return r.stdout.strip()[:400] or "I could not find an answer."
    except:
        return "AI engine not available."

# =======================
# COMMAND HANDLER
# =======================
async def handle_command(text):
    t = text.lower().strip()

    if t == "what is my name":
        name = memory["profile"].get("name")
        speak(f"Your name is {name}." if name else "I don't know your name yet.")
        return

    # ✅ FIX: CLOSE BROWSER
    if t == "close browser":
        await browser.close_browser()
        return

    if t.startswith("open "):
        target = t.replace("open ", "")
        if target in WEB_URLS:
            await browser.open_app(target)
            speak(f"Opening {target}")
            return
        open_desktop_app(target)
        speak(f"Opening {target}")
        return

    if t.startswith("close "):
        target = t.replace("close ", "")
        if target in WEB_URLS:
            await browser.close_app(target)
            return
        close_desktop_app(target)
        speak("Closing")
        return

    speak(ask_ai(text))


# =======================
# VOICE LOOP
# =======================
async def voice_loop():
    r = sr.Recognizer()
    mic = sr.Microphone()

    speak("Assistant ready")

    with mic as source:
        r.adjust_for_ambient_noise(source)

    while True:
        try:
            with mic as source:
                audio = r.listen(source, phrase_time_limit=5)
            text = r.recognize_google(audio)
            print("You:", text)
            await handle_command(text)
        except sr.UnknownValueError:
            pass

asyncio.run(voice_loop())
