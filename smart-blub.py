import os
import time
import difflib
import requests
import torch
import numpy as np
import sounddevice as sd
from transformers import pipeline


ESP32_IP = "192.168.0.241"  


ON_KEYWORDS = ["включити", "увімкнути", "засвітити", "запалити", "вмикай"]
OFF_KEYWORDS = ["виключити", "вимкнути", "погасити", "загасити", "вимикай"]


SIMILARITY_THRESHOLD = 0.7


RATE = 16000  
CHANNELS = 1


SILENCE_THRESHOLD = 0.08

SILENCE_LIMIT = 24

MIN_SPEECH_BLOCKS = 8

COMMAND_COOLDOWN = 2.0


ffmpeg_path = os.path.expandvars(
    r"C:\Users\vital\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin"
)
if os.path.exists(ffmpeg_path):
    os.environ["PATH"] += os.pathsep + ffmpeg_path


device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
print(f"Using device: {device.upper()}")
print("Завантаження моделі Whisper...")


pipe = pipeline(
    "automatic-speech-recognition",
    model="openai/whisper-base",
    device=device
)

_last_command_time = 0.0


def send_command_to_esp(command: str):
    global _last_command_time

    now = time.time()
    if now - _last_command_time < COMMAND_COOLDOWN:
        print(f"[cooldown] Команда '{command}' проігнорована (занадто швидко після попередньої)")
        return
    _last_command_time = now

    url = f"http://{ESP32_IP}/led/{command}"
    try:
        print(f"-> Надсилаю команду '{command.upper()}' на ESP32...")
        response = requests.get(url, timeout=2)
        if response.status_code == 200:
            print(f"Успішно! Відповідь: {response.text}")
    except Exception as e:
        print(f"Помилка зв'язку з ESP32 (перевір IP та мережу): {e}")


def best_keyword_match(text_nospace: str, keywords: list):
    
    best_score = 0.0
    best_fragment = None

    for kw in keywords:
        klen = len(kw)
        for size in range(max(3, klen - 2), klen + 3):
            if size > len(text_nospace):
                continue
            for i in range(0, len(text_nospace) - size + 1):
                window = text_nospace[i:i + size]
                ratio = difflib.SequenceMatcher(None, window, kw).ratio()
                if ratio > best_score:
                    best_score = ratio
                    best_fragment = window

    return best_score, best_fragment


def process_text_and_trigger(text: str):
    
    cleaned = text.lower().strip()
    for ch in ".,!?-":
        cleaned = cleaned.replace(ch, "")
    text_nospace = cleaned.replace(" ", "")

    if not text_nospace:
        return

    print(f"Розпізнано: \"{text}\"")

    on_score, on_fragment = best_keyword_match(text_nospace, ON_KEYWORDS)
    off_score, off_fragment = best_keyword_match(text_nospace, OFF_KEYWORDS)

    if on_score < SIMILARITY_THRESHOLD and off_score < SIMILARITY_THRESHOLD:
        print("Командних слів не виявлено.")
        return

    if on_score >= off_score:
        print(f" [!] Фрагмент '{on_fragment}' схожий на команду 'on' (схожість {on_score:.2f})")
        send_command_to_esp("on")
    else:
        print(f" [!] Фрагмент '{off_fragment}' схожий на команду 'off' (схожість {off_score:.2f})")
        send_command_to_esp("off")


def listen_and_serve():
    print("\n Скрипт запущено! Говоріть у мікрофон (наприклад: 'увімкни', 'погаси').")
    print("Натисніть Ctrl+C для виходу.\n")

    audio_buffer = []
    speaking = False
    silence_counter = 0

    def audio_callback(indata, frames, time_info, status):
        nonlocal audio_buffer, speaking, silence_counter

        amplitude = np.max(np.abs(indata))

        if amplitude > SILENCE_THRESHOLD:
            if not speaking:
                print("Запис голосу...", end="", flush=True)
                speaking = True
            audio_buffer.append(indata.copy())
            silence_counter = 0
        else:
            if speaking:
                audio_buffer.append(indata.copy())
                silence_counter += 1

                if silence_counter > SILENCE_LIMIT:

                    if len(audio_buffer) < MIN_SPEECH_BLOCKS:
                        print(" (закоротко, ігнорую - схоже на шум)")
                        audio_buffer = []
                        speaking = False
                        return

                    print(" обробка ШІ...")

                    audio_np = np.concatenate(audio_buffer, axis=0).flatten()

                    result = pipe(audio_np, generate_kwargs={"language": "ukrainian", "task": "transcribe"})
                    text = result["text"]

                    process_text_and_trigger(text)

                    audio_buffer = []
                    speaking = False
                    print("\nСлухаю знову...")

    with sd.InputStream(callback=audio_callback, channels=CHANNELS, samplerate=RATE, blocksize=1024):
        try:
            while True:
                sd.sleep(100)
        except KeyboardInterrupt:
            print("\nРоботу скрипта завершено.")


if __name__ == "__main__":
    listen_and_serve()
