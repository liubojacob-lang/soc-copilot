"""
Enhanced AI Service for SOC Copilot - Phase 2
Adds RAG (Retrieval Augmented Generation) and advanced AI capabilities
"""

import asyncio
import json
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from core.config import settings
from core.logger import get_logger
from core.prompt_sanitizer import (
    sanitize_alert_data,
    sanitize_json_for_prompt,
    sanitize_prompt_input,
)
from services.ai_providers import LLMFactory, LLMProvider, stream_chat_completion
from services.ai_utils import clean_json_content
from utils.circuit_breaker import CircuitBreaker

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class AIAnalysisResult(BaseModel):
    """Result of AI analysis."""

    summary: str
    root_cause: str
    recommendations: list[str]
    confidence: float
    severity_assessment: str | None = None
    attack_techniques: list[str] | None = None


class NaturalLanguageQueryResult(BaseModel):
    """Natural language query result."""

    intent: str
    parameters: dict[str, Any]
    filter_criteria: dict[str, Any]
    response: str
    sql_query: str | None = None


class PlaybookRecommendation(BaseModel):
    """Playbook recommendation."""

    playbook_id: str
    playbook_name: str
    confidence: float
    reason: str
    estimated_time: str | None = None


class EnhancedAIService:
    """Enhanced AI service with RAG capabilities."""

    def __init__(self):
        self.max_retries = getattr(settings, "max_retries", 3)
        self.provider = getattr(settings, "ai_provider", "zhipu").lower()
        self.llm: LLMProvider | None = None
        self._initialized = False
        self.circuit_breaker = CircuitBreaker(
            name="llm_provider",
            failure_threshold=5,
            recovery_timeout=30.0,
        )

        # Initialize LLM provider
        self._init_llm()

    def _init_llm(self):
        """Initialize LLM provider."""
        try:
            self.llm = LLMFactory.create_from_config()
            if self.llm:
                self._initialized = True
                logger.info(f"Enhanced AI service initialized with {self.provider}")
            else:
                logger.warning("No LLM provider available")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")

    def get_model_name(self) -> str:
        """Return the model identifier currently in use.

        Falls back to the configured provider name when no concrete provider
        is initialized (e.g. degraded mode / missing API key). This keeps
        downstream consumers (LLMRetryService, audit metadata) working even
        when the LLM itself is unavailable.
        """
        if self.llm is not None and getattr(self.llm, "model", None):
            return self.llm.model
        return getattr(settings, "ai_provider", "unknown")

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "You are a cybersecurity expert assistant.",
        temperature: float = 0.7,
    ) -> str:
        """Generate a plain-text completion for the given prompt.

        Unlike ``generate_structured`` (which enforces a JSON schema), this is
        the escape hatch for task types that produce free-form text
        (e.g. CHAT_COMPLETION, REPORT_GENERATION). Returns the raw model
        output as a string.
        """
        if not self.llm:
            raise ValueError("AI service not initialized")

        content = await self.circuit_breaker.call(
            self.llm.chat_completion,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )
        return content

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        system_prompt: str = "You are a cybersecurity expert assistant.",
    ) -> T:
        """Generate structured response using AI."""
        if not self.llm:
            raise ValueError("AI service not initialized")

        schema = response_model.model_json_schema()

        full_prompt = f"""You must respond with valid JSON only. No markdown, no explanations.

JSON Schema:
{json.dumps(schema, indent=2, ensure_ascii=False)}

User Input:
{prompt}

Respond with JSON that matches the schema above:"""

        content = None
        for attempt in range(self.max_retries + 1):
            try:
                content = await self.circuit_breaker.call(
                    self.llm.chat_completion,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": full_prompt},
                    ],
                    temperature=0.1,
                )

                # Clean and parse the content
                content = clean_json_content(content)
                data = json.loads(content)

                # Type coercion for integer fields
                if "properties" in schema:
                    for field_name, field_def in schema["properties"].items():
                        if field_name in data and isinstance(field_def, dict):
                            field_type = field_def.get("type")
                            # Handle anyOf (optional fields) - get the first non-null type
                            if field_type is None and "anyOf" in field_def:
                                for anyof_item in field_def["anyOf"]:
                                    if anyof_item.get("type") != "null":
                                        field_type = anyof_item.get("type")
                                        break

                            if field_type == "integer" and isinstance(
                                data[field_name], float
                            ):
                                data[field_name] = int(data[field_name])
                            elif field_type == "array" and not isinstance(
                                data[field_name], list
                            ):
                                data[field_name] = []

                return response_model(**data)

            except (ValidationError, json.JSONDecodeError) as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e!s}")
                if attempt == self.max_retries:
                    error_msg = f"Failed to parse content: {content[:500] if content else 'empty'}..."
                    logger.error(error_msg)
                    raise ValueError(
                        f"Failed to get valid JSON after {self.max_retries + 1} attempts"
                    )
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"AI service error: {e!s}")
                raise

        raise RuntimeError("Unexpected end of generate_structured")

    async def analyze_alert(self, alert_data: dict[str, Any]) -> AIAnalysisResult:
        """
        Analyze an alert with the configured LLM, falling back to heuristics.

        Args:
            alert_data: Alert information

        Returns:
            AI analysis result
        """
        if not self.llm:
            raise ValueError("AI service not available")

        try:
            # Sanitize alert data to prevent prompt injection
            safe_alert = sanitize_alert_data(alert_data)

            # Build base prompt
            alert_summary = f"""
Alert: {safe_alert.get("title", "N/A")}
Description: {safe_alert.get("description", "N/A")}
Severity: {safe_alert.get("severity", "unknown")}
Source: {safe_alert.get("source", "N/A")}
Type: {safe_alert.get("alert_type", "N/A")}
"""

            system_prompt = """You are an expert SOC analyst. Analyze this security alert and provide:
1. Concise summary
2. Root cause analysis
3. Specific, actionable recommendations
4. Confidence level (0.0-1.0)
5. Severity assessment (if different from provided)
6. MITRE ATT&CK techniques (if applicable)"""

            user_prompt = f"""{alert_summary}

Respond in JSON format with these fields:
- summary (string)
- root_cause (string)
- recommendations (array of strings)
- confidence (float)
- severity_assessment (string, optional)
- attack_techniques (array of strings, optional)"""

            return await self.generate_structured(
                prompt=user_prompt,
                response_model=AIAnalysisResult,
                system_prompt=system_prompt,
            )

        except Exception as e:
            logger.warning(
                f"LLM analysis unavailable or circuit open ({e}), activating rule-based fallback"
            )
            return self._rule_based_fallback_analysis(alert_data, reason=str(e))

    def _rule_based_fallback_analysis(
        self, alert_data: dict[str, Any], reason: str = ""
    ) -> AIAnalysisResult:
        """Rule-based heuristic fallback analysis when LLM service is unavailable or circuit is open."""
        title = alert_data.get("title", "Security Alert")
        description = alert_data.get("description", "")
        severity = alert_data.get("severity", "medium").lower()
        src_ip = alert_data.get("source_ip") or "unknown"
        alert_type = alert_data.get("alert_type") or "unknown"

        recommendations = [
            f"Inspect network traffic and connections associated with source {src_ip}.",
            "Check endpoint detection and response (EDR) telemetry for process anomalies.",
            "Re-trigger AI deep analysis once LLM upstream service recovers.",
        ]
        techniques = []
        low_context = f"{title} {description}".lower()
        if "scan" in low_context or "recon" in low_context:
            techniques.append("T1046 - Network Service Discovery")
        if "brute" in low_context or "login" in low_context or "auth" in low_context:
            techniques.append("T1110 - Brute Force")
        if (
            "malware" in low_context
            or "trojan" in low_context
            or "virus" in low_context
        ):
            techniques.append("T1204 - User Execution")
        if "privilege" in low_context or "escalat" in low_context:
            techniques.append("T1068 - Exploitation for Privilege Escalation")

        return AIAnalysisResult(
            summary=f"[Degraded Mode] Analyzed '{title}' using heuristic rules. External AI engine is currently degraded.",
            root_cause=f"Heuristic signature evaluation for {alert_type}: {reason or 'LLM service fast-fail/circuit open'}.",
            recommendations=recommendations,
            confidence=0.6,
            severity_assessment=severity,
            attack_techniques=techniques,
        )

    async def natural_language_query(
        self, query: str, user_context: dict[str, Any] | None = None
    ) -> NaturalLanguageQueryResult:
        """
        Process natural language query and convert to structured intent.

        Examples:
        - "Show me high severity alerts from yesterday"
        - "What's the status of playbook run XYZ?"
        - "Analyze IP 192.168.1.100"
        """
        if not self.llm:
            raise ValueError("AI service not available")

        try:
            system_prompt = """You are SOC Copilot's query parser. Convert natural language to structured intent.

Supported intents:
- list_alerts: List/filter alerts
- get_alert: Get specific alert
- list_playbooks: List playbooks
- get_playbook: Get playbook details
- run_playbook: Execute a playbook
- list_playbook_runs: List playbook execution history
- get_playbook_run: Get playbook run status
- analyze_entity: Analyze IP, domain, hash, etc.
- create_playbook: Create a new playbook
- get_statistics: Get SOC metrics
- help: General help

Parse the query and extract:
1. Intent
2. Parameters (time ranges, filters, entities)
3. Filter criteria for database queries
4. Natural language acknowledgment"""

            user_prompt = f"Query: {sanitize_prompt_input(query)}"
            if user_context:
                user_prompt += f"\nUser: {user_context.get('username', 'unknown')}"
                user_prompt += f"\nRole: {user_context.get('role', 'unknown')}"

            result = await self.generate_structured(
                prompt=user_prompt,
                response_model=NaturalLanguageQueryResult,
                system_prompt=system_prompt,
            )

            logger.info(f"Natural language query result: intent={result.intent}")
            return result

        except Exception as e:
            logger.error(f"Error processing natural language query: {e}")
            return NaturalLanguageQueryResult(
                intent="unknown",
                parameters={},
                filter_criteria={},
                response=f"I'm sorry, I couldn't understand your query: {e!s}",
            )

    async def recommend_playbooks(
        self, alert_data: dict[str, Any], available_playbooks: list[dict[str, Any]]
    ) -> list[PlaybookRecommendation]:
        """
        Recommend playbooks based on alert characteristics.

        Args:
            alert_data: Alert information
            available_playbooks: List of available playbooks

        Returns:
            Ranked list of recommendations
        """
        if not self.llm or not available_playbooks:
            return []

        try:
            system_prompt = """You are a playbook recommendation engine. Given an alert and available playbooks,
recommend the most suitable ones. Consider alert type, severity, and playbook capabilities.

Respond with an array of recommendations, each with:
- playbook_id (string)
- playbook_name (string)
- confidence (float, 0-1)
- reason (string)
- estimated_time (string, optional, e.g., "5 minutes")"""

            user_prompt = f"""Alert:
{sanitize_json_for_prompt(alert_data)}

Available Playbooks ({len(available_playbooks)}):
{sanitize_json_for_prompt(available_playbooks[:10])}

Provide your recommendations:"""

            response = await self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )

            # Parse response
            content = clean_json_content(response)
            data = json.loads(content)

            if isinstance(data, list):
                return [PlaybookRecommendation(**item) for item in data]
            elif isinstance(data, dict) and "recommendations" in data:
                return [
                    PlaybookRecommendation(**item) for item in data["recommendations"]
                ]
            else:
                return []

        except Exception as e:
            logger.error(f"Error recommending playbooks: {e}")
            return []

    def resolve_auto_model(
        self,
        message: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> tuple[str, str, str]:
        """
        Intelligently determine the best model & provider based on user prompt & configured keys.

        Returns:
            tuple of (model_id, provider, reason)
        """
        from core.config import settings

        def is_valid_key(val: str) -> bool:
            if not val or not isinstance(val, str):
                return False
            v = val.strip().lower()
            return bool(
                v
                and not v.startswith("your-")
                and not v.startswith("sk-placeholder")
                and "example" not in v
                and len(v) > 8
            )

        nvidia_key = is_valid_key(getattr(settings, "nvidia_api_key", ""))
        zhipu_key = is_valid_key(getattr(settings, "zhipu_api_key", ""))
        anthropic_key = is_valid_key(getattr(settings, "anthropic_api_key", ""))
        openai_key = is_valid_key(getattr(settings, "openai_api_key", ""))

        msg_lower = (message or "").lower()
        msg_len = len(message or "")

        # 1. 深度安全推演 / APT / 溯源 / 复杂攻防 / 根因研判 / 报告编制
        deep_reasoning_keywords = [
            "apt",
            "攻击链",
            "溯源",
            "推演",
            "根因",
            "rca",
            "应急响应",
            "处置报告",
            "取证",
            "playbook",
            "剧本设计",
            "深入分析",
            "att&ck",
            "mitre",
            "横向移动",
            "提权",
            "勒索",
            "挖矿",
            "cve-",
        ]
        is_deep_reasoning = any(k in msg_lower for k in deep_reasoning_keywords)

        # 2. 长文本日志 / 代码审查 / SQL注入 / 脚本反混淆 / 大报文
        code_log_keywords = [
            "```",
            "select ",
            "union select",
            "eval",
            "powershell",
            "base64",
            "syslog",
            "traceback",
            "stack trace",
            "exception:",
            "error:",
            "audit_log",
            "pcap",
            "payload",
            "cmd.exe",
            "bash -c",
        ]
        is_code_or_log = (msg_len > 1000) or any(
            k in msg_lower for k in code_log_keywords
        )

        # 决策路由
        if is_code_or_log:
            if zhipu_key:
                return (
                    "glm-4.7-flash",
                    "zhipu",
                    "长文本/代码日志场景：路由至 200K 超长上下文与 MoE 代码增强模型 (GLM-4.7-Flash)",
                )
            elif nvidia_key:
                return (
                    "meta/llama-3.2-11b-vision-instruct",
                    "nvidia",
                    "长文本/日志分析场景：路由至 Llama 3.2 11B Vision",
                )

        if is_deep_reasoning:
            if anthropic_key:
                return (
                    "claude-3-5-sonnet-20241022",
                    "anthropic",
                    "高危研判与深度推演：路由至顶级安全推理模型 Claude 3.5 Sonnet",
                )
            elif nvidia_key:
                return (
                    "nvidia/nemotron-3.5-lightning-30b-a3b",
                    "nvidia",
                    "高危研判与深度推演：路由至 NVIDIA 官方思维链推理模型 (Nemotron 3.5 Lightning)",
                )
            elif zhipu_key:
                return (
                    "glm-4-plus",
                    "zhipu",
                    "高危研判与深度推演：路由至智谱 GLM-4 Plus 旗舰模型",
                )

        # 3. 日常交互 / 快速查 IP / 端口 / 常规问答
        if nvidia_key:
            return (
                "meta/llama-3.2-11b-vision-instruct",
                "nvidia",
                "日常研判与实时交互：路由至毫秒级响应模型 (Llama 3.2 11B Vision)",
            )
        elif zhipu_key:
            return (
                "glm-4.7-flash",
                "zhipu",
                "日常研判与快速问答：路由至智谱高速模型 (GLM-4.7-Flash)",
            )
        elif openai_key:
            return ("gpt-4o-mini", "openai", "日常问答：路由至 GPT-4o Mini")

        # 默认回退
        default_provider = getattr(settings, "ai_provider", "nvidia").lower()
        if default_provider == "nvidia":
            return (
                "meta/llama-3.2-11b-vision-instruct",
                "nvidia",
                "系统默认 NVIDIA 路由",
            )
        elif default_provider == "zhipu":
            return ("glm-4", "zhipu", "系统默认智谱路由")
        return ("glm-4", "zhipu", "兜底默认路由")

    async def chat(
        self,
        message: str,
        conversation_history: list[dict[str, str]] | None = None,
        model_id: str | None = None,
        model_provider: str | None = None,
    ) -> str:
        """
        Chat with AI assistant (non-streaming response).

        Args:
            message: User message
            conversation_history: Previous messages
            model_id: Specific model ID to use (optional)
            model_provider: Provider type for the model (optional)

        Returns:
            Complete response string
        """
        # Resolve 'auto' if specified or empty
        if not model_id or model_id.lower() == "auto":
            model_id, model_provider, reason = self.resolve_auto_model(
                message, conversation_history
            )
            logger.info(
                f"[Auto-Route] Selected {model_id} ({model_provider}): {reason}"
            )

        # Use specified model/provider if provided
        llm = self.llm
        if model_id and model_provider:
            try:
                llm = LLMFactory.create_provider_for_model(model_id, model_provider)
                logger.info(f"Using model {model_id} from provider {model_provider}")
            except Exception as e:
                logger.error(f"Failed to create provider for model {model_id}: {e}")
                if not self.llm:
                    return "I'm sorry, but the AI assistant is currently unavailable."
                llm = self.llm

        if not llm:
            return "I'm sorry, but the AI assistant is currently unavailable."

        try:
            system_prompt = """You are SOC Copilot, an AI assistant for security operations.
Help SOC analysts with alert analysis, investigations, playbook creation, and security questions.
Be concise, professional, and helpful."""

            messages = [{"role": "system", "content": system_prompt}]

            if conversation_history:
                messages.extend(
                    conversation_history[-10:]
                )  # Keep last 10 messages for context

            messages.append({"role": "user", "content": message})

            # Get complete response
            response = await llm.chat_completion(
                messages=messages,
                model=model_id,
                temperature=0.5,
                max_tokens=4096,
            )

            logger.info(f"Chat response length: {len(response)} chars")
            return response

        except Exception as e:
            logger.error(f"Error in chat: {e}")
            logger.warning(
                "Upstream LLM chat unavailable, activating rule-based chat fallback"
            )
            return self._rule_based_chat_fallback(message, reason=str(e))

    async def chat_stream(
        self,
        message: str,
        conversation_history: list[dict[str, str]] | None = None,
        model_id: str | None = None,
        model_provider: str | None = None,
    ):
        """Yield streamed chat deltas; falls back to a one-shot delta when
        the provider cannot stream. Never raises — LLM failures degrade to
        the rule-based fallback text as a single delta."""
        if not model_id or model_id.lower() == "auto":
            model_id, model_provider, _ = self.resolve_auto_model(
                message, conversation_history
            )

        llm = self.llm
        if model_id and model_provider:
            try:
                llm = LLMFactory.create_provider_for_model(model_id, model_provider)
            except Exception as e:
                logger.error(f"Failed to create provider for model {model_id}: {e}")
                llm = self.llm

        if not llm:
            yield self._rule_based_chat_fallback(message, reason="AI unavailable")
            return

        system_prompt = (
            "You are SOC Copilot, an AI assistant for security operations.\n"
            "Help SOC analysts with alert analysis, investigations, playbook "
            "creation, and security questions.\nBe concise, professional, and helpful."
        )
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history[-10:])
        messages.append({"role": "user", "content": message})

        try:
            collected: list[str] = []
            async for delta in stream_chat_completion(
                llm, messages, model=model_id, temperature=0.5, max_tokens=4096
            ):
                collected.append(delta)
                yield delta
            logger.info(
                f"Streamed chat response length: {sum(map(len, collected))} chars"
            )
        except Exception as e:
            logger.error(f"Error in chat stream: {e}")
            yield self._rule_based_chat_fallback(message, reason=str(e))

    def _rule_based_chat_fallback(self, message: str, reason: str = "") -> str:
        """Heuristic rule-based fallback response for chat when upstream LLM is unavailable."""
        import re

        msg_lower = message.lower()

        # Determine intent & context
        is_greeting = any(
            g in msg_lower for g in ["你好", "hello", "hi", "您好", "介绍", "你是谁"]
        )
        is_playbook = any(
            p in msg_lower
            for p in ["剧本", "playbook", "响应", "处置", "应急", "流程", "推荐"]
        )
        is_alert = any(
            a in msg_lower
            for a in [
                "告警",
                "alert",
                "日志",
                "log",
                "分析",
                "研判",
                "waf",
                "攻击",
                "powershell",
                "webshell",
            ]
        )
        is_cve = any(
            c in msg_lower
            for c in [
                "cve",
                "漏洞",
                "vulnerability",
                "rce",
                "sql注入",
                "xss",
                "反序列化",
            ]
        )
        is_report = any(
            r in msg_lower for r in ["报告", "report", "总结", "复盘", "生成"]
        )

        # Extract potential IOCs (IPs, CVEs)
        ip_matches = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", message)
        cve_matches = re.findall(r"(?i)cve-\d{4}-\d{4,7}", message)

        notice = (
            "> 💡 **服务降级通知**：检测到当前大模型上游接口暂时不可用（原因：`API密钥未生效或网络连通受限`）。\n"
            "> 系统已自动切换至**内置启发式安全运营专家规则引擎（Degraded Local Mode）**为您提供即时解答。\n\n"
        )

        if is_greeting:
            body = (
                "### 👋 您好！我是 SOC Copilot 智能安全副驾驶\n\n"
                "我专注于协助 SOC 分析师进行高效安全运营。虽然外部大模型当前处于离线/降级模式，但我仍可通过内置安全规则引擎为您提供以下核心服务：\n"
                "- 🛡️ **告警研判与日志特征分析**：直接粘贴日志或 WAF/EDR 告警，自动提取 IOC 与 ATT&CK 技战术映射\n"
                "- 📋 **应急响应剧本推荐**：提供勒索病毒、挖矿木马、暴力破解等高频事件的标准止血处置流程\n"
                "- 🔍 **威胁排查与处置命令生成**：快速生成 iptables、netsh 阻断命令及排查命令\n"
                "- 📑 **安全复盘报告生成**：整理排查要素一键生成 Markdown 格式调查报告\n\n"
                "请随时粘贴告警日志或描述您遇到的安全问题！"
            )
        elif is_playbook:
            body = (
                "### 📋 应急响应剧本推荐与处置流程\n\n"
                "根据您描述的安全事件，推荐执行以下标准 SOAR 应对流程：\n\n"
                "1. **第一阶段：紧急止血（遏制 Containment）**\n"
                "   - 隔离受害主机或限制其出网流量（防止横向移动及 C2 通信）\n"
                "   - 提取攻击源 IP 并在边界防火墙或 WAF 下发紧急黑名单封禁策略\n"
                "2. **第二阶段：取证排查（根因分析 Eradication）**\n"
                "   - 导出系统日志及网络连接快照（`netstat -ano` / `ss -tulnp`）\n"
                "   - 获取恶意样本或脚本哈希（MD5 / SHA256）并提交静态沙箱分析\n"
                "3. **第三阶段：根除加固（恢复 Recovery）**\n"
                "   - 清除自启动项、后门账号与恶意定时任务（crontab / Task Scheduler）\n"
                "   - 修补系统或应用程序漏洞，强制重置受影响主机凭证\n"
            )
        elif is_alert or is_cve:
            target_obj = message[:60].replace("\n", " ") + (
                "..." if len(message) > 60 else ""
            )
            lines = [
                "### 🛡️ 安全告警 / 威胁分析报告\n\n",
                f"**分析对象**：`{target_obj}`\n\n",
                "#### 1. 威胁研判与特征提取\n",
            ]
            if ip_matches:
                lines.append(
                    f"- **识别到的涉案 IP**：{', '.join(f'`{ip}`' for ip in set(ip_matches))}\n"
                )
            if cve_matches:
                lines.append(
                    f"- **关联 CVE 漏洞**：{', '.join(f'`{c.upper()}`' for c in set(cve_matches))}\n"
                )

            techniques = []
            if any(k in msg_lower for k in ["scan", "扫描", "探测", "nmap"]):
                techniques.append("T1046 - 网络服务发现 (Network Service Discovery)")
            if any(k in msg_lower for k in ["sql", "injection", "注入"]):
                techniques.append(
                    "T1190 - 利用面向互联网的应用程序 (Exploit Public-Facing Application)"
                )
            if any(k in msg_lower for k in ["brute", "暴破", "密码", "login"]):
                techniques.append("T1110 - 暴力破解凭证 (Brute Force)")
            if any(
                k in msg_lower for k in ["powershell", "cmd", "bash", "shell", "exec"]
            ):
                techniques.append(
                    "T1059 - 命令与脚本执行 (Command and Scripting Interpreter)"
                )
            if any(k in msg_lower for k in ["ransom", "勒索", "加密", "encrypt"]):
                techniques.append("T1486 - 针对性数据加密 (Data Encrypted for Impact)")

            if techniques:
                lines.append(
                    "- **MITRE ATT&CK 战术技术映射**：\n"
                    + "\n".join(f"  - {t}" for t in techniques)
                    + "\n\n"
                )
            else:
                lines.append(
                    "- **初步定性**：检测到可疑网络活动，建议重点核对通信端口与载荷参数。\n\n"
                )

            lines.append(
                "#### 2. 建议应急处置措施\n"
                "1. **网络阻断**：在防火墙或安全组上阻断可疑源 IP 的所有访问请求。\n"
                "2. **资产排查**：检查目标主机的活动进程列表及定时任务。\n"
                "3. **凭证审查**：排查是否有异常提权或高频失败登录记录。\n"
                "4. **情报检索**：在威胁情报平台（VT / AbuseIPDB）中交叉验证上述指标的声誉。\n"
            )
            body = "".join(lines)
        elif is_report:
            body = (
                "### 📑 安全事件排查总结报告模板\n\n"
                "| 字段 | 内容 |\n"
                "| :--- | :--- |\n"
                "| **事件概述** | 系统监测到异常安全事件，已完成初步处置与排查 |\n"
                "| **威胁等级** | 高危 (High) |\n"
                "| **涉及资产** | 受影响业务主机 / 内网服务器 |\n"
                "| **处置状态** | 风险已阻断，正处于根除与加固阶段 |\n\n"
                "#### 排查过程概要\n"
                "1. 接收到安全监控告警，触发安全运营自动化处置流程。\n"
                "2. 完成关键网络 IOC 阻断，切断潜在数据回传链路。\n"
                "3. 进行了系统级异常项清查，加固访问控制策略。\n"
            )
        else:
            body = (
                "### 💡 安全运营专家建议\n\n"
                f"针对您提出的问题：**“{message}”**\n\n"
                "在日常 SOC 运营与事件响应中，建议遵循以下标准实践：\n"
                "1. **上下文关联**：结合资产关键度与历史日志排查，避免孤立看待单个告警指标。\n"
                "2. **分级处置**：高危告警第一时间阻断外部网络通信，中低危告警进入排查工单。\n"
                "3. **自动化闭环**：通过配置 SOAR 剧本减少重复人工操作，提升 MTTR（平均响应时间）。\n\n"
                "若需深入研判，请直接粘贴详细日志片段、IP 或攻击命令。"
            )

        return notice + body

    async def generate_investigation_report(
        self, alert_id: str, investigation_data: dict[str, Any]
    ) -> str:
        """
        Generate investigation report in Markdown format.

        Args:
            alert_id: Alert ID
            investigation_data: Investigation findings

        Returns:
            Markdown report
        """
        if not self.llm:
            return "AI service not available for report generation."

        try:
            system_prompt = """You are a senior SOC analyst writing an investigation report.
Generate a professional Markdown report with:
- Executive Summary
- Alert Details
- Investigation Timeline
- Findings
- Recommendations
- Conclusion"""

            user_prompt = f"""Generate an investigation report for:
Alert ID: {sanitize_prompt_input(alert_id)}

Investigation Data:
{sanitize_json_for_prompt(investigation_data)}

Format the report in Markdown."""

            report = await self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,
                max_tokens=3000,
            )

            return report

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return f"Error generating report: {e!s}"


# Global service instance
_enhanced_ai_service: EnhancedAIService | None = None


def get_enhanced_ai_service() -> EnhancedAIService:
    """Get or create global enhanced AI service instance."""
    global _enhanced_ai_service
    if _enhanced_ai_service is None:
        _enhanced_ai_service = EnhancedAIService()
    return _enhanced_ai_service
