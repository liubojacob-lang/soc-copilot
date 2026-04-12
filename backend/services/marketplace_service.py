"""
Playbook Marketplace Service
Community-driven playbook sharing platform
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class PlaybookCategory(Enum):
    """Playbook categories."""

    MALWARE_RESPONSE = "malware_response"
    PHISHING = "phishing"
    DATA_BREACH = "data_breach"
    RANSOMWARE = "ransomware"
    NETWORK_INTRUSION = "network_intrusion"
    INSIDER_THREAT = "insider_threat"
    COMPLIANCE = "compliance"
    CUSTOM = "custom"


class PlaybookDifficulty(Enum):
    """Playbook difficulty levels."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


@dataclass
class PlaybookReview:
    """Playbook review/rating."""

    id: str
    playbook_id: str
    user_id: str
    username: str
    rating: int  # 1-5
    comment: str
    created_at: datetime


@dataclass
class MarketplacePlaybook:
    """Playbook in marketplace."""

    id: str
    name: str
    description: str
    version: str
    category: PlaybookCategory
    difficulty: PlaybookDifficulty
    author: str
    author_id: str
    tags: list[str]

    # Stats
    download_count: int
    rating_average: float
    rating_count: int
    review_count: int

    # Content
    dag_json: dict[str, Any]
    documentation: str

    # Metadata
    created_at: datetime
    updated_at: datetime
    verified: bool
    featured: bool

    # Requirements
    required_plugins: list[str]
    compatible_versions: list[str]


