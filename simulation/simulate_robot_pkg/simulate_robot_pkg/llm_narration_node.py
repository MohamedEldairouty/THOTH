#!/usr/bin/env python3
"""
llm_narration_node.py
- Pre-generates all exhibit narrations at startup (zero delay on arrival)
- Watches Nav2 action status for goal completion
- On arrival near exhibit: plays cached audio instantly
- Ends narration with "Do you have any questions? I am all ears!"
- Listens for visitor voice questions via Whisper and answers via Gemini
"""

import os
import asyncio
import tempfile
import time
import threading
import math

import rclpy
from rclpy.node import Node
from nav2_msgs.action import NavigateToPose
from action_msgs.msg import GoalStatusArray
from geometry_msgs.msg import PoseWithCovarianceStamped
from std_msgs.msg import Bool

import edge_tts
import soundfile as sf
import sounddevice as sd
import numpy as np
import whisper
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ── System prompt ──────────────────────────────────────────────
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
    "ar": "ar-EG-SalmaNeural",
    "en": "en-US-JennyNeural"
}

QA_ENDING = {
    "en": "Do you have any questions? I am all ears!",
    "ar": "هل لديك أي أسئلة؟ أنا كلي آذان صاغية!"
}

# ── Exhibit map: (x, y) → exhibit info ────────────────────────
EXHIBIT_MAP = {
    (-2.92494535446167, 3.9759843349456787): {
        "name": "Tutankhamun Golden Mask",
        "language": "en",
        "script": """Narrate the golden death mask of Tutankhamun to a visitor standing
                     in front of it. Describe what it looks like, what it is made of,
                     and its purpose in ancient Egyptian burial traditions.
                     Keep it to 3-4 warm engaging sentences.""",
    },
    (2.0068302154541016, 0.941784143447876): {
        "name": "Rosetta Stone",
        "language": "en",
        "script": """Narrate the Rosetta Stone exhibit to a visitor standing in front of it.
                     Explain what it is, why it was a breakthrough for understanding
                     ancient Egypt, and what languages are inscribed on it.
                     Keep it to 3-4 warm engaging sentences.""",
    },
    (5.001344680786133, -2.0101232528686523): {
        "name": "Royal Mummies Chamber",
        "language": "en",
        "script": """Introduce the Royal Mummies Chamber to a visitor.
                     Name some of the pharaohs present, explain the mummification
                     process briefly, and why these mummies are historically significant.
                     Keep it to 3-4 warm engaging sentences.""",
    },
}

TRIGGER_RADIUS = 1.5  # meters


def find_nearest_exhibit(x, y):
    best, best_dist = None, float('inf')
    for (ex, ey), exhibit in EXHIBIT_MAP.items():
        dist = math.sqrt((x - ex)**2 + (y - ey)**2)
        if dist < best_dist:
            best_dist = dist
            best = exhibit
    return best if best_dist <= TRIGGER_RADIUS else None


# ── Audio helpers ──────────────────────────────────────────────

async def _tts_async(text, language, output_file):
    voice = VOICES.get(language, VOICES["en"])
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)


def tts(text, language, output_file):
    asyncio.run(_tts_async(text, language, output_file))


def play(file_path):
    data, samplerate = sf.read(file_path)
    sd.play(data, samplerate)
    sd.wait()


def record_audio(duration=6, sample_rate=16000):
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype=np.float32
    )
    sd.wait()
    return audio, sample_rate


def transcribe(audio, sample_rate, model):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp = f.name
    sf.write(tmp, audio, sample_rate)
    result = model.transcribe(tmp)
    os.unlink(tmp)
    return result["text"].strip(), result["language"]


def ask_gemini(visitor_text, exhibit_name):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"{SYSTEM_PROMPT}\nCurrent exhibit: {exhibit_name}\nVisitor says: {visitor_text}"
    )
    return response.text.strip()


# ── ROS Node ───────────────────────────────────────────────────

