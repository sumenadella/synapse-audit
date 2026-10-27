import os
import cv2
import base64
import json
import time
import threading
import pyttsx3
from dotenv import load_dotenv

load_dotenv()

# --- 1. Audio Voice Alert Engine (Asynchronous) ---
tts_lock = threading.Lock()

def _speak_worker(text):
    with tts_lock:
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 165)
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"[Audio Error]: {e}")

def speak_async(text):
    """Speaks text in a background thread so the camera feed never freezes."""
    print(f"\n>>> [AI ADVISOR VOICE]: {text}")
    t = threading.Thread(target=_speak_worker, args=(text,))
    t.daemon = True
    t.start()

# --- 2. Mission-Critical Standard Operating Procedure (SOP) ---
SOP_WORKFLOW = [
    {
        "step_id": 1,
        "title": "Verify Ground Connection",
        "description": "Ground wire must be firmly attached to chassis before powering.",
        "violation_condition": "Power switch activated without grounding attached."
    },
    {
        "step_id": 2,
        "title": "Inspect Capacitor Polarity",
        "description": "Align striped negative lead to the ground plane.",
        "violation_condition": "Capacitor inverted or loose contact."
    },
    {
        "step_id": 3,
        "title": "Engage Auxiliary Bus Circuit",
        "description": "Slide terminal jumper into port Alpha.",
        "violation_condition": "Connecting jumper to live hot bus."
    }
]

# --- 3. State Management ---
current_step_idx = 0
last_status = "INITIALIZING"
last_reason = "System online. Observing workbench..."
is_evaluating = False

# Check if active API key is present
api_key = os.getenv("META_API_KEY", "").strip()
IS_SIMULATION_MODE = not api_key or api_key == "paste_your_key_here"

def encode_frame(frame):
    """Compress frame to keep payload lightweight and fast"""
    resized = cv2.resize(frame, (640, 360))
    _, buffer = cv2.imencode('.jpg', resized, [int(cv2.IMWRITE_JPEG_QUALITY), 65])
    return base64.b64encode(buffer).decode('utf-8')

def evaluate_frame_api(frame_b64, step_info):
    """Meta Model API / Baseten inference pipeline"""
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url="https://bridge.baseten.co/v1"  # Baseten gateway
        )
        
        prompt = f"""
        You are SynapseAudit, an industrial safety inspector.
        Current Step: {step_info['title']} - {step_info['description']}
        Safety Risk: {step_info['violation_condition']}
        
        Evaluate the operator's actions in the image.
        Respond ONLY in raw JSON:
        {{
            "compliance": "COMPLIANT" | "VIOLATION" | "IDLE",
            "intervene": true | false,
            "spoken_alert": "<short spoken warning or affirmation>",
            "observation": "<brief physical description>"
        }}
        """
        
        response = client.chat.completions.create(
            model="meta-models/muse-spark-open-1026",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200
        )
        
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content[7:-3].strip()
        elif content.startswith("```"):
            content = content[3:-3].strip()
            
        return json.loads(content)
    except Exception as e:
        return {
            "compliance": "IDLE",
            "intervene": False,
            "spoken_alert": "",
            "observation": f"API error: {str(e)[:40]}"
        }

# --- 4. Main Application Loop ---
def main():
    global current_step_idx, last_status, last_reason, is_evaluating
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[Error]: Cannot open webcam.")
        return

    mode_label = "SIMULATION (HOTKEYS: 'c'=verify, 'v'=violation)" if IS_SIMULATION_MODE else "LIVE META MODEL API"
    print("=" * 60)
    print(f" SynapseAudit Engine Running [{mode_label}]")
    print(" Controls:")
    print("   'c' -> Force Step Verification (Pass)")
    print("   'v' -> Force Mistake Interception (Trigger Alarm)")
    print("   'q' -> Exit")
    print("=" * 60)
    
    speak_async("SynapseAudit safety guard active. Monitoring workbench.")
    last_eval_time = time.time()

    def async_api_worker(b64, step):
        global current_step_idx, last_status, last_reason, is_evaluating
        res = evaluate_frame_api(b64, step)
        comp = res.get("compliance", "IDLE")
        intervene = res.get("intervene", False)
        alert = res.get("spoken_alert", "")
        obs = res.get("observation", "")
        
        last_status = comp
        last_reason = obs
        
        if intervene:
            speak_async(f"Stop! {alert}")
        elif comp == "COMPLIANT":
            speak_async(f"Step {step['step_id']} verified.")
            if current_step_idx < len(SOP_WORKFLOW) - 1:
                current_step_idx += 1
                speak_async(f"Next step: {SOP_WORKFLOW[current_step_idx]['title']}")
        is_evaluating = False

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        active_step = SOP_WORKFLOW[current_step_idx]

        # Trigger background API check every 3 seconds if live key is configured
        if not IS_SIMULATION_MODE and time.time() - last_eval_time > 3.0 and not is_evaluating:
            last_eval_time = time.time()
            is_evaluating = True
            b64_img = encode_frame(frame)
            t = threading.Thread(target=async_api_worker, args=(b64_img, active_step))
            t.daemon = True
            t.start()

        # Render Professional HUD Overlay
        h, w, _ = frame.shape
        
        # Top Header Bar
        cv2.rectangle(frame, (0, 0), (w, 85), (20, 20, 20), -1)
        cv2.putText(frame, f"SYNAPSE-AUDIT | ACTIVE PROTOCOL [STEP {active_step['step_id']}/{len(SOP_WORKFLOW)}]", 
                    (20, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
        cv2.putText(frame, f"TARGET: {active_step['title']}", 
                    (20, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        cv2.putText(frame, f"RULE: {active_step['description']}", 
                    (20, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

        # Status Bar Color Switch
        if last_status == "VIOLATION":
            status_color = (0, 0, 255)  # Bright Red
            # Draw red warning border on frame
            cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 255), 6)
        elif last_status == "COMPLIANT":
            status_color = (0, 255, 0)  # Green
        else:
            status_color = (255, 180, 0) # Amber / Neutral

        # Bottom Telemetry Bar
        cv2.rectangle(frame, (0, h - 45), (w, h), (15, 15, 15), -1)
        cv2.putText(frame, f"STATE: {last_status}", (20, h - 16), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
        cv2.putText(frame, f"| {last_reason[:60]}", (190, h - 16), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1)

        cv2.imshow("SynapseAudit Real-Time Compliance Interceptor", frame)

        # Hotkey listener
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):  # Force Step Complete
            last_status = "COMPLIANT"
            last_reason = f"Operator satisfied Step {active_step['step_id']} conditions."
            speak_async(f"Step {active_step['step_id']} verified.")
            if current_step_idx < len(SOP_WORKFLOW) - 1:
                current_step_idx += 1
                speak_async(f"Proceeding to {SOP_WORKFLOW[current_step_idx]['title']}")
        elif key == ord('v'):  # Force Violation / Intercept
            last_status = "VIOLATION"
            last_reason = f"Critical risk detected: {active_step['violation_condition']}"
            speak_async(f"HOLD! Safety violation: {active_step['violation_condition']}")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()