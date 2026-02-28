"""AI Guardrails — Input/Output validation for financial agents.

★ Inspired by FinceptTerminal's guardrails_module.py.
★ PII detection (VN), prompt injection protection, financial compliance.
"""
from __future__ import annotations
import logging
import re

logger = logging.getLogger("agents.guardrails")

_PII_PATTERNS: dict[str, str] = {
    "cmnd_cccd": r"\b\d{9}\b|\b\d{12}\b",
    "phone_vn": r"\b(0[3-9]\d{8})\b",
    "credit_card": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
    "bank_account": r"\b\d{10,19}\b",
    "api_key": r"\b(sk-|pk-|api[-_]?key)[\w-]{20,}\b",
    "password": r"(?i)(password|passwd|mật\s*khẩu)\s*[:=]\s*\S+",
    "secret": r"(?i)(secret|token|bí\s*mật)\s*[:=]\s*\S+",
}

_INJECTION_PATTERNS: list[str] = [
    r"(?i)ignore\s+(previous|all|above)\s+instructions?",
    r"(?i)forget\s+(everything|all|previous)",
    r"(?i)you\s+are\s+now\s+(a|an)\s+\w+",
    r"(?i)jailbreak",
    r"(?i)system\s*prompt\s*:",
    r"(?i)bỏ\s+qua\s+hướng\s+dẫn",
    r"(?i)quên\s+tất\s+cả",
]


class AgentGuardrailPipeline:
    """Composite guardrail pipeline for financial agents."""

    def __init__(self) -> None:
        self._pii_patterns = {name: re.compile(pattern) for name, pattern in _PII_PATTERNS.items()}
        self._injection_patterns = [re.compile(p) for p in _INJECTION_PATTERNS]

    def check_input(self, text: str) -> tuple[bool, str]:
        """Check and sanitize input. Returns (is_safe, sanitized_text)."""
        for pattern in self._injection_patterns:
            if pattern.search(text):
                logger.warning("Prompt injection detected")
                return False, text
        sanitized = text
        for pii_type, pattern in self._pii_patterns.items():
            if pattern.search(sanitized):
                sanitized = pattern.sub(f"[{pii_type.upper()}_REDACTED]", sanitized)
        return True, sanitized

    def sanitize_news_headlines(self, headlines: list[str]) -> list[str]:
        """Sanitize news headlines for LLM consumption."""
        sanitized: list[str] = []
        for headline in headlines:
            is_safe, clean = self.check_input(headline)
            if is_safe:
                sanitized.append(clean)
            else:
                logger.warning("Headline blocked: %s...", headline[:50])
        return sanitized
