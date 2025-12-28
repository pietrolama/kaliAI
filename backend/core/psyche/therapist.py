"""
Therapist Module - Post-mission psychological analysis and psyche adjustment.

After each mission:
1. Analyzes technical logs and dialog patterns
2. Correlates events with current psyche state
3. Generates therapy session summary
4. Adjusts dopamine/cortisol for system stability
"""

import os
import json
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from .neuro_system import get_psyche, PsycheSystem
from .log_parser import get_parser, MissionAnalysis, EventType, DialogTone

logger = logging.getLogger('Therapist')


@dataclass
class TherapyReport:
    """Results of a therapy session."""
    mission_id: str
    timestamp: str
    
    # Analysis
    technical_summary: str
    dialog_summary: str
    correlation_notes: str
    
    # Pre/Post state
    pre_dopamine: float
    pre_cortisol: float
    post_dopamine: float
    post_cortisol: float
    
    # Metrics
    mission_score: float
    success_count: int
    failure_count: int
    hallucination_count: int
    
    # Therapist notes
    therapist_notes: str
    recommendations: List[str]


class Therapist:
    """
    The system's psychological counselor.
    Analyzes mission outcomes and adjusts psyche for stability.
    """
    
    # Adjustment rules based on events
    ADJUSTMENT_RULES = {
        "mission_success": {"dopamine": 0.15, "cortisol": -0.10},
        "mission_partial": {"dopamine": 0.05, "cortisol": -0.03},
        "mission_failure": {"dopamine": -0.10, "cortisol": 0.15},
        "hallucination": {"dopamine": -0.20, "cortisol": 0.25},
        "creative_solution": {"dopamine": 0.20, "cortisol": -0.05},
        "timeout_stall": {"dopamine": 0.0, "cortisol": 0.10},
        "risk_detected": {"dopamine": -0.05, "cortisol": 0.08},
    }
    
    def __init__(self, psyche: Optional[PsycheSystem] = None, llm_config: Optional[Dict] = None):
        self.psyche = psyche or get_psyche()
        self.parser = get_parser()
        self.llm_config = llm_config
        self.session_log_path = "data/session/therapy_log.json"
        self._mission_counter = 0
    
    def analyze_mission(
        self, 
        technical_log: str, 
        dialog_log: List[Dict[str, Any]],
        mission_id: Optional[str] = None
    ) -> TherapyReport:
        """
        Perform full psychological analysis of a completed mission.
        
        Now integrates with Execution Ledger for accurate metrics.
        
        Args:
            technical_log: Raw output from commands executed
            dialog_log: List of agent messages from the mission
            mission_id: Optional identifier for the mission
            
        Returns:
            TherapyReport with analysis and adjustments
        """
        self._mission_counter += 1
        mission_id = mission_id or f"mission_{self._mission_counter}"
        
        # Capture pre-state
        pre_state = self.psyche.get_emotional_state()
        pre_dopamine = pre_state["dopamine"]
        pre_cortisol = pre_state["cortisol"]
        
        # Parse logs
        analysis = self.parser.analyze_mission(technical_log, dialog_log)
        
        # 📝 LEDGER INTEGRATION: Enhance analysis with Ledger data
        try:
            from backend.core.ledger import get_ledger
            ledger = get_ledger()
            ledger_metrics = ledger.compute_metrics()
            
            # Use Ledger tool counts if higher (more accurate)
            tool_calls = ledger_metrics.get("total_tool_calls", 0)
            success_rate = ledger_metrics.get("success_rate", 0)
            
            if tool_calls > 0:
                # Override with real data from Ledger
                ledger_successes = int(tool_calls * success_rate)
                ledger_failures = tool_calls - ledger_successes
                
                # Use maximum of parser or ledger (Ledger is more accurate)
                if ledger_successes > analysis.success_count:
                    analysis.success_count = ledger_successes
                if ledger_failures > analysis.failure_count:
                    analysis.failure_count = ledger_failures
                
                # Recalculate score based on Ledger data
                total = analysis.success_count + analysis.failure_count
                if total > 0:
                    analysis.mission_score = analysis.success_count / total
                    # Apply hallucination penalty
                    analysis.mission_score *= (1 - (analysis.hallucination_count * 0.2))
                    analysis.mission_score = max(0.0, min(1.0, analysis.mission_score))
                    
        except ImportError:
            pass  # Ledger not available, use parser data only
        except Exception as e:
            import logging
            logging.getLogger("Therapist").warning(f"Ledger integration error: {e}")
        
        # Generate summaries
        technical_summary = self._generate_technical_summary(analysis)
        dialog_summary = self._generate_dialog_summary(analysis)
        correlation_notes = self._correlate_events_with_psyche(analysis, pre_state)
        
        # Apply adjustments
        self._apply_adjustments(analysis)
        
        # Capture post-state
        post_state = self.psyche.get_emotional_state()
        
        # Generate therapist notes
        therapist_notes = self._generate_therapist_notes(analysis, pre_state, post_state)
        recommendations = self._generate_recommendations(analysis, post_state)
        
        report = TherapyReport(
            mission_id=mission_id,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            technical_summary=technical_summary,
            dialog_summary=dialog_summary,
            correlation_notes=correlation_notes,
            pre_dopamine=pre_dopamine,
            pre_cortisol=pre_cortisol,
            post_dopamine=post_state["dopamine"],
            post_cortisol=post_state["cortisol"],
            mission_score=analysis.mission_score,
            success_count=analysis.success_count,
            failure_count=analysis.failure_count,
            hallucination_count=analysis.hallucination_count,
            therapist_notes=therapist_notes,
            recommendations=recommendations
        )
        
        # Save to log
        self._save_session(report)
        
        return report
    
    def _generate_technical_summary(self, analysis: MissionAnalysis) -> str:
        """Summarize technical events."""
        total = len(analysis.events)
        if total == 0:
            return "No significant technical events detected."
        
        lines = [
            f"Commands executed: {total}",
            f"Success rate: {(analysis.success_count / total * 100):.0f}%",
        ]
        
        if analysis.failure_count > 0:
            lines.append(f"Failures: {analysis.failure_count}")
        if analysis.risk_count > 0:
            lines.append(f"Risk events: {analysis.risk_count}")
        if analysis.hallucination_count > 0:
            lines.append(f"⚠️ HALLUCINATIONS DETECTED: {analysis.hallucination_count}")
        
        return " | ".join(lines)
    
    def _generate_dialog_summary(self, analysis: MissionAnalysis) -> str:
        """Summarize dialog patterns."""
        if not analysis.dialog_events:
            return "No dialog recorded."
        
        # Count agent participation
        agent_counts = {}
        for de in analysis.dialog_events:
            agent_counts[de.agent] = agent_counts.get(de.agent, 0) + 1
        
        most_active = max(agent_counts, key=agent_counts.get) if agent_counts else "unknown"
        decisions = sum(1 for de in analysis.dialog_events if de.is_decision)
        tool_calls = sum(1 for de in analysis.dialog_events if de.is_tool_call)
        
        return f"Dominant agent: {most_active} | Tone: {analysis.dominant_tone.value} | Decisions: {decisions} | Tool calls: {tool_calls}"
    
    def _correlate_events_with_psyche(self, analysis: MissionAnalysis, pre_state: Dict) -> str:
        """Correlate mission events with psyche state."""
        notes = []
        
        cortisol = pre_state["cortisol"]
        dopamine = pre_state["dopamine"]
        state = pre_state["state"]
        
        # High cortisol correlations
        if cortisol > 0.5:
            if analysis.failure_count > analysis.success_count:
                notes.append(f"Elevated stress (cortisol={cortisol:.2f}) may have contributed to higher failure rate.")
            if analysis.dominant_tone == DialogTone.CAUTIOUS:
                notes.append("Cautious tone in dialog aligns with elevated cortisol - expected behavior.")
        
        # Low dopamine correlations
        if dopamine < 0.4:
            if analysis.mission_score < 0.5:
                notes.append(f"Low motivation (dopamine={dopamine:.2f}) correlates with below-average mission score.")
        
        # High dopamine correlations
        if dopamine > 0.7:
            if analysis.hallucination_count > 0:
                notes.append("⚠️ High confidence (high dopamine) may have led to hallucinated outputs.")
            if analysis.dominant_tone == DialogTone.AGGRESSIVE:
                notes.append("Aggressive tone matches elevated dopamine - monitoring for overconfidence.")
        
        # State-specific observations
        if state == "PARANOID":
            notes.append("System was in PARANOID state - expect slower, more cautious execution.")
        elif state == "MANIC":
            notes.append("System was in MANIC state - fast execution but higher risk of errors.")
        elif state == "FLOW":
            notes.append("System was in optimal FLOW state - expect balanced performance.")
        
        return " | ".join(notes) if notes else "No significant correlations detected."
    
    def _apply_adjustments(self, analysis: MissionAnalysis):
        """Apply psyche adjustments based on mission analysis."""
        # Determine overall mission outcome
        if analysis.hallucination_count > 0:
            # Severe penalty for hallucinations
            adj = self.ADJUSTMENT_RULES["hallucination"]
            self.psyche.dopamine = max(0.0, self.psyche.dopamine + adj["dopamine"])
            self.psyche.cortisol = min(1.0, self.psyche.cortisol + adj["cortisol"])
            logger.warning(f"Hallucination penalty applied: dopamine {adj['dopamine']}, cortisol {adj['cortisol']}")
        
        elif analysis.mission_score >= 0.8:
            # Success
            adj = self.ADJUSTMENT_RULES["mission_success"]
            self.psyche.stimulate(adj["dopamine"])
            logger.info(f"Success reward applied: dopamine +{adj['dopamine']}")
        
        elif analysis.mission_score >= 0.5:
            # Partial success
            adj = self.ADJUSTMENT_RULES["mission_partial"]
            self.psyche.stimulate(adj["dopamine"])
            logger.info(f"Partial success reward applied: dopamine +{adj['dopamine']}")
        
        else:
            # Failure
            adj = self.ADJUSTMENT_RULES["mission_failure"]
            self.psyche.stress(adj["cortisol"])
            logger.info(f"Failure penalty applied: cortisol +{adj['cortisol']}")
        
        # Additional adjustments for risk events
        if analysis.risk_count > 2:
            adj = self.ADJUSTMENT_RULES["risk_detected"]
            self.psyche.stress(abs(adj["cortisol"]))
    
    def _generate_therapist_notes(
        self, 
        analysis: MissionAnalysis, 
        pre_state: Dict, 
        post_state: Dict
    ) -> str:
        """Generate therapist's narrative notes."""
        notes = []
        
        # Overall assessment
        if analysis.mission_score >= 0.8:
            notes.append("The team performed admirably.")
        elif analysis.mission_score >= 0.5:
            notes.append("Performance was acceptable with room for improvement.")
        else:
            notes.append("This mission presented significant challenges.")
        
        # Hallucination feedback
        if analysis.hallucination_count > 0:
            notes.append(
                f"⚠️ {analysis.hallucination_count} hallucination event(s) detected. "
                "This is a serious issue requiring immediate attention. "
                "The system may be overconfident in its predictions."
            )
        
        # State transition commentary
        pre_st = pre_state["state"]
        post_st = post_state["state"]
        if pre_st != post_st:
            notes.append(f"Emotional state transitioned from {pre_st} to {post_st}.")
        
        # Dopamine/Cortisol delta
        d_delta = post_state["dopamine"] - pre_state["dopamine"]
        c_delta = post_state["cortisol"] - pre_state["cortisol"]
        
        if abs(d_delta) > 0.1 or abs(c_delta) > 0.1:
            direction = "improved" if d_delta > 0 and c_delta < 0 else "shifted"
            notes.append(f"Neurochemistry has {direction} (Δdopamine: {d_delta:+.2f}, Δcortisol: {c_delta:+.2f}).")
        
        return " ".join(notes)
    
    def _generate_recommendations(self, analysis: MissionAnalysis, post_state: Dict) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # State-based recommendations
        state = post_state["state"]
        if state == "PARANOID":
            recommendations.append("Consider simpler, lower-risk tasks to rebuild confidence.")
        elif state == "MANIC":
            recommendations.append("Recommend verification steps before executing critical commands.")
        elif state == "ANXIOUS":
            recommendations.append("Allow extra time for reconnaissance before action.")
        
        # Event-based recommendations
        if analysis.hallucination_count > 0:
            recommendations.append("CRITICAL: Review tool execution to ensure actual commands are run.")
            recommendations.append("Consider enabling stricter output validation.")
        
        if analysis.failure_count > analysis.success_count:
            recommendations.append("Focus on simpler targets to improve success rate.")
        
        if analysis.dominant_tone == DialogTone.FRUSTRATED:
            recommendations.append("Team morale may be low. Consider a rest period.")
        
        return recommendations
    
    def _save_session(self, report: TherapyReport):
        """Save therapy session to persistent log."""
        try:
            os.makedirs(os.path.dirname(self.session_log_path), exist_ok=True)
            
            # Load existing log
            sessions = []
            if os.path.exists(self.session_log_path):
                with open(self.session_log_path, "r") as f:
                    sessions = json.load(f)
            
            # Append new session
            sessions.append(asdict(report))
            
            # Keep only last 50 sessions
            sessions = sessions[-50:]
            
            with open(self.session_log_path, "w") as f:
                json.dump(sessions, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save therapy session: {e}")
    
    def format_report(self, report: TherapyReport) -> str:
        """Format report for display."""
        lines = [
            "═" * 60,
            f"🧠 THERAPY SESSION REPORT - {report.mission_id}",
            "═" * 60,
            "",
            "📊 MISSION ANALYSIS:",
            f"   Score: {report.mission_score * 100:.0f}%",
            f"   Successes: {report.success_count} | Failures: {report.failure_count}",
            f"   Hallucinations: {report.hallucination_count}",
            "",
            "📝 TECHNICAL SUMMARY:",
            f"   {report.technical_summary}",
            "",
            "💬 DIALOG SUMMARY:",
            f"   {report.dialog_summary}",
            "",
            "🔗 PSYCHE CORRELATION:",
            f"   {report.correlation_notes}",
            "",
            "📈 ADJUSTMENTS APPLIED:",
            f"   Dopamine: {report.pre_dopamine:.2f} → {report.post_dopamine:.2f} ({report.post_dopamine - report.pre_dopamine:+.2f})",
            f"   Cortisol: {report.pre_cortisol:.2f} → {report.post_cortisol:.2f} ({report.post_cortisol - report.pre_cortisol:+.2f})",
            "",
            "💭 THERAPIST NOTES:",
            f"   {report.therapist_notes}",
        ]
        
        if report.recommendations:
            lines.append("")
            lines.append("📋 RECOMMENDATIONS:")
            for rec in report.recommendations:
                lines.append(f"   • {rec}")
        
        lines.append("")
        lines.append("═" * 60)
        
        return "\n".join(lines)


# Singleton instance
_therapist = None

def get_therapist() -> Therapist:
    global _therapist
    if _therapist is None:
        _therapist = Therapist()
    return _therapist
