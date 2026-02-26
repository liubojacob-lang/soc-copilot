#!/usr/bin/env python3
"""
Wazuh API Client
Handles communication with Wazuh API for security events, agents, and alerts
"""

import asyncio
import aiohttp
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

logger = logging.getLogger(__name__)


class WazuhAPIError(Exception):
    """Base exception for Wazuh API errors"""
    pass


class WazuhAuthError(WazuhAPIError):
    """Authentication error"""
    pass


class WazuhConnectionError(WazuhAPIError):
    """Connection error"""
    pass


class WazuhClient:
    """
    Async Wazuh API client with JWT authentication and automatic token refresh
    """

    def __init__(
        self,
        api_url: str,
        username: str,
        password: str,
        cert_path: Optional[str] = None,
        verify_ssl: bool = True
    ):
        """
        Initialize Wazuh API client

        Args:
            api_url: Wazuh API base URL (e.g., https://wazuh.example.com:55000)
            username: API username
            password: API password
            cert_path: Path to CA certificate (if using self-signed certs)
            verify_ssl: Whether to verify SSL certificates
        """
        self.api_url = api_url.rstrip('/')
        self.username = username
        self.password = password
        self.cert_path = cert_path
        self.verify_ssl = verify_ssl

        # Token management
        self.jwt_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None

        # Session
        self._session: Optional[aiohttp.ClientSession] = None

        logger.info(f"Wazuh client initialized for {self.api_url}")

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_session()

    async def start_session(self):
        """Create aiohttp session"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                ssl=self.cert_path if self.cert_path else self.verify_ssl,
                limit=100
            )
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                trust_env=True
            )

    async def close_session(self):
        """Close aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
            await asyncio.sleep(0.25)  # Allow connections to close

    def _generate_jwt_token(self) -> str:
        """
        Generate JWT token for Wazuh API authentication

        Returns:
            JWT token string
        """
        payload = {
            'exp': datetime.utcnow() + timedelta(seconds=900),  # 15 minutes
            'username': self.username
        }

        # Wazuh uses a secret key (default is in wazuh-indexer or wazuh-api config)
        # For the API, we can use basic auth to get a token
        token = jwt.encode(payload, self.password, algorithm='HS256')
        return token

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def _ensure_authenticated(self):
        """
        Ensure we have a valid JWT token
        Authenticate with Wazuh API and retrieve JWT token
        """
        # Check if token is still valid (with 5 min buffer)
        if self.jwt_token and self.token_expiry:
            if datetime.utcnow() < self.token_expiry - timedelta(minutes=5):
                return

        await self.start_session()

        # Authenticate using basic auth to get JWT token
        auth_url = f"{self.api_url}/security/user/authenticate?raw=true"

        try:
            auth = aiohttp.BasicAuth(self.username, self.password)
            async with self._session.post(auth_url, auth=auth) as response:
                if response.status == 200:
                    self.jwt_token = await response.text()
                    # Decode token to get expiry
                    try:
                        decoded = jwt.decode(self.jwt_token, options={'verify_signature': False})
                        exp_timestamp = decoded.get('exp')
                        if exp_timestamp:
                            self.token_expiry = datetime.fromtimestamp(exp_timestamp)
                    except Exception as e:
                        logger.warning(f"Could not decode token expiry: {e}")
                        # Default to 12 minutes from now (tokens typically last 15 min)
                        self.token_expiry = datetime.utcnow() + timedelta(minutes=12)

                    logger.info("Successfully authenticated with Wazuh API")
                else:
                    error_text = await response.text()
                    raise WazuhAuthError(
                        f"Authentication failed: HTTP {response.status} - {error_text}"
                    )

        except aiohttp.ClientError as e:
            raise WazuhConnectionError(f"Connection error during authentication: {e}")

    def _get_headers(self) -> Dict[str, str]:
        """
        Get headers for API requests

        Returns:
            Dictionary of headers
        """
        return {
            'Authorization': f'Bearer {self.jwt_token}',
            'Content-Type': 'application/json'
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make API request

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            json_data: Request body (JSON)

        Returns:
            Response data as dictionary
        """
        await self._ensure_authenticated()
        await self.start_session()

        url = f"{self.api_url}{endpoint}"

        try:
            async with self._session.request(
                method,
                url,
                headers=self._get_headers(),
                params=params,
                json=json_data
            ) as response:
                # Handle successful responses
                if response.status == 200:
                    return await response.json()

                # Handle error responses
                error_data = await response.json() if response.content_length else {}
                error_msg = error_data.get('message', 'Unknown error')

                if response.status == 401:
                    # Token might be expired, clear and retry
                    self.jwt_token = None
                    self.token_expiry = None
                    raise WazuhAuthError(f"Authentication failed: {error_msg}")

                elif response.status == 403:
                    raise WazuhAPIError(f"Permission denied: {error_msg}")

                elif response.status == 404:
                    raise WazuhAPIError(f"Not found: {endpoint}")

                elif 400 <= response.status < 500:
                    raise WazuhAPIError(f"Client error {response.status}: {error_msg}")

                else:
                    raise WazuhAPIError(f"Server error {response.status}: {error_msg}")

        except aiohttp.ClientError as e:
            raise WazuhConnectionError(f"Connection error: {e}")
        except asyncio.TimeoutError:
            raise WazuhConnectionError("Request timed out")

    # ========== Agent Management ==========

    async def get_agents(
        self,
        limit: int = 500,
        offset: int = 0,
        status: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of agents

        Args:
            limit: Maximum number of agents to return
            offset: Starting offset
            status: Filter by status (active, disconnected, never_connected)
            search: Search term

        Returns:
            List of agent dictionaries
        """
        params = {'limit': limit, 'offset': offset}
        if status:
            params['status'] = status
        if search:
            params['search'] = search

        response = await self._request('GET', '/agents', params=params)

        # Response format: {'data': {'items': [...], 'totalItems': 123}}
        return response.get('data', {}).get('items', [])

    async def get_agent_info(self, agent_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific agent

        Args:
            agent_id: Agent ID or name

        Returns:
            Agent information dictionary
        """
        response = await self._request('GET', f'/agents/{agent_id}')
        return response.get('data', {})

    async def get_agent_status(self, agent_id: str) -> str:
        """
        Get agent status

        Args:
            agent_id: Agent ID or name

        Returns:
            Agent status (active, disconnected, never_connected)
        """
        response = await self._request('GET', f'/agents/{agent_id}/status')
        return response.get('data', '')

    # ========== Events and Logs ==========

    async def get_events(
        self,
        limit: int = 100,
        offset: int = 0,
        search: Optional[str] = None,
        agent_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get security events/logs

        Args:
            limit: Maximum number of events
            offset: Starting offset
            search: Search query
            agent_id: Filter by agent
            start_time: Start time filter
            end_time: End time filter

        Returns:
            List of event dictionaries
        """
        params = {'limit': limit, 'offset': offset}

        if search:
            params['search'] = search
        if agent_id:
            params['agents_list'] = agent_id

        # Add time filters (Wazuh uses Unix timestamps)
        if start_time:
            params['date_start'] = str(int(start_time.timestamp()))
        if end_time:
            params['date_end'] = str(int(end_time.timestamp()))

        response = await self._request('GET', '/events', params=params)
        return response.get('data', {}).get('items', [])

    async def get_events_summary(self) -> Dict[str, Any]:
        """
        Get events summary statistics

        Returns:
            Events summary dictionary
        """
        response = await self._request('GET', '/events/summary')
        return response.get('data', {})

    # ========== Alerts ==========

    async def get_alerts(
        self,
        limit: int = 100,
        offset: int = 0,
        agent_id: Optional[str] = None,
        level: Optional[int] = None,
        rule_group: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get security alerts

        Args:
            limit: Maximum number of alerts
            offset: Starting offset
            agent_id: Filter by agent
            level: Filter by rule level (0-15)
            rule_group: Filter by rule group
            start_time: Start time filter
            end_time: End time filter

        Returns:
            List of alert dictionaries
        """
        params = {'limit': limit, 'offset': offset}

        if agent_id:
            params['agents_list'] = agent_id
        if level is not None:
            params['alert_level'] = level
        if rule_group:
            params['rule_groups'] = rule_group
        if start_time:
            params['date_start'] = str(int(start_time.timestamp()))
        if end_time:
            params['date_end'] = str(int(end_time.timestamp()))

        response = await self._request('GET', '/alerts/alerts', params=params)
        return response.get('data', {}).get('items', [])

    async def get_alerts_summary(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get alerts summary statistics

        Args:
            start_time: Start time filter
            end_time: End time filter

        Returns:
            Alerts summary dictionary
        """
        params = {}
        if start_time:
            params['date_start'] = str(int(start_time.timestamp()))
        if end_time:
            params['date_end'] = str(int(end_time.timestamp()))

        response = await self._request('GET', '/alerts/summary', params=params)
        return response.get('data', {})

    # ========== MITRE ATT&CK ==========

    async def get_mitre_attack_events(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get MITRE ATT&CK related events

        Args:
            limit: Maximum number of events
            offset: Starting offset

        Returns:
            List of MITRE ATT&CK event dictionaries
        """
        # Search for events with MITRE technique fields
        search_query = 'mitre.*'
        params = {
            'limit': limit,
            'offset': offset,
            'search': search_query
        }

        response = await self._request('GET', '/events', params=params)
        return response.get('data', {}).get('items', [])

    # ========== Syscheck ==========

    async def get_syscheck_changes(
        self,
        agent_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get file integrity monitoring changes

        Args:
            agent_id: Agent ID or name
            limit: Maximum number of changes
            offset: Starting offset

        Returns:
            List of syscheck change dictionaries
        """
        params = {'limit': limit, 'offset': offset}
        response = await self._request(
            'GET',
            f'/syscheck/{agent_id}',
            params=params
        )
        return response.get('data', {}).get('items', [])

    # ========== Health Check ==========

    async def health_check(self) -> bool:
        """
        Check if Wazuh API is accessible

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self._request('GET', '/')
            return 'data' in response
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False


# Singleton instance
_wazuh_client: Optional[WazuhClient] = None


def get_wazuh_client() -> Optional[WazuhClient]:
    """
    Get Wazuh client singleton instance

    Returns:
        WazuhClient instance or None if not configured
    """
    global _wazuh_client
    return _wazuh_client


def init_wazuh_client(
    api_url: str,
    username: str,
    password: str,
    cert_path: Optional[str] = None,
    verify_ssl: bool = True
) -> WazuhClient:
    """
    Initialize Wazuh client singleton

    Args:
        api_url: Wazuh API URL
        username: API username
        password: API password
        cert_path: Path to CA certificate
        verify_ssl: Whether to verify SSL

    Returns:
        WazuhClient instance
    """
    global _wazuh_client
    _wazuh_client = WazuhClient(
        api_url=api_url,
        username=username,
        password=password,
        cert_path=cert_path,
        verify_ssl=verify_ssl
    )
    return _wazuh_client
