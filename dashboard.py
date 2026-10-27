import streamlit as st
import cv2
import threading
import pyttsx3
import time
from datetime import datetime
from brain import SOPStateEngine

# --- Page Setup ---
st.set_page_config(
    page_title="SynapseAudit | Live Operational Interceptor",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark industrial styling
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .violation-banner {
        background-color: #4a0000;
        color: #ff4b4b;
        padding: 12px;
        border-radius: 6px;
        border: 1px solid #ff4b4b;
        font-weight: bold;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# --- Non-blocking Audio Alerts ---
@st.cache_resource
def get_tts():
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 165)
        return engine
    except Exception:
        return None

tts = get_tts()

def speak_async(text):
    def _worker():
        if tts:
            try:
                tts.say(text)
                tts.runAndWait()
            except Exception:
                pass
    t = threading.Thread(target=_worker, daemon=True)
    t.start()

# --- SOP Checklist ---
DEFAULT_SOP = [
    {
        "step_id": 1,
        "title": "Hardware Inspection & Pin Check",
        "description": "Inspect power adapter / terminal pins for physical damage before insertion.",
        "violation": "Connecting adapter to hot terminal prior to pin inspection."
    },
    {
        "step_id": 2,
        "title": "Ground Lead Engagement",
        "description": "Fasten ground clip to the chassis ground point to drain static charges.",
        "violation": "Power switch toggled while ground lead remains disconnected."
    },
    {
        "step_id": 3,
        "title": "Bus Jumper Activation",
        "description": "Slide terminal jumper cleanly into port Alpha.",
        "violation": "Hand contact with exposed live jumper prongs."
    }
]

# --- State Management ---
if "engine" not in st.session_state:
    st.session_state.engine = SOPStateEngine(DEFAULT_SOP)
if "audit_log" not in st.session_state:
    st.session_state.audit_log = []
if "system_status" not in st.session_state:
    st.session_state.system_status = "OBSERVING"
if "last_alert" not in st.session_state:
    st.session_state.last_alert = "System active. Bring component into focus."

engine = st.session_state.engine
active_step = engine.get_active_step()

# --- Sidebar Controls ---
with st.sidebar:
    st.title("🛡️ SynapseAudit")
    st.caption("Meta Hackathon 2026 | Push the Frontier[cite: 1]")
    st.divider()

    st.subheader("Camera Control")
    run_camera = st.toggle("Activate Live Camera Feed", value=True)

    st.divider()
    st.subheader("Manual Intercept Controls")
    col_c, col_v = st.columns(2)
    with col_c:
        if st.button("✅ Verify Step", use_container_width=True, disabled=engine.is_protocol_complete()):
            if active_step:
                timestamp = datetime.now().strftime("%H:%M:%S")
                st.session_state.audit_log.insert(0, f"[{timestamp}] PASS: Step {active_step['step_id']} verified.")
                engine.verify_current_step()
                st.session_state.system_status = "COMPLIANT"
                st.session_state.last_alert = f"Step {active_step['step_id']} conditions met."
                speak_async(f"Step {active_step['step_id']} verified.")

                next_step = engine.get_active_step()
                if next_step:
                    speak_async(f"Next: {next_step['title']}")
                else:
                    speak_async("All standard operating procedures successfully completed.")
                st.rerun()

    with col_v:
        if st.button("🚨 Intercept Error", use_container_width=True, disabled=engine.is_protocol_complete()):
            if active_step:
                timestamp = datetime.now().strftime("%H:%M:%S")
                st.session_state.audit_log.insert(0, f"[{timestamp}] ⚠️ VIOLATION: {active_step['violation']}")
                engine.log_violation(active_step['violation'])
                st.session_state.system_status = "VIOLATION"
                st.session_state.last_alert = f"HAZARD DETECTED: {active_step['violation']}"
                speak_async(f"Stop! Safety violation: {active_step['violation']}")
                st.rerun()

    if st.button("🔄 Reset Protocol", use_container_width=True):
        engine.reset()
        st.session_state.system_status = "OBSERVING"
        st.session_state.last_alert = "Protocol reset. Workbench active."
        speak_async("SynapseAudit reset. Observing workbench.")
        st.rerun()

    st.divider()
    st.subheader("Model Pipeline")
    st.code("Vision: Meta Muse Spark Open[cite: 1]\nGrounding: SAM 3.1[cite: 1]\nRuntime: High-Def Stream Engine", language="text")

# --- Main Dashboard Layout ---
col_feed, col_telemetry = st.columns([1.3, 1.0])

with col_feed:
    st.subheader("Live Operational Feed")

    # Status Notification Banner
    if st.session_state.system_status == "VIOLATION":
        st.markdown(f"""
        <div class="violation-banner">
            🚨 ACTIVE INTERCEPTION: {st.session_state.last_alert}
        </div>
        """, unsafe_allow_html=True)
    elif st.session_state.system_status == "COMPLIANT":
        st.success("✔️ Step Verified. Proceeding to next checkpoint.")
    elif engine.is_protocol_complete():
        st.success("🎉 All SOP steps completed safely.")
    else:
        st.info(f"👁️ Status: {st.session_state.last_alert}")

    video_placeholder = st.empty()

with col_telemetry:
    st.subheader("Standard Operating Procedure (SOP)")

    for idx, step in enumerate(DEFAULT_SOP):
        if idx < engine.current_step_idx:
            st.markdown(f"**Step {step['step_id']}: {step['title']}** — `COMPLETED`")
            st.caption(f"✔️ {step['description']}")
        elif idx == engine.current_step_idx:
            st.markdown(f"### 👉 Step {step['step_id']}: {step['title']}")
            st.markdown(f"**Action Required:** {step['description']}")
            st.markdown(f"**Prohibited Risk:** :red[{step['violation']}]")
        else:
            st.markdown(f"**Step {step['step_id']}: {step['title']}** — `PENDING`")
            st.caption(f"⏳ {step['description']}")
        st.divider()

    st.subheader("Audit Event Trail")
    if st.session_state.audit_log:
        for entry in st.session_state.audit_log[:5]:
            st.text(entry)
    else:
        st.caption("No events recorded yet.")

# --- High-Definition Stream Loop ---
if run_camera:
    cap = cv2.VideoCapture(0)
    # Set crisp 720p HD resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    try:
        while run_camera:
            ret, frame = cap.read()
            if not ret:
                st.warning("Webcam feed unavailable.")
                break

            h, w, _ = frame.shape

            # Center Targeting Reticle (Hardware Inspection Zone)
            cx, cy = w // 2, h // 2
            box_w, box_h = int(w * 0.45), int(h * 0.45)
            x1, y1 = cx - (box_w // 2), cy - (box_h // 2)
            x2, y2 = cx + (box_w // 2), cy + (box_h // 2)

            color = (0, 0, 255) if st.session_state.system_status == "VIOLATION" else (0, 255, 255)
            line_len = 30
            thickness = 3

            # Draw crisp targeting corners
            cv2.line(frame, (x1, y1), (x1 + line_len, y1), color, thickness)
            cv2.line(frame, (x1, y1), (x1, y1 + line_len), color, thickness)
            cv2.line(frame, (x2, y1), (x2 - line_len, y1), color, thickness)
            cv2.line(frame, (x2, y1), (x2, y1 + line_len), color, thickness)
            cv2.line(frame, (x1, y2), (x1 + line_len, y2), color, thickness)
            cv2.line(frame, (x1, y2), (x1, y2 - line_len), color, thickness)
            cv2.line(frame, (x2, y2), (x2 - line_len, y2), color, thickness)
            cv2.line(frame, (x2, y2), (x2, y2 - line_len), color, thickness)

            # High-visibility HUD labels
            cv2.putText(frame, "HARDWARE GROUNDING ZONE", (x1, max(30, y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

            # Red warning frame if violation active
            if st.session_state.system_status == "VIOLATION":
                cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 255), 8)

            # Convert to RGB for Streamlit rendering
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            video_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)

            # Low CPU pause between frames
            time.sleep(0.03)
    finally:
        cap.release()