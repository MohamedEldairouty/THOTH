import os
import asyncio
import tempfile
import time
import edge_tts
import sounddevice as sd
import soundfile as sf
import numpy as np
import whisper
from dotenv import load_dotenv
from google import genai
from playsound import playsound

# ─────────────────────────────────────────
# SETUP
# ─────────────────────────────────────────

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_PROMPT = """You are THOTH, a friendly and enthusiastic museum tour guide robot 
at the Egyptian Museum in Giza, Egypt.

Your rules:
- Always reply in the SAME language the visitor used
- If they speak Arabic, reply in Arabic
- If they speak English, reply in English
- Keep answers SHORT — maximum 3 sentences, this is real-time conversation
- Be warm, friendly, and make history exciting
- You are talking to museum visitors of all ages including children
- If you don't know something specific, say so honestly
"""

VOICES = {
    "ar": "ar-EG-SalmaNeural",   # Egyptian Arabic
    "en": "en-US-JennyNeural"    # English
}

# ─────────────────────────────────────────
# STEP 1 — RECORD from microphone
# ─────────────────────────────────────────

def record_audio(duration=6, sample_rate=16000):
    print(f"\n🎤 Listening... speak now! ({duration} seconds)")
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype=np.float32
    )
    sd.wait()
    print("  Got it! ✓")
    return audio, sample_rate

# ─────────────────────────────────────────
# STEP 2 — TRANSCRIBE with Whisper
# ─────────────────────────────────────────

def transcribe(audio, sample_rate, whisper_model):
    print("  Transcribing your speech...")
    
    # Save audio to a temp file for Whisper to process
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
    sf.write(tmp_path, audio, sample_rate)
    
    result = whisper_model.transcribe(tmp_path)
    os.unlink(tmp_path)  # delete temp file
    
    text = result["text"].strip()
    language = result["language"]  # "ar" or "en"
    
    print(f"  Detected language: {language}")
    print(f"  You said: {text}")
    return text, language

# ─────────────────────────────────────────
# STEP 3 — ASK Gemini
# ─────────────────────────────────────────

def ask_gemini(visitor_text):
    print("  Thinking...")
    full_message = f"{SYSTEM_PROMPT}\n\nVisitor says: {visitor_text}"
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=full_message
    )
    answer = response.text.strip()
    print(f"  THOTH says: {answer}")
    return answer

# ─────────────────────────────────────────
# STEP 4 — SPEAK the answer
# ─────────────────────────────────────────

async def generate_audio(text, language, output_file):
    voice = VOICES.get(language, VOICES["en"])
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

def speak(text, language="en"):
    print("  Speaking...")
    # Use a timestamp in filename so it's always unique and never locked
    output_file = f"response_{language}_{int(time.time())}.mp3"
    asyncio.run(generate_audio(text, language, output_file))
    playsound(output_file)
    # Small pause to make sure file is released before next time
    time.sleep(0.5)
# ─────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────

def main():
    print("=" * 55)
    print("   🏛️  THOTH — Egyptian Museum Tour Guide Robot")
    print("=" * 55)
    print("\nLoading Whisper model... (takes ~30 seconds first time)")
    
    whisper_model = whisper.load_model("base")
    print("Whisper ready ✓")
    print("\nTHOTH is ready! Press Ctrl+C anytime to stop.")
    print("-" * 55)

    # Greet the visitor
    greeting_en = "Welcome to the Egyptian Museum! I am THOTH, your personal tour guide. Please ask me anything about our exhibits!"
    speak(greeting_en, language="en")

    # Main conversation loop - keeps running until you press Ctrl+C
    while True:
        try:
            print("\n" + "─" * 40)
            input("  Press ENTER to ask a question (or Ctrl+C to quit)...")
            
            # Step 1 - Record
            audio, sr = record_audio(duration=6)
            
            # Step 2 - Transcribe
            visitor_text, language = transcribe(audio, sr, whisper_model)
            
            # If Whisper didn't catch anything meaningful, skip
            if len(visitor_text) < 2:
                print("  Didn't catch that, please try again.")
                continue
            
            # Step 3 - Ask Gemini
            answer = ask_gemini(visitor_text)
            
            # Step 4 - Speak the answer
            speak(answer, language)
            
        except KeyboardInterrupt:
            print("\n\nThank you for visiting the Egyptian Museum! Goodbye! 👋")
            break

if __name__ == "__main__":
    main()