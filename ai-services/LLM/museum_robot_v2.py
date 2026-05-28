import os
import tempfile
import time
import sounddevice as sd
from playsound import playsound
import soundfile as sf
import numpy as np
import whisper
from dotenv import load_dotenv
from google import genai
from elevenlabs import ElevenLabs

# -----------------------------------------
# SETUP
# -----------------------------------------

# Load your API keys from the .env file
load_dotenv()

# Connect to Gemini (your LLM)
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Connect to ElevenLabs (your TTS)
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "sk_64c92d5791dc00c4660309eee8c38c43f704ea2f9c6ef8d3")
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# Bill voice — deep male, works in all languages with multilingual model
ELEVENLABS_VOICE_ID = "pqHfZKP75CvOlQylNhV4"
ELEVENLABS_MODEL = "eleven_multilingual_v2"

# -----------------------------------------
# SYSTEM PROMPT
# The instruction we give Gemini.
# The visitor never sees this.
# -----------------------------------------

SYSTEM_PROMPT = """You are THOTH, a friendly and enthusiastic museum tour guide robot 
at the Egyptian Museum in Giza, Egypt.

Your rules:
- Always reply in the EXACT SAME language the visitor used
- If they speak Arabic, reply in Arabic
- If they speak English, reply in English
- If they speak French, reply in French
- If they speak any other language, reply in that same language
- NEVER switch languages unless the visitor switches first
- Keep answers SHORT — maximum 3 sentences, this is a real-time conversation
- Be warm, friendly, and make history exciting
- You are talking to museum visitors of all ages including children
- If you don't know something specific, say so honestly
"""

# -----------------------------------------
# STEP 1 — RECORD audio from the microphone
# -----------------------------------------

def record_audio(duration=6, sample_rate=16000):
    """
    Turns on your microphone and records audio.
    - duration: how many seconds to record
    - sample_rate: 16000 is what Whisper expects, don't change this
    """
    print(f"\n Recording for {duration} seconds... speak now!")
    
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype=np.float32
    )
    
    sd.wait()  # pauses until recording finishes
    print("  Got it!")
    return audio, sample_rate

# -----------------------------------------
# STEP 2 — TRANSCRIBE speech to text
# -----------------------------------------

def transcribe(audio, sample_rate, whisper_model):
    """
    Converts recorded audio to text.
    Whisper automatically detects what language was spoken.
    Returns the text and language code (e.g. "ar", "en", "fr").
    """
    print("  Transcribing your speech...")
    
    # Whisper needs audio as a file, so we save it temporarily
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
    
    sf.write(tmp_path, audio, sample_rate)
    result = whisper_model.transcribe(tmp_path)
    os.unlink(tmp_path)  # delete temp file after use
    
    text = result["text"].strip()
    language = result["language"]
    
    print(f"  Detected language: {language}")
    print(f"  You said: {text}")
    return text, language

# -----------------------------------------
# STEP 3 — ASK Gemini for a response
# -----------------------------------------

def ask_gemini(visitor_text):
    """
    Sends the visitor's question to Gemini.
    Gemini replies in the same language as the visitor.

    If Gemini's servers are busy (503 error), we wait 3 seconds and retry.
    We try up to 3 times before giving up gracefully.
    """
    print("  Thinking...")
    
    full_message = f"{SYSTEM_PROMPT}\n\nVisitor says: {visitor_text}"
    
    # Try up to 3 times in case Gemini is temporarily overloaded
    for attempt in range(3):
        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=full_message
            )
            answer = response.text.strip()
            print(f"  THOTH says: {answer}")
            return answer
        
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                # Gemini is temporarily busy — wait and retry
                if attempt < 2:
                    print(f"  Gemini is busy, retrying in 3 seconds... (attempt {attempt + 1}/3)")
                    time.sleep(3)
                else:
                    # All 3 attempts failed — reply politely instead of crashing
                    print("  Gemini unavailable after 3 attempts.")
                    return "I'm sorry, I'm having a small technical issue. Please try asking me again in a moment!"
            else:
                raise  # a different error — let it show so we can debug it

# -----------------------------------------
# STEP 4 — SPEAK using ElevenLabs
# -----------------------------------------

def speak(text):
    """
    Takes text in any language and speaks it using ElevenLabs.
    The multilingual model handles Arabic, English, French, etc.
    """
    print("  Speaking...")
    
    audio_stream = elevenlabs_client.text_to_speech.convert(
        text=text,
        voice_id=ELEVENLABS_VOICE_ID,
        model_id=ELEVENLABS_MODEL,
        output_format="mp3_44100_128"
    )
    
    # Unique filename using timestamp so files never conflict
    output_file = f"thoth_response_{int(time.time())}.mp3"
    
    with open(output_file, "wb") as f:
        for chunk in audio_stream:
            f.write(chunk)
    
    playsound(output_file)
    time.sleep(0.3)
    
    try:
        os.remove(output_file)
    except:
        pass  # if cleanup fails, no big deal

# -----------------------------------------
# MAIN LOOP
# -----------------------------------------

def main():
    print("=" * 55)
    print("   THOTH - Egyptian Museum Tour Guide Robot")
    print("   Powered by Whisper + Gemini + ElevenLabs")
    print("=" * 55)
    
    # FIX 1: Using "small" model instead of "base"
    # "small" is much more accurate for Arabic, especially Egyptian dialect
    # First-time download is ~460MB — totally normal, just wait for it
    print("\nLoading Whisper model... (first time downloads ~460MB, be patient!)")
    whisper_model = whisper.load_model("small")
    print("Whisper ready!")
    
    print("\nTHOTH is ready! Press Ctrl+C anytime to stop.")
    print("Supported: Arabic, English, French, Spanish, German, and more.")
    print("-" * 55)

    greeting = "Welcome to the Egyptian Museum! I am THOTH, your personal tour guide. You can speak to me in any language and I will reply in the same language. Please ask me anything!"
    speak(greeting)

    while True:
        try:
            print("\n" + "-" * 40)
            input("  Press ENTER to ask a question (or Ctrl+C to quit)...")
            
            audio, sr = record_audio(duration=6)
            visitor_text, language = transcribe(audio, sr, whisper_model)
            
            if len(visitor_text) < 2:
                print("  Didn't catch that — please try again.")
                continue
            
            # FIX 2: ask_gemini now retries automatically if Gemini is busy
            answer = ask_gemini(visitor_text)
            
            speak(answer)

        except KeyboardInterrupt:
            print("\n\nThank you for visiting the Egyptian Museum! Goodbye!")
            break

if __name__ == "__main__":
    main()