import streamlit as st
import cv2
import threading
import pyttsx3
import time
import json
import hashlib
from datetime import datetime
from brain import SOPStateEngine

# --- Page Setup ---
st.set_page_config(
    page_title="SynapseAudit | Industrial Compliance Interceptor",
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
    .cert-card {
        background-color: #112211;
        border: 1px solid #2e7d32;
        padding: 15px;
        border-radius: 8px;
        margin-top: 15px;
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

# --- Default Fallback SOP Protocol ---
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
if "active_protocol" not in st.session_state:
    st.session_state.active_protocol = DEFAULT_SOP
if "engine" not in st.session_state:
    st.session_state.engine = SOPStateEngine(st.session_state.active_protocol)
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
    st.caption("Meta Hackathon 2026 | Push the Frontier")
    st.divider()

    # Dynamic SOP Ingestion
    st.subheader("📁 Ingest Custom SOP")
    uploaded_file = st.file_uploader("Upload SOP JSON", type=["json"])
    if uploaded_file is not None:
        try:
            custom_data = json.load(uploaded_file)
            if isinstance(custom_data, list) and len(custom_data) > 0 and "step_id" in custom_data[0]:
                if st.button("Apply Ingested SOP", use_container_width=True):
                    st.session_state.active_protocol = custom_data
                    st.session_state.engine = SOPStateEngine(custom_data)
                    st.session_state.audit_log.clear()
                    st.session_state.system_status = "OBSERVING"
                    st.session_state.last_alert = "Custom SOP loaded successfully."
                    speak_async("New procedural protocol loaded.")
                    st.rerun()
            else:
                st.error("Invalid SOP format: JSON must be a list of step objects.")
        except Exception as e:
            st.error(f"Error parsing JSON: {e}")

    st.divider()
    st.subheader("Camera Feed")
    run_camera = st.toggle("Activate Live Feed", value=True)

    st.divider()
    st.subheader("Manual Intercept Controls")
    col_c, col_v = st.columns(2)
    with col_c:
        if st.button("✅ Verify Step", use_container_width=True, disabled=engine.is_protocol_complete()):
            if active_step:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.audit_log.insert(0, {
                    "timestamp": timestamp,
                    "event": "STEP_VERIFIED",
                    "step_id": active_step['step_id'],
                    "title": active_step['title']
                })
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
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.audit_log.insert(0, {
                    "timestamp": timestamp,
                    "event": "SAFETY_VIOLATION_INTERCEPTED",
                    "step_id": active_step['step_id'],
                    "risk": active_step['violation']
                })
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

    for idx, step in enumerate(st.session_state.active_protocol):
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
        for entry in st.session_state.audit_log[:4]:
            if entry["event"] == "STEP_VERIFIED":
                st.caption(f"🟢 [{entry['timestamp']}] Step {entry['step_id']}: {entry['title']} passed.")
            else:
                st.caption(f"🔴 [{entry['timestamp']}] INTERCEPT: {entry['risk']}")
    else:
        st.caption("No events recorded yet.")

    # --- Compliance Certificate Generation ---
    if engine.is_protocol_complete():
        st.markdown("""
        <div class="cert-card">
            <h4>🏅 Procedural Compliance Certified</h4>
            <p style='font-size: 0.85em; color: #a5d6a7;'>All mandatory steps verified without unresolved critical hazards.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Build cryptographically verified audit payload
        report_data = {
            "auditor": "SynapseAudit Autonomous Agent v1.0",
            "completion_time": datetime.now().isoformat(),
            "total_steps": len(st.session_state.active_protocol),
            "verified_steps": engine.verified_steps,
            "violations_intercepted": engine.violation_history,
            "audit_trail": st.session_state.audit_log
        }
        raw_json = json.dumps(report_data, indent=2)
        cert_hash = hashlib.sha256(raw_json.encode('utf-8')).hexdigest()
        report_data["integrity_sha256"] = cert_hash
        final_json_str = json.dumps(report_data, indent=2)

        st.download_button(
            label="📥 Download Signed Audit Certificate (JSON)",
            data=final_json_str,
            file_name=f"synapse_audit_cert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )

# --- High-Definition Stream Loop ---
if run_camera:
    cap = cv2.VideoCapture(0)
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

            # Draw targeting corners
            cv2.line(frame, (x1, y1), (x1 + line_len, y1), color, thickness)
            cv2.line(frame, (x1, y1), (x1, y1 + line_len), color, thickness)
            cv2.line(frame, (x2, y1), (x2 - line_len, y1), color, thickness)
            cv2.line(frame, (x2, y1), (x2, y1 + line_len), color, thickness)
            cv2.line(frame, (x1, y2), (x1 + line_len, y2), color, thickness)
            cv2.line(frame, (x1, y2), (x1, y2 - line_len), color, thickness)
            cv2.line(frame, (x2, y2), (x2 - line_len, y2), color, thickness)
            cv2.line(frame, (x2, y2), (x2 - line_len, y2), color, thickness)

            cv2.putText(frame, "HARDWARE GROUNDING ZONE", (x1, max(30, y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

            if st.session_state.system_status == "VIOLATION":
                cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 255), 8)

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            video_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)

            time.sleep(0.03)
    finally:
        cap.release()