class LLMNarrationNode(Node):

    def __init__(self):
        super().__init__('llm_narration_node')

        self._busy = False
        self._active_uuids = set()
        self._robot_x = None
        self._robot_y = None
        self._audio_cache = {}   # exhibit name → {file, language}
        self._whisper_model = None

        self.create_subscription(
            PoseWithCovarianceStamped,
            '/amcl_pose',
            self._pose_cb,
            10
        )
        self.create_subscription(
            NavigateToPose.Impl.FeedbackMessage,
            '/navigate_to_pose/_action/feedback',
            self._feedback_cb,
            10
        )
        self.create_subscription(
            GoalStatusArray,
            '/navigate_to_pose/_action/status',
            self._status_cb,
            10
        )

        self._speaking_pub = self.create_publisher(Bool, '/robot_speaking', 10)

        self.get_logger().info('Loading Whisper + pre-generating exhibit audio...')
        threading.Thread(target=self._startup, daemon=True).start()

    # ── Startup: load Whisper + pre-generate all audio ─────────
    def _startup(self):
        self._whisper_model = whisper.load_model("base")
        self.get_logger().info('Whisper ready ✓')

        for coords, exhibit in EXHIBIT_MAP.items():
            name = exhibit["name"]
            lang = exhibit["language"]
            self.get_logger().info(f'Pre-generating: {name}...')
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"{SYSTEM_PROMPT}\nPrompt: {exhibit['script']}"
                )
                text = response.text.strip() + " " + QA_ENDING[lang]
                audio_file = f"/tmp/thoth_{name.replace(' ', '_')}.mp3"
                tts(text, lang, audio_file)
                self._audio_cache[name] = {"file": audio_file, "language": lang}
                self.get_logger().info(f'  ✓ {name} ready')
            except Exception as e:
                self.get_logger().error(f'Pre-gen failed for {name}: {e}')

        self.get_logger().info('All exhibits ready! Navigate to an exhibit to start.')

    # ── Pose tracking ──────────────────────────────────────────
    def _pose_cb(self, msg: PoseWithCovarianceStamped):
        self._robot_x = msg.pose.pose.position.x
        self._robot_y = msg.pose.pose.position.y

    def _uuid_str(self, uuid_bytes):
        return '-'.join(str(b) for b in uuid_bytes)

    def _feedback_cb(self, msg):
        self._active_uuids.add(self._uuid_str(msg.goal_id.uuid))

    # ── Status: trigger on goal success ───────────────────────
    def _status_cb(self, msg: GoalStatusArray):
        if self._busy:
            return
        for status in msg.status_list:
            uid = self._uuid_str(status.goal_info.goal_id.uuid)
            if status.status == 4 and uid in self._active_uuids:
                self._active_uuids.discard(uid)
                threading.Thread(
                    target=self._check_and_narrate,
                    daemon=True
                ).start()

    def _check_and_narrate(self):
        time.sleep(0.2)

        if self._robot_x is None:
            self.get_logger().warn('Robot pose not received yet.')
            return

        exhibit = find_nearest_exhibit(self._robot_x, self._robot_y)
        if not exhibit:
            self.get_logger().info(
                f'Arrived at ({self._robot_x:.2f}, {self._robot_y:.2f}) — not near an exhibit.'
            )
            return

        cached = self._audio_cache.get(exhibit["name"])
        if not cached:
            self.get_logger().warn(f'Audio not ready yet for {exhibit["name"]}')
            return

        self.get_logger().info(f'At exhibit: {exhibit["name"]} — playing narration!')
        self._busy = True
        self._speaking_pub.publish(Bool(data=True))

        try:
            # Play cached audio instantly
            play(cached["file"])
            # Start Q&A loop
            self._qa_loop(exhibit, cached["language"])
        except Exception as e:
            self.get_logger().error(f'Narration error: {e}')
        finally:
            self._busy = False
            self._speaking_pub.publish(Bool(data=False))

    # ── Q&A loop ───────────────────────────────────────────────
    def _qa_loop(self, exhibit, language):
        self.get_logger().info('Q&A started — listening for visitor questions...')
        silence = 0
        max_silence = 2

        while silence < max_silence:
            audio, sr = record_audio(duration=6)
            text, lang = transcribe(audio, sr, self._whisper_model)

            if len(text) < 3:
                silence += 1
                self.get_logger().info(f'No question ({silence}/{max_silence})')
                continue

            silence = 0
            self.get_logger().info(f'Visitor ({lang}): {text}')

            answer = ask_gemini(text, exhibit["name"])
            self.get_logger().info(f'THOTH: {answer}')

            out = f"/tmp/thoth_answer_{int(time.time())}.mp3"
            tts(answer, lang, out)
            play(out)
            try:
                os.unlink(out)
            except Exception:
                pass

        self.get_logger().info('Q&A ended. Ready for next goal.')


def main(args=None):
    rclpy.init(args=args)
    node = LLMNarrationNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
