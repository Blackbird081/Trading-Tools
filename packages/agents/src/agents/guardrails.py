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
    "api_key": r"\b(sk-|pk-|api[-_]?key)[\w-]{20,}\b",
    "password": r"(?i)(password|passwd|mật\s*khẩu)\s*[:=]\s*\S+",
    "secret": r"(?i)(secret|token|bí\s*mật)\s*[:=]\s*\S+",
}

_BANK_ACCOUNT_NUMBER_PATTERN = re.compile(r"\b\d{8,16}\b")
_BANK_ALLOW_CONTEXTS = (
    "stk",
    "số tk",
    "so tk",
    "số tài khoản",
    "so tai khoan",
    "tai khoan",
    "account no",
    "account number",
    "bank account",
    "ngân hàng",
    "ngan hang",
    "chuyển khoản",
    "chuyen khoan",
    "chuyển tiền",
    "chuyen tien",
    "vietcombank",
    "vietinbank",
    "bidv",
    "agribank",
    "techcombank",
    "mbbank",
    "acb",
    "vpbank",
    "tpbank",
    "sacombank",
    "hdbank",
    "vib",
    "shb",
    "msb",
    "ocb",
    "lpbank",
)
_BANK_DENY_CONTEXTS = (
    "vnindex",
    "hnx",
    "upcom",
    "rsi",
    "macd",
    "eps",
    "roe",
    "p/e",
    "pe",
    "kl",
    "gtgd",
    "volume",
    "order id",
    "ma ck",
    "mã ck",
    "symbol",
)

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
        sanitized = self._redact_bank_accounts(sanitized)
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

    def _redact_bank_accounts(self, text: str) -> str:
        """Redact bank-account-like numbers only when VN banking context is present.

        This avoids false positives on benign market/indicator numeric text.
        """
        stripped = text.strip()

        def _replace(match: re.Match[str]) -> str:
            raw = match.group(0)
            if stripped == raw and len(raw) >= 10:
                return "[BANK_ACCOUNT_REDACTED]"

            start, end = match.span()
            window = text[max(0, start - 40): min(len(text), end + 40)].lower()

            has_allow_context = any(token in window for token in _BANK_ALLOW_CONTEXTS)
            has_deny_context = any(token in window for token in _BANK_DENY_CONTEXTS)

            if has_allow_context and not has_deny_context:
                return "[BANK_ACCOUNT_REDACTED]"
            return raw

        return _BANK_ACCOUNT_NUMBER_PATTERN.sub(_replace, text)