class PlaybookMarketplace:
    """Playbook marketplace engine."""

    def __init__(self):
        self.playbooks: dict[str, MarketplacePlaybook] = {}
        self.reviews: dict[str, list[PlaybookReview]] = {}
        self._initialize_sample_playbooks()

    def _initialize_sample_playbooks(self):
        """Initialize with sample playbooks."""
        sample_playbooks = [
            MarketplacePlaybook(
                id="market_001",
                name="Phishing Email Response",
                description="Complete playbook for handling phishing email incidents including user notification, IOC extraction, and blocking.",
                version="1.2.0",
                category=PlaybookCategory.PHISHING,
                difficulty=PlaybookDifficulty.BEGINNER,
                author="SOC Team",
                author_id="admin",
                tags=["phishing", "email", "ioc", "blocking"],
                download_count=1250,
                rating_average=4.5,
                rating_count=45,
                review_count=12,
                dag_json={
                    "nodes": [
                        {"id": "start", "type": "start", "name": "Start"},
                        {
                            "id": "extract_iocs",
                            "type": "extract_iocs",
                            "name": "Extract IOCs",
                        },
                        {
                            "id": "ti_lookup",
                            "type": "ti_lookup_otx",
                            "name": "Threat Intel Lookup",
                        },
                        {
                            "id": "block_iocs",
                            "type": "block_iocs",
                            "name": "Block IOCs",
                        },
                        {
                            "id": "notify_user",
                            "type": "slack_notify",
                            "name": "Notify User",
                        },
                        {"id": "end", "type": "end", "name": "End"},
                    ],
                    "edges": [
                        {"source": "start", "target": "extract_iocs"},
                        {"source": "extract_iocs", "target": "ti_lookup"},
                        {"source": "ti_lookup", "target": "block_iocs"},
                        {"source": "block_iocs", "target": "notify_user"},
                        {"source": "notify_user", "target": "end"},
                    ],
                },
                documentation="""# Phishing Email Response Playbook

## Overview
This playbook automates the response to phishing email incidents.

## Steps
1. Extract IOCs from email (URLs, IPs, attachments)
2. Query threat intelligence sources
3. Block malicious IOCs
4. Notify affected user
5. Create incident report

## Requirements
- OTX API key
- Slack webhook
- Network blocking capabilities
""",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                verified=True,
                featured=True,
                required_plugins=["extract_iocs", "ti_lookup_otx", "slack_notify"],
                compatible_versions=["0.7.0", "0.7.1", "0.7.2"],
            ),
            MarketplacePlaybook(
                id="market_002",
                name="Ransomware Emergency Response",
                description="Emergency response playbook for ransomware incidents with immediate containment actions.",
                version="2.0.0",
                category=PlaybookCategory.RANSOMWARE,
                difficulty=PlaybookDifficulty.ADVANCED,
                author="Security Expert",
                author_id="user_002",
                tags=["ransomware", "emergency", "containment", "forensics"],
                download_count=890,
                rating_average=4.8,
                rating_count=32,
                review_count=8,
                dag_json={
                    "nodes": [
                        {"id": "start", "type": "start", "name": "Start"},
                        {
                            "id": "isolate_host",
                            "type": "isolate_host",
                            "name": "Isolate Host",
                        },
                        {
                            "id": "disable_account",
                            "type": "disable_account",
                            "name": "Disable Account",
                        },
                        {
                            "id": "snapshot_forensics",
                            "type": "create_snapshot",
                            "name": "Create Snapshot",
                        },
                        {
                            "id": "collect_evidence",
                            "type": "collect_logs",
                            "name": "Collect Evidence",
                        },
                        {
                            "id": "analyze_artifacts",
                            "type": "analyze_malware",
                            "name": "Analyze Malware",
                        },
                        {
                            "id": "notify_stakeholders",
                            "type": "slack_notify",
                            "name": "Notify Stakeholders",
                        },
                        {
                            "id": "create_ticket",
                            "type": "create_ticket",
                            "name": "Create Ticket",
                        },
                        {"id": "end", "type": "end", "name": "End"},
                    ],
                    "edges": [
                        {"source": "start", "target": "isolate_host"},
                        {"source": "isolate_host", "target": "disable_account"},
                        {"source": "disable_account", "target": "snapshot_forensics"},
                        {"source": "snapshot_forensics", "target": "collect_evidence"},
                        {"source": "collect_evidence", "target": "analyze_artifacts"},
                        {
                            "source": "analyze_artifacts",
                            "target": "notify_stakeholders",
                        },
                        {"source": "notify_stakeholders", "target": "create_ticket"},
                        {"source": "create_ticket", "target": "end"},
                    ],
                },
                documentation="""# Ransomware Emergency Response

## Overview
Emergency response playbook for active ransomware incidents.

## Immediate Actions
1. Isolate affected host from network
2. Disable compromised user account
3. Create forensic snapshot
4. Collect evidence (logs, memory dump)
5. Analyze malware sample

## Communication
- Notify security team
- Alert management
- Create incident ticket

## Post-Incident
- Restore from backup
- Patch vulnerabilities
- Update detection rules
""",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                verified=True,
                featured=True,
                required_plugins=["isolate_host", "disable_account", "slack_notify"],
                compatible_versions=["0.7.0", "0.7.1", "0.7.2"],
            ),
            MarketplacePlaybook(
                id="market_003",
                name="Data Exfiltration Investigation",
                description="Investigate potential data exfiltration with comprehensive analysis workflow.",
                version="1.0.0",
                category=PlaybookCategory.DATA_BREACH,
                difficulty=PlaybookDifficulty.INTERMEDIATE,
                author="Data Protection Team",
                author_id="user_003",
                tags=["data_exfiltration", "dlp", "investigation", "forensics"],
                download_count=567,
                rating_average=4.3,
                rating_count=23,
                review_count=5,
                dag_json={
                    "nodes": [
                        {"id": "start", "type": "start", "name": "Start"},
                        {
                            "id": "analyze_logs",
                            "type": "analyze_logs",
                            "name": "Analyze Proxy Logs",
                        },
                        {
                            "id": "check_dlp",
                            "type": "check_dlp_alerts",
                            "name": "Check DLP Alerts",
                        },
                        {
                            "id": "identify_files",
                            "type": "identify_files",
                            "name": "Identify Accessed Files",
                        },
                        {
                            "id": "assess_impact",
                            "type": "assess_impact",
                            "name": "Assess Data Impact",
                        },
                        {
                            "id": "generate_report",
                            "type": "generate_report",
                            "name": "Generate Report",
                        },
                        {"id": "end", "type": "end", "name": "End"},
                    ],
                    "edges": [
                        {"source": "start", "target": "analyze_logs"},
                        {"source": "analyze_logs", "target": "check_dlp"},
                        {"source": "check_dlp", "target": "identify_files"},
                        {"source": "identify_files", "target": "assess_impact"},
                        {"source": "assess_impact", "target": "generate_report"},
                        {"source": "generate_report", "target": "end"},
                    ],
                },
                documentation="Investigation playbook for data exfiltration incidents.",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                verified=False,
                featured=False,
                required_plugins=["analyze_logs", "check_dlp"],
                compatible_versions=["0.7.0", "0.7.1", "0.7.2"],
            ),
            MarketplacePlaybook(
                id="market_004",
                name="Malware Analysis & Quarantine",
                description="Automated malware analysis with sandboxing and network quarantine.",
                version="1.5.0",
                category=PlaybookCategory.MALWARE_RESPONSE,
                difficulty=PlaybookDifficulty.INTERMEDIATE,
                author="Malware Research Team",
                author_id="user_004",
                tags=["malware", "sandbox", "quarantine", "analysis"],
                download_count=2100,
                rating_average=4.7,
                rating_count=89,
                review_count=25,
                dag_json={},
                documentation="Malware analysis playbook with automated sandboxing.",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                verified=True,
                featured=True,
                required_plugins=["malware_scan", "sandbox", "quarantine"],
                compatible_versions=["0.7.0", "0.7.1", "0.7.2"],
            ),
            MarketplacePlaybook(
                id="market_005",
                name="Insider Threat Investigation",
                description="Investigate potential insider threats with UEBA correlation and data access analysis.",
                version="1.0.0",
                category=PlaybookCategory.INSIDER_THREAT,
                difficulty=PlaybookDifficulty.ADVANCED,
                author="Insider Threat Team",
                author_id="user_005",
                tags=["insider_threat", "ueba", "data_access", "investigation"],
                download_count=432,
                rating_average=4.4,
                rating_count=18,
                review_count=4,
                dag_json={},
                documentation="Insider threat investigation with UEBA integration.",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                verified=False,
                featured=False,
                required_plugins=["ueba_analyze", "data_access_log"],
                compatible_versions=["0.7.0", "0.7.1", "0.7.2"],
            ),
            MarketplacePlaybook(
                id="market_006",
                name="GDPR Data Breach Response",
                description="Compliance playbook for GDPR data breach notification and response.",
                version="1.0.0",
                category=PlaybookCategory.COMPLIANCE,
                difficulty=PlaybookDifficulty.INTERMEDIATE,
                author="Compliance Team",
                author_id="user_006",
                tags=["gdpr", "compliance", "data_breach", "notification"],
                download_count=756,
                rating_average=4.6,
                rating_count=28,
                review_count=7,
                dag_json={},
                documentation="GDPR compliance playbook for data breach response.",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                verified=True,
                featured=False,
                required_plugins=["gdpr_check", "notification"],
                compatible_versions=["0.7.0", "0.7.1", "0.7.2"],
            ),
        ]

        for playbook in sample_playbooks:
            self.playbooks[playbook.id] = playbook
            self.reviews[playbook.id] = []

        logger.info(f"Initialized marketplace with {len(sample_playbooks)} playbooks")

    async def search_playbooks(
        self,
        query: str | None = None,
        category: PlaybookCategory | None = None,
        difficulty: PlaybookDifficulty | None = None,
        tags: list[str] | None = None,
        min_rating: float | None = None,
        verified_only: bool = False,
        sort_by: str = "rating",  # rating, downloads, newest
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[MarketplacePlaybook], int]:
        """
        Search playbooks in marketplace.

        Args:
            query: Text search query
            category: Filter by category
            difficulty: Filter by difficulty
            tags: Filter by tags
            min_rating: Minimum rating filter
            verified_only: Only verified playbooks
            sort_by: Sort field
            page: Page number
            page_size: Items per page

        Returns:
            (playbooks, total_count)
        """
        results = list(self.playbooks.values())

        # Apply filters
        if query:
            query_lower = query.lower()
            results = [
                p
                for p in results
                if query_lower in p.name.lower()
                or query_lower in p.description.lower()
                or any(query_lower in tag.lower() for tag in p.tags)
            ]

        if category:
            results = [p for p in results if p.category == category]

        if difficulty:
            results = [p for p in results if p.difficulty == difficulty]

        if tags:
            results = [p for p in results if any(tag in p.tags for tag in tags)]

        if min_rating:
            results = [p for p in results if p.rating_average >= min_rating]

        if verified_only:
            results = [p for p in results if p.verified]

        # Sort
        if sort_by == "rating":
            results.sort(
                key=lambda p: (p.rating_average, p.download_count), reverse=True
            )
        elif sort_by == "downloads":
            results.sort(key=lambda p: p.download_count, reverse=True)
        elif sort_by == "newest":
            results.sort(key=lambda p: p.created_at, reverse=True)

        # Paginate
        total = len(results)
        start = (page - 1) * page_size
        end = start + page_size

        return results[start:end], total

    async def get_playbook(self, playbook_id: str) -> MarketplacePlaybook | None:
        """Get playbook by ID."""
        return self.playbooks.get(playbook_id)

    async def download_playbook(
        self, playbook_id: str, user_id: str
    ) -> dict[str, Any] | None:
        """
        Download playbook for local use.

        Args:
            playbook_id: Marketplace playbook ID
            user_id: User downloading

        Returns:
            Playbook definition for import
        """
        playbook = self.playbooks.get(playbook_id)
        if not playbook:
            return None

        # Increment download count
        playbook.download_count += 1

        return {
            "name": f"[Marketplace] {playbook.name}",
            "version": playbook.version,
            "description": playbook.description,
            "dag": playbook.dag_json,
            "metadata": {
                "source": "marketplace",
                "marketplace_id": playbook.id,
                "author": playbook.author,
                "downloaded_at": datetime.now().isoformat(),
                "documentation": playbook.documentation,
            },
        }

    async def submit_review(
        self, playbook_id: str, user_id: str, username: str, rating: int, comment: str
    ) -> bool:
        """
        Submit a review for a playbook.

        Args:
            playbook_id: Playbook ID
            user_id: Reviewer user ID
            username: Reviewer username
            rating: Rating 1-5
            comment: Review comment

        Returns:
            Success status
        """
        if playbook_id not in self.playbooks:
            return False

        if not 1 <= rating <= 5:
            return False

        review = PlaybookReview(
            id=f"review_{len(self.reviews.get(playbook_id, [])) + 1}",
            playbook_id=playbook_id,
            user_id=user_id,
            username=username,
            rating=rating,
            comment=comment,
            created_at=datetime.now(),
        )

        if playbook_id not in self.reviews:
            self.reviews[playbook_id] = []

        self.reviews[playbook_id].append(review)

        # Update playbook stats
        playbook = self.playbooks[playbook_id]
        reviews = self.reviews[playbook_id]
        playbook.rating_count = len(reviews)
        playbook.review_count = len([r for r in reviews if r.comment])
        playbook.rating_average = sum(r.rating for r in reviews) / len(reviews)

        logger.info(f"Review submitted for {playbook_id}: {rating} stars")
        return True

    async def get_playbook_reviews(
        self, playbook_id: str, page: int = 1, page_size: int = 10
    ) -> list[PlaybookReview]:
        """Get reviews for a playbook."""
        reviews = self.reviews.get(playbook_id, [])
        start = (page - 1) * page_size
        end = start + page_size
        return reviews[start:end]

    async def get_categories(self) -> list[dict[str, Any]]:
        """Get playbook categories with counts."""
        categories = {}
        for playbook in self.playbooks.values():
            cat = playbook.category.value
            if cat not in categories:
                categories[cat] = {"count": 0, "name": cat.replace("_", " ").title()}
            categories[cat]["count"] += 1

        return [
            {"id": k, "name": v["name"], "count": v["count"]}
            for k, v in sorted(categories.items())
        ]

    async def get_featured_playbooks(self, limit: int = 5) -> list[MarketplacePlaybook]:
        """Get featured playbooks."""
        featured = [p for p in self.playbooks.values() if p.featured]
        featured.sort(key=lambda p: p.rating_average, reverse=True)
        return featured[:limit]

    async def get_trending_playbooks(self, limit: int = 5) -> list[MarketplacePlaybook]:
        """Get trending playbooks (most downloads in last 30 days)."""
        # In production, calculate based on recent downloads
        # For now, sort by total downloads
        trending = sorted(
            self.playbooks.values(), key=lambda p: p.download_count, reverse=True
        )
        return trending[:limit]


# Global marketplace instance
_marketplace: PlaybookMarketplace | None = None


def get_marketplace() -> PlaybookMarketplace:
    """Get or create global marketplace instance."""
    global _marketplace
    if _marketplace is None:
        _marketplace = PlaybookMarketplace()
    return _marketplace


async def initialize_marketplace():
    """Initialize marketplace on application startup."""
    global _marketplace
    _marketplace = PlaybookMarketplace()
    logger.info("Playbook marketplace initialized")


async def close_marketplace():
    """Cleanup marketplace on application shutdown."""
    global _marketplace
    if _marketplace:
        logger.info("Playbook marketplace closed")
        _marketplace = None
