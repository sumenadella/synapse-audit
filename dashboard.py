import streamlit as st
import cv2
import time
import base64
import json
import threading
import pyttsx3
from datetime import datetime
from brain import SOPStateEngine

# --- Page Configuration ---
st.set_page_config(
    page_title="SynapseAudit | Procedural Interceptor",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Industrial Dark Styling
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .status-card {
        padding: 18px;
        border-radius: 8px;
        margin-bottom: 12px;
        border-left: 6px solid #4CAF50;
    }
    .violation-banner {
        background-color: #4a0000;
        color: #ff4b4b;
        padding: 15px;
        border-radius: 6px;
        border: 1px solid #ff4b4b;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- Audio Engine (Non-blocking) ---
@st.cache_resource
def get_tts_engine():
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 165)
        return engine
    except Exception:
        return None

tts = get_tts_engine()

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

# --- SOP Protocol Definition ---
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

# --- State Engine & Session Initialization ---
if "engine" not in st.session_state:
    st.session_state.engine = SOPStateEngine(DEFAULT_SOP)
if "audit_log" not in st.session_state:
    st.session_state.audit_log = []
if "system_status" not in st.session_state:
    st.session_state.system_status = "OBSERVING"
if "last_alert" not in st.session_state:
    st.session_state.last_alert = "System active. Awaiting operator action."

engine = st.session_state.engine
active_step = engine.get_active_step()

# --- Sidebar Controls ---
with st.sidebar:
    st.title("🛡️ SynapseAudit")
    st.caption("Meta Hackathon 2026 | Push the Frontier")
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
    st.code("Vision: Meta Muse Spark Open\nGrounding: SAM 3.1\nEngine: SOPStateEngine", language="text")

# --- Main Dashboard Layout ---
col_feed, col_telemetry = st.columns([1.3, 1.0])

with col_feed:
    st.subheader("Live Operational Feed")
    
    # Camera Stream Input
    camera_image = st.camera_input("Workstation Camera Feed", label_visibility="collapsed")
    
    # Status Banner
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

with col_telemetry:
    st.subheader("Standard Operating Procedure (SOP)")
    
    for idx, step in enumerate(DEFAULT_SOP):
        if idx < engine.current_step_idx:
            # Completed Steps
            st.markdown(f"**Step {step['step_id']}: {step['title']}** — `COMPLETED`")
            st.caption(f"✔️ {step['description']}")
        elif idx == engine.current_step_idx:
            # Current Active Step
            st.markdown(f"### 👉 Step {step['step_id']}: {step['title']}")
            st.markdown(f"**Action Required:** {step['description']}")
            st.markdown(f"**Prohibited Risk:** :red[{step['violation']}]")
        else:
            # Upcoming Steps
            st.markdown(f"**Step {step['step_id']}: {step['title']}** — `PENDING`")
            st.caption(f"⏳ {step['description']}")
        st.divider()

    st.subheader("Audit Event Trail")
    if st.session_state.audit_log:
        for entry in st.session_state.audit_log[:5]:
            st.text(entry)
    else:
        st.caption("No events recorded yet.")