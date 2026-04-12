"""
UEBA (User and Entity Behavior Analytics) Service
Detects insider threats and anomalous behavior using ML
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from core.logger import get_logger

logger = get_logger(__name__)


class BehaviorType(Enum):
    """Types of behaviors to monitor."""

    LOGIN = "login"
    FILE_ACCESS = "file_access"
    NETWORK_ACCESS = "network_access"
    DATA_EXFILTRATION = "data_exfiltration"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    LATERAL_MOVEMENT = "lateral_movement"


class RiskLevel(Enum):
    """Risk level classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class BehaviorBaseline:
    """User/entity behavior baseline."""

    entity_id: str
    entity_type: str  # user, host, ip
    login_times: list[int]  # Hour of day (0-23)
    accessed_resources: list[str]
    peer_group: list[str]
    typical_data_volume: float
    typical_connections: int
    last_updated: datetime


@dataclass
class AnomalyDetection:
    """Anomaly detection result."""

    entity_id: str
    behavior_type: BehaviorType
    anomaly_score: float
    risk_level: RiskLevel
    description: str
    indicators: list[str]
    recommended_actions: list[str]
    detected_at: datetime


@dataclass
class UserRiskProfile:
    """Comprehensive user risk profile."""

    user_id: str
    username: str
    overall_risk_score: float  # 0-100
    risk_level: RiskLevel
    risk_factors: list[dict[str, Any]]
    anomalous_behaviors: list[AnomalyDetection]
    compromised_probability: float
    last_activity: datetime


