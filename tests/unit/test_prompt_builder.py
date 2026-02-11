from __future__ import annotations

import json
from pathlib import Path

import pytest
from agents.prompt_builder import (
    FinancialPromptBuilder,
    PromptRegistry,
)


@pytest.fixture
def prompts_dir(tmp_path: Path) -> Path:
    """Create a temporary prompts directory with manifest."""
    manifest = {
        "prompts": {
            "financial_analysis": {
                "description": "Test prompt",
                "active_version": "v1.0.0",
                "versions": {
                    "v1.0.0": {
                        "file": "financial_analysis/v1.0.0.md",
                        "model_target": "phi-3-mini",
                        "max_tokens": 512,
                        "temperature": 0.3,
                    },
                    "v2.0.0": {
                        "file": "financial_analysis/v2.0.0.md",
                        "model_target": "llama-3-8b",
                        "max_tokens": 1024,
                        "temperature": 0.5,
                    },
                },
            }
        }
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    fa_dir = tmp_path / "financial_analysis"
    fa_dir.mkdir()
    (fa_dir / "v1.0.0.md").write_text("System prompt v1", encoding="utf-8")
    (fa_dir / "v2.0.0.md").write_text("System prompt v2", encoding="utf-8")
    return tmp_path


class TestPromptRegistry:
    def test_get_active_version(self, prompts_dir: Path) -> None:
        reg = PromptRegistry(prompts_dir)
        pv = reg.get_active("financial_analysis")
        assert pv.version == "v1.0.0"
        assert pv.template == "System prompt v1"
        assert pv.model_target == "phi-3-mini"

    def test_get_specific_version(self, prompts_dir: Path) -> None:
        reg = PromptRegistry(prompts_dir)
        pv = reg.get_version("financial_analysis", "v2.0.0")
        assert pv.version == "v2.0.0"
        assert pv.template == "System prompt v2"

    def test_cache_works(self, prompts_dir: Path) -> None:
        reg = PromptRegistry(prompts_dir)
        pv1 = reg.get_active("financial_analysis")
        pv2 = reg.get_active("financial_analysis")
        assert pv1 is pv2

    def test_list_versions(self, prompts_dir: Path) -> None:
        reg = PromptRegistry(prompts_dir)
        versions = reg.list_versions("financial_analysis")
        assert len(versions) == 2

    def test_missing_manifest(self, tmp_path: Path) -> None:
        reg = PromptRegistry(tmp_path)
        assert reg._manifest == {}


class TestFinancialPromptBuilder:
    def test_build_analysis_prompt(self, prompts_dir: Path) -> None:
        reg = PromptRegistry(prompts_dir)
        builder = FinancialPromptBuilder(reg)
        prompt, pv = builder.build_analysis_prompt(
            symbol="FPT",
            company_name="FPT Corp",
            technical_score=7.5,
            rsi=35.0,
            macd_signal="bullish_cross",
            bb_position="below_lower",
            trend_ma="golden_cross",
        )
        assert "<|system|>" in prompt
        assert "System prompt v1" in prompt
        assert "FPT" in prompt
        assert pv.version == "v1.0.0"

    def test_build_with_fundamentals(self, prompts_dir: Path) -> None:
        reg = PromptRegistry(prompts_dir)
        builder = FinancialPromptBuilder(reg)
        prompt, _ = builder.build_analysis_prompt(
            symbol="VNM",
            company_name="Vinamilk",
            technical_score=3.0,
            rsi=55.0,
            macd_signal="neutral",
            bb_position="inside",
            trend_ma="neutral",
            eps_growth=0.15,
            pe_ratio=12.5,
        )
        assert "EPS" in prompt
        assert "PE ratio" in prompt

    def test_build_with_news(self, prompts_dir: Path) -> None:
        reg = PromptRegistry(prompts_dir)
        builder = FinancialPromptBuilder(reg)
        prompt, _ = builder.build_analysis_prompt(
            symbol="HPG",
            company_name="Hoa Phat",
            technical_score=5.0,
            rsi=40.0,
            macd_signal="bullish_cross",
            bb_position="inside",
            trend_ma="golden_cross",
            news_headlines=["HPG tang 5%", "Thep tang gia"],
        )
        assert "HPG tang 5%" in prompt

    def test_specific_version_override(self, prompts_dir: Path) -> None:
        reg = PromptRegistry(prompts_dir)
        builder = FinancialPromptBuilder(reg)
        prompt, pv = builder.build_analysis_prompt(
            symbol="FPT",
            company_name="FPT Corp",
            technical_score=7.5,
            rsi=35.0,
            macd_signal="bullish_cross",
            bb_position="below_lower",
            trend_ma="golden_cross",
            prompt_version="v2.0.0",
        )
        assert "System prompt v2" in prompt
        assert pv.version == "v2.0.0"
