"""UEBA service - upgraded with DB-backed baselines and real data extraction.

F3-4: Data pipeline upgrade from demo to production-ready.
"""

import json
import pickle
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

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


# ── Feature extraction helpers ──────────────────────────────────────────


async def _extract_behavior_features_from_db(
    session: AsyncSession, user_id: str, days: int = 30
) -> dict[str, Any]:
    """Extract 6-class behavior features from real database tables.

    Queries security_alerts and audit_logs to compute:
        login_count, login_failures, file_access_count,
        network_connections, privilege_escalation, lateral_movement

    Args:
        session: Async database session
        user_id: Target user ID
        days: Lookback window in days

    Returns:
        Dict with feature values keyed by feature name
    """
    since = datetime.now() - timedelta(days=days)
    since_iso = since.isoformat()

    features: dict[str, Any] = {
        "login_count": 0,
        "login_failures": 0,
        "file_access_count": 0,
        "network_connections": 0,
        "privilege_escalation": 0,
        "lateral_movement": 0,
        "data_volume_mb": 0.0,
        "unique_hosts": 0,
    }

    try:
        # ── 1. Login count & failures from audit_logs ──
        result = await session.execute(
            text(
                """
                SELECT
                  COUNT(*) as total_logins,
                  SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as failures
                FROM audit_logs
                WHERE user_id = :uid
                  AND created_at >= :since
                  AND action LIKE :action_pattern
                """
            ),
            {"uid": user_id, "since": since_iso, "action_pattern": "%login%"},
        )
        row = result.fetchone()
        if row:
            features["login_count"] = row[0] or 0
            features["login_failures"] = row[1] or 0

        # ── 2. File access from audit_logs ──
        result = await session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM audit_logs
                WHERE user_id = :uid
                  AND created_at >= :since
                  AND (action LIKE :a1 OR action LIKE :a2 OR action LIKE :a3)
                """
            ),
            {"uid": user_id, "since": since_iso, "a1": "%file%", "a2": "%read%", "a3": "%download%"},
        )
        row = result.fetchone()
        if row:
            features["file_access_count"] = row[0] or 0

        # ── 3. Network connections from security_alerts ──
        result = await session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM security_alerts
                WHERE created_at >= :since
                  AND (event_type LIKE :et1 OR event_type LIKE :et2)
                """
            ),
            {"since": since_iso, "et1": "%network%", "et2": "%connection%"},
        )
        row = result.fetchone()
        if row:
            features["network_connections"] = row[0] or 0

        # ── 4. Privilege escalation from security_alerts ──
        result = await session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM security_alerts
                WHERE created_at >= :since
                  AND (
                    event_type LIKE :et1
                    OR event_type LIKE :et2
                    OR title LIKE :t1
                    OR title LIKE :t2
                    OR rule_mitre LIKE :rm1
                    OR rule_mitre LIKE :rm2
                  )
                """
            ),
            {
                "since": since_iso,
                "et1": "%privilege%",
                "et2": "%escalation%",
                "t1": "%sudo%",
                "t2": "%admin%",
                "rm1": "%T1068%",
                "rm2": "%T1078%",
            },
        )
        row = result.fetchone()
        if row:
            features["privilege_escalation"] = row[0] or 0

        # ── 5. Lateral movement from security_alerts ──
        result = await session.execute(
            text(
                """
                SELECT COUNT(*), COUNT(DISTINCT destination_ip)
                FROM security_alerts
                WHERE created_at >= :since
                  AND (
                    event_type LIKE :et1
                    OR event_type LIKE :et2
                    OR rule_mitre LIKE :rm1
                  )
                """
            ),
            {
                "since": since_iso,
                "et1": "%lateral%",
                "et2": "%movement%",
                "rm1": "%TA0008%",
            },
        )
        row = result.fetchone()
        if row:
            features["lateral_movement"] = row[0] or 0
            features["unique_hosts"] = row[1] or 0

    except Exception as e:
        logger.warning(f"Feature extraction partial failure for {user_id}: {e}")

    return features


# ── UEBA Engine ──────────────────────────────────────────────────────────


class UEBAEngine:
    """UEBA detection engine with DB-backed baselines."""

    def __init__(self, session: AsyncSession | None = None):
        self.baselines: dict[str, BehaviorBaseline] = {}
        self.feature_cache: dict[str, dict[str, Any]] = {}
        self.scaler = StandardScaler()
        self.isolation_forest = IsolationForest(
            contamination=0.1,
            random_state=42,
            n_estimators=100,
        )
        self._model_trained = False
        self.session = session

    # ── F3-4: Core feature ──

    async def build_baseline_from_db(
        self,
        user_id: str,
        days_of_history: int = 30,
        session: AsyncSession | None = None,
    ) -> BehaviorBaseline | None:
        """Build behavior baseline from real database data.

        Extracts 6-class behavior features from security_alerts and audit_logs,
        trains an IsolationForest model, and persists both to ueba_baselines.

        Args:
            user_id: User to build baseline for
            days_of_history: Lookback window
            session: Optional DB session (uses self.session if not provided)

        Returns:
            BehaviorBaseline or None if insufficient data
        """
        db = session or self.session
        if db is None:
            logger.error("No database session available for baseline building")
            return None

        logger.info(f"Building DB-backed baseline for user {user_id}")

        # Step 1: Extract features from DB
        features = await _extract_behavior_features_from_db(db, user_id, days_of_history)
        self.feature_cache[user_id] = features

        total_events = (
            features["login_count"]
            + features["file_access_count"]
            + features["network_connections"]
        )
        if total_events < 10:
            logger.warning(
                f"Insufficient data for user {user_id}: {total_events} events (need >=10)"
            )
            return None

        # Step 2: Build baseline object
        baseline = BehaviorBaseline(
            entity_id=user_id,
            entity_type="user",
            login_times=[9, 10, 11, 14, 15, 16],  # default biz hours
            accessed_resources=[],
            peer_group=[],
            typical_data_volume=features.get("data_volume_mb", 100.0),
            typical_connections=features.get("network_connections", 10),
            last_updated=datetime.now(),
        )

        self.baselines[user_id] = baseline

        # Step 3: Train IsolationForest on this user's features
        feature_names = [
            "login_count",
            "login_failures",
            "file_access_count",
            "network_connections",
            "privilege_escalation",
            "lateral_movement",
        ]
        feature_vector = [features.get(f, 0) for f in feature_names]

        # For single-user model, we need multiple samples — create synthetic variations
        synthetic_samples = []
        for delta_factor in [0.5, 0.75, 0.9, 1.0, 1.1, 1.25, 1.5, 2.0]:
            sample = [max(0, int(v * delta_factor)) for v in feature_vector]
            synthetic_samples.append(sample)
        X_train = np.array(synthetic_samples)

        try:
            X_scaled = self.scaler.fit_transform(X_train)
            self.isolation_forest.fit(X_scaled)
            self._model_trained = True
            logger.info(f"IsolationForest trained for {user_id} ({X_train.shape[0]} samples)")
        except Exception as e:
            logger.error(f"ML training failed for {user_id}: {e}")

        # Step 4: Persist to ueba_baselines table
        try:
            await self._persist_baseline(db, user_id, features)
        except Exception as e:
            logger.warning(f"Failed to persist baseline for {user_id}: {e}")

        return baseline

    async def _persist_baseline(
        self,
        session: AsyncSession,
        user_id: str,
        features: dict[str, Any],
    ) -> None:
        """Persist the baseline and model to ueba_baselines table."""
        model_bytes = None
        if self._model_trained:
            try:
                model_bytes = pickle.dumps(self.isolation_forest)
            except Exception as e:
                logger.warning(f"Failed to serialize model: {e}")

        # Use simple insert-or-replace via raw SQL for cross-DB compatibility
        existing = await session.execute(
            text("SELECT id FROM ueba_baselines WHERE user_id = :uid"),
            {"uid": user_id},
        )
        row = existing.fetchone()

        if row:
            await session.execute(
                text(
                    """
                    UPDATE ueba_baselines
                    SET model_data = :md, features_json = :fj,
                        anomaly_threshold = :at, training_samples = :ts,
                        updated_at = :now
                    WHERE user_id = :uid
                    """
                ),
                {
                    "md": model_bytes,
                    "fj": json.dumps(features),
                    "at": 0.8,
                    "ts": 8,
                    "now": datetime.now().isoformat(),
                    "uid": user_id,
                },
            )
        else:
            import uuid

            await session.execute(
                text(
                    """
                    INSERT INTO ueba_baselines (id, user_id, entity_type, model_data,
                        features_json, anomaly_threshold, training_samples, created_at, updated_at)
                    VALUES (:id, :uid, :et, :md, :fj, :at, :ts, :now, :now)
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "uid": user_id,
                    "et": "user",
                    "md": model_bytes,
                    "fj": json.dumps(features),
                    "at": 0.8,
                    "ts": 8,
                    "now": datetime.now().isoformat(),
                },
            )
        await session.commit()
        logger.info(f"Baseline persisted for user {user_id}")

    async def load_baseline_from_db(
        self,
        user_id: str,
        session: AsyncSession | None = None,
    ) -> BehaviorBaseline | None:
        """Load a previously persisted baseline from the database.

        Args:
            user_id: User ID to load
            session: Optional DB session

        Returns:
            BehaviorBaseline or None
        """
        db = session or self.session
        if db is None:
            return None

        try:
            result = await db.execute(
                text(
                    """
                    SELECT model_data, features_json, training_samples
                    FROM ueba_baselines
                    WHERE user_id = :uid
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """
                ),
                {"uid": user_id},
            )
            row = result.fetchone()
            if row is None:
                return None

            model_bytes = row[0]
            features_json = row[1]

            # Restore features
            if features_json:
                features = json.loads(features_json)
                self.feature_cache[user_id] = features

            # Restore model
            if model_bytes:
                try:
                    self.isolation_forest = pickle.loads(model_bytes)
                    self._model_trained = True
                except Exception as e:
                    logger.warning(f"Failed to deserialize model for {user_id}: {e}")

            baseline = BehaviorBaseline(
                entity_id=user_id,
                entity_type="user",
                login_times=[9, 10, 11, 14, 15, 16],
                accessed_resources=[],
                peer_group=[],
                typical_data_volume=features.get("data_volume_mb", 100.0) if features_json else 100.0,
                typical_connections=features.get("network_connections", 10) if features_json else 10,
                last_updated=datetime.now(),
            )
            self.baselines[user_id] = baseline
            return baseline

        except Exception as e:
            logger.error(f"Failed to load baseline for {user_id}: {e}")
            return None

    # ── (legacy) build_baseline kept for compat ──

    async def build_baseline(
        self, entity_id: str, entity_type: str, days_of_history: int = 30
    ) -> BehaviorBaseline:
        """Build behavior baseline. Prefers DB data with fallback to defaults.

        Args:
            entity_id: User ID, host ID, or IP address
            entity_type: Type of entity
            days_of_history: Days of historical data to analyze

        Returns:
            Behavior baseline
        """
        # Try DB-backed baseline first
        if self.session:
            db_baseline = await self.build_baseline_from_db(
                entity_id, days_of_history, self.session
            )
            if db_baseline:
                return db_baseline

        # Fallback to in-memory defaults
        logger.info(
            f"Building baseline for {entity_type} {entity_id} (defaults)"
        )
        baseline = BehaviorBaseline(
            entity_id=entity_id,
            entity_type=entity_type,
            login_times=[9, 10, 11, 14, 15, 16],
            accessed_resources=["file_share", "email", "vpn"],
            peer_group=["user1", "user2", "user3"],
            typical_data_volume=100.0,
            typical_connections=10,
            last_updated=datetime.now(),
        )
        self.baselines[entity_id] = baseline
        return baseline

    async def detect_anomalies(
        self, entity_id: str, current_behavior: dict[str, Any]
    ) -> list[AnomalyDetection]:
        """Detect anomalies in current behavior compared to baseline.

        Uses DB-loaded baseline if available; falls back to in-memory.
        """
        anomalies: list[AnomalyDetection] = []

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
        """Calculate overall risk score based on anomalies."""
        if not recent_anomalies:
            return 0.0, RiskLevel.LOW

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

        risk_score = min(total_score, 100.0)

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
        """Get comprehensive risk profile for a user with real data.

        Uses DB-loaded baseline features when available.
        """
        # Try to load real features
        features = self.feature_cache.get(user_id)

        risk_factors: list[dict[str, Any]] = []
        sample_anomalies: list[AnomalyDetection] = []

        if features:
            # Generate real risk factors based on extracted features
            if features.get("login_failures", 0) > 5:
                risk_factors.append({
                    "type": "authentication",
                    "severity": "medium",
                    "description": f"Elevated login failures: {features['login_failures']}",
                })
                sample_anomalies.append(
                    AnomalyDetection(
                        entity_id=user_id,
                        behavior_type=BehaviorType.LOGIN,
                        anomaly_score=0.65,
                        risk_level=RiskLevel.MEDIUM,
                        description=f"Multiple login failures detected ({features['login_failures']})",
                        indicators=["brute_force_attempt", "credential_stuffing"],
                        recommended_actions=["review_auth_logs", "check_account_lockout"],
                        detected_at=datetime.now(),
                    )
                )

            if features.get("privilege_escalation", 0) > 0:
                risk_factors.append({
                    "type": "privilege",
                    "severity": "high",
                    "description": f"Privilege escalation attempts: {features['privilege_escalation']}",
                })
                sample_anomalies.append(
                    AnomalyDetection(
                        entity_id=user_id,
                        behavior_type=BehaviorType.PRIVILEGE_ESCALATION,
                        anomaly_score=0.85,
                        risk_level=RiskLevel.HIGH,
                        description=f"Privilege escalation detected ({features['privilege_escalation']} attempts)",
                        indicators=["sudo_abuse", "unauthorized_role_change"],
                        recommended_actions=["audit_sudo_logs", "review_rbac_assignments"],
                        detected_at=datetime.now(),
                    )
                )

            if features.get("lateral_movement", 0) > 0:
                risk_factors.append({
                    "type": "lateral_movement",
                    "severity": "high",
                    "description": f"Lateral movement indicators: {features['lateral_movement']}",
                })
                sample_anomalies.append(
                    AnomalyDetection(
                        entity_id=user_id,
                        behavior_type=BehaviorType.LATERAL_MOVEMENT,
                        anomaly_score=0.88,
                        risk_level=RiskLevel.HIGH,
                        description=f"Lateral movement detected ({features['lateral_movement']} events, {features.get('unique_hosts', 0)} hosts)",
                        indicators=["network_scanning", "pivoting"],
                        recommended_actions=["isolate_host", "check_for_malware"],
                        detected_at=datetime.now(),
                    )
                )

        if not sample_anomalies:
            risk_factors = []
            sample_anomalies = []

        risk_score, risk_level = await self.calculate_risk_score(user_id, sample_anomalies)

        # Get username from DB if possible
        username = f"user_{user_id}"
        last_activity = datetime.now()
        if self.session:
            try:
                result = await self.session.execute(
                    text("SELECT username FROM users WHERE id = :uid"),
                    {"uid": user_id},
                )
                row = result.fetchone()
                if row:
                    username = row[0]
            except Exception:
                pass

        return UserRiskProfile(
            user_id=user_id,
            username=username,
            overall_risk_score=risk_score,
            risk_level=risk_level,
            risk_factors=risk_factors,
            anomalous_behaviors=sample_anomalies,
            compromised_probability=(
                0.3 if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] else 0.05
            ),
            last_activity=last_activity,
        )

    async def detect_peer_group_anomalies(
        self, entity_id: str, peer_group: list[str]
    ) -> list[AnomalyDetection]:
        """Detect when entity behaves differently from peer group."""
        return []

    async def train_ml_models(self, historical_data: list[dict[str, Any]]):
        """Train ML models on historical data."""
        if len(historical_data) < 100:
            logger.warning("Insufficient data for ML training")
            return

        try:
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
            self.isolation_forest.fit(X_scaled)
            self._model_trained = True

            logger.info("UEBA ML models trained successfully")

        except Exception as e:
            logger.error(f"Error training ML models: {e}")

    async def predict_with_ml(self, behavior_vector: list[float]) -> tuple[bool, float]:
        """Predict if behavior is anomalous using ML."""
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

    async def build_all_baselines(
        self,
        session: AsyncSession,
        days_of_history: int = 30,
    ) -> dict[str, Any]:
        """Batch-build baselines for all users with sufficient data.

        Args:
            session: Database session
            days_of_history: Lookback window

        Returns:
            Summary dict with counts
        """
        logger.info("Batch-building baselines for all users...")
        try:
            result = await session.execute(
                text("SELECT DISTINCT user_id FROM audit_logs WHERE user_id IS NOT NULL")
            )
            user_ids = [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.error(f"Failed to fetch user IDs: {e}")
            return {"total": 0, "success": 0, "failed": 0, "errors": [str(e)]}

        self.session = session
        success = 0
        failed = 0
        errors: list[str] = []

        for uid in user_ids:
            try:
                baseline = await self.build_baseline_from_db(uid, days_of_history, session)
                if baseline:
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                errors.append(f"{uid}: {e!s}")

        logger.info(f"Batch baseline complete: {success}/{len(user_ids)} success")
        return {
            "total": len(user_ids),
            "success": success,
            "failed": failed,
            "errors": errors[:20],
        }


# ── Global engine ────────────────────────────────────────────────────────

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
