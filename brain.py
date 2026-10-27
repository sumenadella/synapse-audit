import os
import json
import base64
from typing import Dict, Any, List
from pydantic import BaseModel, Field

# Verifiable Agent Schema
class AuditDecision(BaseModel):
    step_id: int
    compliance: str = Field(description="COMPLIANT, VIOLATION, or IDLE")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    detected_action: str = Field(description="Exact physical action seen by camera")
    intervene: bool = Field(description="True if dangerous action or violation occurred")
    voice_alert: str = Field(description="Short phrase spoken to operator")
    prerequisite_met: bool = Field(description="Whether previous prerequisite steps hold true")

class SOPStateEngine:
    def __init__(self, protocol: List[Dict[str, Any]]):
        self.protocol = protocol
        self.current_step_idx = 0
        self.violation_history = []
        self.verified_steps = []

    def get_active_step(self) -> Dict[str, Any]:
        if self.current_step_idx < len(self.protocol):
            return self.protocol[self.current_step_idx]
        return None

    def is_protocol_complete(self) -> bool:
        return self.current_step_idx >= len(self.protocol)

    def verify_current_step(self, note: str = "Passed by auditor"):
        active = self.get_active_step()
        if active:
            self.verified_steps.append({
                "step_id": active["step_id"],
                "title": active["title"],
                "note": note
            })
            self.current_step_idx += 1
            return True
        return False

    def log_violation(self, reason: str):
        active = self.get_active_step()
        step_id = active["step_id"] if active else -1
        self.violation_history.append({
            "step_id": step_id,
            "reason": reason
        })

    def reset(self):
        self.current_step_idx = 0
        self.violation_history.clear()
        self.verified_steps.clear()

    def build_agent_prompt(self, base64_image: str) -> Dict[str, Any]:
        """Constructs a verifiable multimodal prompt for Meta Muse Spark / Llama Vision"""
        active = self.get_active_step()
        if not active:
            return None

        prompt_instruction = f"""
You are SynapseAudit, an autonomous mission-critical compliance agent.
Current SOP Step {active['step_id']}: {active['title']}
Required Action: {active['description']}
Critical Safety Hazard: {active['violation']}

Previous Verified Steps: {[s['title'] for s in self.verified_steps]}

Inspect the provided frame. Determine if the operator is safely complying, in the middle of a mistake, or idle.
Respond STRICTLY with valid JSON following this schema:
{{
  "step_id": {active['step_id']},
  "compliance": "COMPLIANT" | "VIOLATION" | "IDLE",
  "confidence": 0.95,
  "detected_action": "<what hands/tools are doing>",
  "intervene": true | false,
  "voice_alert": "<short phrase to say>",
  "prerequisite_met": true | false
}}
"""
        return {
            "model": "meta-models/muse-spark-open-1026",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_instruction},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            "temperature": 0.0,
            "max_tokens": 250
        }