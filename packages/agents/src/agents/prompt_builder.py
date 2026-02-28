from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("agents.prompt")


@dataclass(frozen=True, slots=True)
class PromptVersion:
    """A versioned prompt template."""

    name: str
    version: str
    template: str
    model_target: str
    max_tokens: int
    temperature: float

    def render(self, **kwargs: Any) -> str:
        """Render prompt template with variables."""
        return self.template


class PromptRegistry:
    """Central registry for all versioned prompts.

    Loads from manifest.json, resolves active versions.
    """

    def __init__(self, prompts_dir: Path) -> None:
        self._dir = prompts_dir
        self._manifest: dict[str, Any] = {}
        self._cache: dict[str, PromptVersion] = {}
        self._load_manifest()

    def _load_manifest(self) -> None:
        manifest_path = self._dir / "manifest.json"
        if manifest_path.exists():
            self._manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    def get_active(self, prompt_name: str) -> PromptVersion:
        """Get the currently active version of a prompt."""
        prompt_config = self._manifest["prompts"][prompt_name]
        active_ver: str = prompt_config["active_version"]
        return self.get_version(prompt_name, active_ver)

    def get_version(self, prompt_name: str, version: str) -> PromptVersion:
        """Get a specific version of a prompt."""
        cache_key = f"{prompt_name}:{version}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        prompt_config = self._manifest["prompts"][prompt_name]
        ver_config = prompt_config["versions"][version]

        template_path = self._dir / ver_config["file"]
        template = template_path.read_text(encoding="utf-8")

        pv = PromptVersion(
            name=prompt_name,
            version=version,
            template=template,
            model_target=ver_config["model_target"],
            max_tokens=ver_config["max_tokens"],
            temperature=ver_config["temperature"],
        )
        self._cache[cache_key] = pv
        return pv

    def list_versions(self, prompt_name: str) -> list[dict[str, Any]]:
        """List all versions with metadata."""
        prompt_config = self._manifest["prompts"][prompt_name]
        return [{"version": ver, **config} for ver, config in prompt_config["versions"].items()]


class FinancialPromptBuilder:
    """Assembles complete prompts for financial analysis."""

    def __init__(self, registry: PromptRegistry) -> None:
        self._registry = registry

    def build_analysis_prompt(
        self,
        symbol: str,
        company_name: str,
        technical_score: float,
        rsi: float,
        macd_signal: str,
        bb_position: str,
        trend_ma: str,
        eps_growth: float | None = None,
        pe_ratio: float | None = None,
        news_headlines: list[str] | None = None,
        prompt_version: str | None = None,
        extra_context: str | None = None,  # ★ NEW: early warning + DuPont context
    ) -> tuple[str, PromptVersion]:
        """Build complete prompt for Fundamental Agent."""
        if prompt_version:
            pv = self._registry.get_version("financial_analysis", prompt_version)
        else:
            pv = self._registry.get_active("financial_analysis")

        system_prompt = pv.template
        user_prompt = self._build_user_section(
            symbol=symbol,
            company_name=company_name,
            technical_score=technical_score,
            rsi=rsi,
            macd_signal=macd_signal,
            bb_position=bb_position,
            trend_ma=trend_ma,
            eps_growth=eps_growth,
            pe_ratio=pe_ratio,
            news_headlines=news_headlines,
            extra_context=extra_context,
        )

        full_prompt = (
            f"<|system|>\n{system_prompt}\n<|end|>\n"
            f"<|user|>\n{user_prompt}\n<|end|>\n"
            f"<|assistant|>\n"
        )
        return full_prompt, pv

    def _build_user_section(
        self,
        symbol: str,
        company_name: str,
        technical_score: float,
        rsi: float,
        macd_signal: str,
        bb_position: str,
        trend_ma: str,
        eps_growth: float | None,
        pe_ratio: float | None,
        news_headlines: list[str] | None,
        extra_context: str | None = None,  # ★ NEW
    ) -> str:
        lines = [
            f"Phan tich ma: {symbol} ({company_name})",
            "",
            "## Chi bao ky thuat:",
            f"- RSI(14): {rsi:.1f}",
            f"- MACD: {macd_signal}",
            f"- Bollinger Bands: {bb_position}",
            f"- MA50/MA200: {trend_ma}",
            f"- Diem tong hop: {technical_score:+.1f}/10",
        ]

        if eps_growth is not None or pe_ratio is not None:
            lines.append("")
            lines.append("## Co ban:")
            if eps_growth is not None:
                lines.append(f"- EPS tang truong: {eps_growth:.1%}")
            if pe_ratio is not None:
                lines.append(f"- PE ratio: {pe_ratio:.1f}")

        if news_headlines:
            lines.append("")
            lines.append("## Tin tuc gan day:")
            for headline in news_headlines[:5]:
                lines.append(f"- {headline}")

        # ★ NEW: Inject early warning + DuPont context
        if extra_context:
            lines.append("")
            lines.append("## Phan tich tai chinh nang cao:")
            lines.append(extra_context.strip())

        lines.append("")
        lines.append("Hay phan tich va dua ra khuyen nghi.")
        return "\n".join(lines)
