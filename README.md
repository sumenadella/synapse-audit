# SynapseAudit 🛡️
> Real-Time Procedural Compliance & Safety Interceptor for Mission-Critical Infrastructure.

Built for the **Meta Global AI Developer Hackathon 2026**  
Track: **Indie Developer** | Problem Statement: **Push the Frontier**

## Overview
In critical aerospace, server operations, and electrical facilities, human error during routine maintenance leads to massive equipment loss and physical danger. Traditional audits happen *post-mortem* via incident logs. 

**SynapseAudit** provides real-time, pre-action computer vision and autonomous voice intervention. It tracks continuous technician actions against live Standard Operating Procedures (SOPs), segments target components, and interrupts deviations *before* physical mistakes turn catastrophic.

## Key Features
- **Verifiable Agent State Machine:** Multi-step deterministic procedural tracking built on Pydantic schemas.
- **Visual Grounding:** Real-time targeting crosshairs to identify and track hardware components.
- **Autonomous Voice Interceptor:** Asynchronous TTS alert engine that speaks immediately upon detecting safety violations.
- **Mission-Critical Telemetry Dashboard:** Full dark-mode web console tracking audit logs, verified steps, and risk states.

## Architecture Pipeline
- **Reasoning Agent:** Meta Muse Spark Open (`meta-models/muse-spark-open-1026`) via Meta Model API / Baseten.
- **Component Grounding:** Meta SAM 3.1 & edge contour reticles.
- **Runtime:** Python, OpenCV, Streamlit, PyTTSx3.

## Quickstart

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/sumenadella/synapse-audit.git](https://github.com/sumenadella/synapse-audit.git)
   cd synapse-audit