class UEBAEngine:
    """UEBA detection engine."""

    def __init__(self):
        self.baselines: dict[str, BehaviorBaseline] = {}
        self.scaler = StandardScaler()
        self.isolation_forest = IsolationForest(
            contamination=0.1,  # Expected 10% anomalies
            random_state=42,
            n_estimators=100,
        )
        self._model_trained = False

    async def build_baseline(
        self, entity_id: str, entity_type: str, days_of_history: int = 30
    ) -> BehaviorBaseline:
        """
        Build behavior baseline for an entity from historical data.

        Args:
            entity_id: User ID, host ID, or IP address
            entity_type: Type of entity
            days_of_history: Days of historical data to analyze

        Returns:
            Behavior baseline
        """
        logger.info(f"Building baseline for {entity_type} {entity_id}")

        # In production, query from database
        # For now, simulate with default values
        baseline = BehaviorBaseline(
            entity_id=entity_id,
            entity_type=entity_type,
            login_times=[9, 10, 11, 14, 15, 16],  # Business hours
            accessed_resources=["file_share", "email", "vpn"],
            peer_group=["user1", "user2", "user3"],
            typical_data_volume=100.0,  # MB
            typical_connections=10,
            last_updated=datetime.now(),
        )

        self.baselines[entity_id] = baseline
        return baseline

    async def detect_anomalies(
        self, entity_id: str, current_behavior: dict[str, Any]
    ) -> list[AnomalyDetection]:
        """
        Detect anomalies in current behavior compared to baseline.

        Args:
            entity_id: Entity to check
            current_behavior: Current behavior metrics

        Returns:
            List of detected anomalies
        """
        anomalies = []

        # Get baseline
        baseline = self.baselines.get(entity_id)
        if not baseline:
            baseline = await self.build_baseline(entity_id, "user")

        # Check login time anomaly
        if "login_time" in current_behavior:
            login_hour = current_behavior["login_time"].hour
            if login_hour not in baseline.login_times:
                anomalies.append(
                    AnomalyDetection(
                        entity_id=entity_id,
                        behavior_type=BehaviorType.LOGIN,
                        anomaly_score=0.7,
                        risk_level=RiskLevel.MEDIUM,
                        description=f"Login at unusual hour: {login_hour}:00",
                        indicators=["off_hours_login", "unusual_time"],
                        recommended_actions=["verify_identity", "check_vpn_logs"],
                        detected_at=datetime.now(),
                    )
                )

        # Check data volume anomaly
        if "data_volume_mb" in current_behavior:
            current_volume = current_behavior["data_volume_mb"]
            if current_volume > baseline.typical_data_volume * 5:
                anomalies.append(
                    AnomalyDetection(
                        entity_id=entity_id,
                        behavior_type=BehaviorType.DATA_EXFILTRATION,
                        anomaly_score=0.9,
                        risk_level=RiskLevel.HIGH,
                        description=f"Unusual data volume: {current_volume}MB (typical: {baseline.typical_data_volume}MB)",
                        indicators=["large_data_transfer", "potential_exfiltration"],
                        recommended_actions=[
                            "investigate_destination",
                            "review_file_access",
                        ],
                        detected_at=datetime.now(),
                    )
                )

        # Check lateral movement
        if "accessed_hosts" in current_behavior:
            accessed = current_behavior["accessed_hosts"]
            if len(accessed) > baseline.typical_connections * 3:
                anomalies.append(
                    AnomalyDetection(
                        entity_id=entity_id,
                        behavior_type=BehaviorType.LATERAL_MOVEMENT,
                        anomaly_score=0.85,
                        risk_level=RiskLevel.HIGH,
                        description=f"Access to {len(accessed)} hosts (typical: {baseline.typical_connections})",
                        indicators=["lateral_movement", "network_scanning"],
                        recommended_actions=["isolate_host", "check_for_malware"],
                        detected_at=datetime.now(),
                    )
                )

        return anomalies

    async def calculate_risk_score(
        self, entity_id: str, recent_anomalies: list[AnomalyDetection]
    ) -> tuple[float, RiskLevel]:
        """
        Calculate overall risk score based on anomalies.

        Args:
            entity_id: Entity ID
            recent_anomalies: Recent anomaly detections

        Returns:
            (risk_score, risk_level)
        """
        if not recent_anomalies:
            return 0.0, RiskLevel.LOW

        # Calculate weighted score
        weights = {
            BehaviorType.LOGIN: 0.1,
            BehaviorType.FILE_ACCESS: 0.15,
            BehaviorType.NETWORK_ACCESS: 0.2,
            BehaviorType.DATA_EXFILTRATION: 0.3,
            BehaviorType.PRIVILEGE_ESCALATION: 0.35,
            BehaviorType.LATERAL_MOVEMENT: 0.4,
        }

        total_score = 0.0
        for anomaly in recent_anomalies:
            weight = weights.get(anomaly.behavior_type, 0.1)
            total_score += anomaly.anomaly_score * weight * 100

        # Cap at 100
        risk_score = min(total_score, 100.0)

        # Determine risk level
        if risk_score >= 80:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 60:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 30:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        return risk_score, risk_level

    async def get_user_risk_profile(
        self, user_id: str, days_to_analyze: int = 7
    ) -> UserRiskProfile:
        """
        Get comprehensive risk profile for a user.

        Args:
            user_id: User ID
            days_to_analyze: Days of history to analyze

        Returns:
            User risk profile
        """
        # In production, fetch from database
        # For now, return sample data

        sample_anomalies = [
            AnomalyDetection(
                entity_id=user_id,
                behavior_type=BehaviorType.LOGIN,
                anomaly_score=0.7,
                risk_level=RiskLevel.MEDIUM,
                description="Login from unusual location: Beijing, China",
                indicators=["geolocation_anomaly", "impossible_travel"],
                recommended_actions=["verify_identity", "enable_2fa"],
                detected_at=datetime.now() - timedelta(hours=2),
            )
        ]

        risk_score, risk_level = await self.calculate_risk_score(
            user_id, sample_anomalies
        )

        return UserRiskProfile(
            user_id=user_id,
            username=f"user_{user_id}",
            overall_risk_score=risk_score,
            risk_level=risk_level,
            risk_factors=[
                {
                    "type": "geolocation",
                    "severity": "medium",
                    "description": "Unusual login location",
                },
                {
                    "type": "time",
                    "severity": "low",
                    "description": "Off-hours activity",
                },
            ],
            anomalous_behaviors=sample_anomalies,
            compromised_probability=(
                0.3 if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] else 0.05
            ),
            last_activity=datetime.now(),
        )

    async def detect_peer_group_anomalies(
        self, entity_id: str, peer_group: list[str]
    ) -> list[AnomalyDetection]:
        """
        Detect when entity behaves differently from peer group.

        Args:
            entity_id: Entity to check
            peer_group: List of peer entity IDs

        Returns:
            List of peer-based anomalies
        """
        anomalies = []

        # Compare entity behavior to peer group average
        # In production, this would involve statistical analysis

        return anomalies

    async def train_ml_models(self, historical_data: list[dict[str, Any]]):
        """
        Train ML models on historical data.

        Args:
            historical_data: Historical behavior data
        """
        if len(historical_data) < 100:
            logger.warning("Insufficient data for ML training")
            return

        try:
            # Extract features
            features = []
            for record in historical_data:
                feature_vector = [
                    record.get("login_hour", 9),
                    record.get("data_volume_mb", 0),
                    record.get("num_connections", 0),
                    record.get("num_files_accessed", 0),
                    record.get("unique_hosts", 0),
                ]
                features.append(feature_vector)

            X = np.array(features)
            X_scaled = self.scaler.fit_transform(X)

            # Train isolation forest
            self.isolation_forest.fit(X_scaled)
            self._model_trained = True

            logger.info("UEBA ML models trained successfully")

        except Exception as e:
            logger.error(f"Error training ML models: {e}")

    async def predict_with_ml(self, behavior_vector: list[float]) -> tuple[bool, float]:
        """
        Predict if behavior is anomalous using ML.

        Args:
            behavior_vector: Behavior features

        Returns:
            (is_anomaly, confidence_score)
        """
        if not self._model_trained:
            return False, 0.0

        try:
            X = np.array([behavior_vector])
            X_scaled = self.scaler.transform(X)

            prediction = self.isolation_forest.predict(X_scaled)
            score = self.isolation_forest.score_samples(X_scaled)[0]

            is_anomaly = prediction[0] == -1
            confidence = abs(score)

            return is_anomaly, confidence

        except Exception as e:
            logger.error(f"Error in ML prediction: {e}")
            return False, 0.0


# Global UEBA engine instance
_ueba_engine: UEBAEngine | None = None


def get_ueba_engine() -> UEBAEngine:
    """Get or create global UEBA engine."""
    global _ueba_engine
    if _ueba_engine is None:
        _ueba_engine = UEBAEngine()
    return _ueba_engine


async def initialize_ueba():
    """Initialize UEBA on application startup."""
    global _ueba_engine
    _ueba_engine = UEBAEngine()
    logger.info("UEBA engine initialized")


async def close_ueba():
    """Cleanup UEBA on application shutdown."""
    global _ueba_engine
    if _ueba_engine:
        logger.info("UEBA engine closed")
        _ueba_engine = None
