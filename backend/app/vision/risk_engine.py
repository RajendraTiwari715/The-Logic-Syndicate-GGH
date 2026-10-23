from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

from app.config import settings


@dataclass(slots=True)
class RiskSignals:
    object_class: str
    zone_name: str | None = None
    restricted_zone: bool = False
    fence_crossed: bool = False
    loitering: bool = False
    night_time: bool = False
    camera_offline: bool = False
    repeated_direction_changes: bool = False
    low_traffic_period: bool = False
    watchlist_match: bool = False

@dataclass(slots=True)
class RiskEvaluation:
    score: int
    severity: str
    reasons: list[str]
    explanation: str


def score_to_severity(score: int) -> str:
    if score <= 30:
        return "LOW"
    if score <= 60:
        return "MEDIUM"
    if score <= 80:
        return "HIGH"
    return "CRITICAL"


class RiskEngine:
    def __init__(self) -> None:
        self.night_start = self._parse_time(settings.night_start)
        self.night_end = self._parse_time(settings.night_end)

    @staticmethod
    def _parse_time(value: str) -> time:
        hour, minute = value.split(":")
        return time(hour=int(hour), minute=int(minute))

    def is_night_time(self, when: datetime | None = None) -> bool:
        now = (when or datetime.now()).time()
        if self.night_start <= self.night_end:
            return self.night_start <= now <= self.night_end
        return now >= self.night_start or now <= self.night_end

    def evaluate(self, signals: RiskSignals) -> RiskEvaluation:
        score = 10
        reasons: list[str] = ["Person detected" if signals.object_class == "person" else f"{signals.object_class.title()} detected"]
        explanation = "Normal activity."

        if signals.watchlist_match:
            score = 95
            reasons.append("Watchlist match")
            explanation = "Biometric/Plate match against active Watchlist."

        # Rule Combinations
        if signals.restricted_zone and signals.night_time and signals.loitering:
            score = max(score, 85)
            reasons.append("Nighttime Restricted Loitering")
            explanation = "Elevated Risk: Subject is loitering in a restricted zone during night hours."
        elif signals.repeated_direction_changes and signals.low_traffic_period and not signals.restricted_zone:
            score = max(score, 65)
            reasons.append("Suspicious Movement Pattern")
            explanation = "Unusual tracking: Repeated direction changes during low traffic period."
        else:
            if signals.restricted_zone:
                score += 32
                reasons.append("Restricted zone")
            if signals.fence_crossed:
                score += 35
                reasons.append("Virtual fence crossed")
            if signals.loitering:
                score += 28
                reasons.append(f"Loitering detected")
            if signals.night_time:
                score += 15
                reasons.append("Night-time movement")
            if signals.camera_offline:
                score = max(score, 72)
                reasons.append("Camera offline")

        score = min(score, 100)
        
        # Generate Simulated Edge-LLM Tactical Narrative Brief
        time_str = datetime.now().strftime("%H:%M")
        subj_str = f"an unidentified {signals.object_class}"
        if signals.restricted_zone and signals.night_time:
            narrative = f"TACTICAL BRIEF: At {time_str} Hrs, {subj_str} initiated an unauthorized approach into a Restricted Zone under cover of darkness. Risk of reconnaissance or boundary sabotage is HIGH."
        elif signals.fence_crossed:
            narrative = f"TACTICAL BRIEF: Perimeter breach detected at {time_str} Hrs. {subj_str} crossed the virtual demarcation line. Immediate interdiction recommended."
        elif signals.repeated_direction_changes:
            narrative = f"TACTICAL BRIEF: Tracked {subj_str} executing evasive/repeated direction changes during low traffic window ({time_str} Hrs). Potential scoping pattern observed."
        elif signals.loitering:
            narrative = f"TACTICAL BRIEF: {subj_str} has occupied a static position (Loitering) in the monitored sector beyond acceptable dwell thresholds. Subject may be observing patrol routes."
        else:
            narrative = f"Routine detection of {subj_str} logged at {time_str} Hrs. No immediate tactical threat."
            
        # Override basic explanation with the Tactical Narrative
        explanation = narrative
            
        return RiskEvaluation(score=score, severity=score_to_severity(score), reasons=reasons, explanation=explanation)
