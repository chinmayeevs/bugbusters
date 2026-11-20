"""
agents/orchestrator_agent.py
AI Orchestrator: Explicit Python state machine coordinating exactly three reasoning agents in sequence:
  1. Triage Agent (agents/triage_agent.py)
  2. Root-Cause Agent (agents/root_cause_agent.py)
  3. Risk Validator Agent (agents/risk_validator_agent.py - strict maker-checker gate)
Enforces strict Pydantic contract compliance and end-to-end evidence traceability.
"""

from __future__ import annotations
import asyncio
import time
from enum import Enum
from typing import Tuple, Dict, Any, Optional

from backend.models.contracts import (
    ComputeResult,
    TriageReport,
    RootCauseReport,
    RiskValidationReport,
)
from agents.triage_agent import TriageAgent
from agents.root_cause_agent import RootCauseAgent
from agents.risk_validator_agent import RiskValidatorAgent


class AIOrchestratorState(str, Enum):
    IDLE = "IDLE"
    TRIAGING = "TRIAGING"
    ROOT_CAUSE_ANALYSIS = "ROOT_CAUSE_ANALYSIS"
    RISK_VALIDATING = "RISK_VALIDATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AIOrchestrator:
    def __init__(self):
        self.triage_agent = TriageAgent()
        self.root_cause_agent = RootCauseAgent()
        self.risk_validator_agent = RiskValidatorAgent()
        self.state = AIOrchestratorState.IDLE
        self.stage_telemetry: Dict[str, float] = {}

    async def execute(
        self,
        packet: ComputeResult,
        runtime_hints: Optional[Dict[str, Any]] = None
    ) -> Tuple[TriageReport, RootCauseReport, RiskValidationReport]:
        """
        Runs the 3-stage agent sequence through an explicit state machine.
        """
        runtime_hints = runtime_hints or {}

        # -------------------------------------------------------------
        # Stage 1: Triage
        # -------------------------------------------------------------
        self.state = AIOrchestratorState.TRIAGING
        t0 = time.perf_counter()
        triage_report = await self.triage_agent.run(packet, hints=runtime_hints)
        self.stage_telemetry["triage_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        # -------------------------------------------------------------
        # Stage 2: Root Cause Analysis
        # -------------------------------------------------------------
        self.state = AIOrchestratorState.ROOT_CAUSE_ANALYSIS
        t1 = time.perf_counter()
        root_cause_report = await self.root_cause_agent.run(packet, triage=triage_report, hints=runtime_hints)
        self.stage_telemetry["root_cause_ms"] = round((time.perf_counter() - t1) * 1000, 2)

        # -------------------------------------------------------------
        # Stage 3: Risk Validator (Maker-Checker Gate)
        # -------------------------------------------------------------
        self.state = AIOrchestratorState.RISK_VALIDATING
        t2 = time.perf_counter()
        risk_report = await self.risk_validator_agent.run(
            packet,
            triage=triage_report,
            root_cause=root_cause_report,
            hints=runtime_hints
        )
        self.stage_telemetry["risk_validation_ms"] = round((time.perf_counter() - t2) * 1000, 2)

        self.state = AIOrchestratorState.COMPLETED
        return triage_report, root_cause_report, risk_report
