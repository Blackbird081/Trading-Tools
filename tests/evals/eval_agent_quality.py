"""LLM-as-Judge Evaluation Suite for Trading Agent.

★ Inspired by Dexter's eval suite with LangSmith integration.
★ Tests agent signal quality against expected outcomes.
★ Uses LLM-as-judge to score correctness.

Usage:
    uv run python tests/evals/eval_agent_quality.py
    uv run python tests/evals/eval_agent_quality.py --sample 5

Dataset format (CSV):
    question,expected_signal,expected_reasoning
    "Phân tích FPT","BUY","RSI oversold + MACD bullish cross + strong earnings"
    "Đánh giá VNM","NEUTRAL","P/E cao, tăng trưởng chậm"
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import random
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("evals")

EVAL_DATASET_PATH = Path("tests/evals/data/agent_eval_dataset.csv")
RESULTS_DIR = Path("tests/evals/results")


@dataclass
class EvalExample:
    """A single evaluation example."""

    question: str
    expected_signal: str  # BUY | SELL | NEUTRAL | STRONG_BUY | STRONG_SELL
    expected_reasoning: str


@dataclass
class EvalResult:
    """Result of evaluating a single example."""

    question: str
    expected_signal: str
    actual_signal: str | None
    actual_reasoning: str | None
    score: float  # 0.0 to 1.0
    judge_reasoning: str
    passed: bool
    duration_ms: float


class AgentEvaluator:
    """Evaluates agent signal quality using LLM-as-judge.

    ★ Inspired by Dexter's eval runner.
    ★ Runs agent on each question, compares to expected output.
    ★ Uses LLM to judge correctness (not just exact match).
    """

    def __init__(
        self,
        agent_runner: Any,
        judge_llm: Any | None = None,
        sample_size: int | None = None,
    ) -> None:
        self._agent = agent_runner
        self._judge = judge_llm
        self._sample_size = sample_size

    def load_dataset(self, path: Path = EVAL_DATASET_PATH) -> list[EvalExample]:
        """Load evaluation dataset from CSV."""
        if not path.exists():
            logger.warning("Eval dataset not found: %s — using sample data", path)
            return self._get_sample_dataset()

        examples: list[EvalExample] = []
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("question"):
                    examples.append(EvalExample(
                        question=row["question"],
                        expected_signal=row.get("expected_signal", "NEUTRAL"),
                        expected_reasoning=row.get("expected_reasoning", ""),
                    ))

        if self._sample_size and self._sample_size < len(examples):
            examples = random.sample(examples, self._sample_size)

        logger.info("Loaded %d eval examples", len(examples))
        return examples

    async def run(self, examples: list[EvalExample] | None = None) -> list[EvalResult]:
        """Run evaluation on all examples."""
        if examples is None:
            examples = self.load_dataset()

        results: list[EvalResult] = []
        passed = 0

        print(f"\n{'='*60}")
        print(f"Running {len(examples)} eval examples...")
        print(f"{'='*60}\n")

        for i, example in enumerate(examples, 1):
            print(f"[{i}/{len(examples)}] {example.question[:60]}...")
            start = datetime.now(UTC)

            try:
                result = await self._evaluate_example(example)
                results.append(result)
                if result.passed:
                    passed += 1
                    print(f"  ✅ PASS (score: {result.score:.2f}) — {result.actual_signal}")
                else:
                    print(f"  ❌ FAIL (score: {result.score:.2f}) — expected: {result.expected_signal}, got: {result.actual_signal}")
            except Exception as exc:
                logger.exception("Eval failed for: %s", example.question)
                results.append(EvalResult(
                    question=example.question,
                    expected_signal=example.expected_signal,
                    actual_signal=None,
                    actual_reasoning=None,
                    score=0.0,
                    judge_reasoning=f"Error: {exc}",
                    passed=False,
                    duration_ms=0.0,
                ))

        accuracy = passed / len(results) if results else 0.0
        print(f"\n{'='*60}")
        print(f"Results: {passed}/{len(results)} passed ({accuracy:.1%} accuracy)")
        print(f"{'='*60}\n")

        # Save results
        self._save_results(results, accuracy)
        return results

    async def _evaluate_example(self, example: EvalExample) -> EvalResult:
        """Evaluate a single example."""
        import time
        start = time.monotonic()

        # Run agent
        agent_output = await self._run_agent(example.question)
        duration_ms = (time.monotonic() - start) * 1000

        # Extract signal from agent output
        actual_signal = self._extract_signal(agent_output)
        actual_reasoning = self._extract_reasoning(agent_output)

        # Judge correctness
        score, judge_reasoning = await self._judge_correctness(
            question=example.question,
            expected_signal=example.expected_signal,
            expected_reasoning=example.expected_reasoning,
            actual_signal=actual_signal,
            actual_reasoning=actual_reasoning,
        )

        return EvalResult(
            question=example.question,
            expected_signal=example.expected_signal,
            actual_signal=actual_signal,
            actual_reasoning=actual_reasoning,
            score=score,
            judge_reasoning=judge_reasoning,
            passed=score >= 0.7,
            duration_ms=duration_ms,
        )

    async def _run_agent(self, question: str) -> dict[str, Any]:
        """Run the agent on a question."""
        if self._agent is None:
            return {"signal": "NEUTRAL", "reasoning": "No agent configured"}
        try:
            result = await self._agent(question)
            return result if isinstance(result, dict) else {"raw": str(result)}
        except Exception as exc:
            return {"error": str(exc)}

    def _extract_signal(self, output: dict[str, Any]) -> str | None:
        """Extract trading signal from agent output."""
        # Try common output formats
        for key in ("signal", "recommended_action", "dominant_signal", "action"):
            if key in output:
                return str(output[key]).upper()
        # Try nested
        if "persona_consensus" in output:
            for symbol_data in output["persona_consensus"].values():
                return str(symbol_data.get("dominant_signal", "NEUTRAL")).upper()
        return None

    def _extract_reasoning(self, output: dict[str, Any]) -> str | None:
        """Extract reasoning from agent output."""
        for key in ("reasoning", "reason", "explanation", "analysis"):
            if key in output:
                return str(output[key])
        return None

    async def _judge_correctness(
        self,
        question: str,
        expected_signal: str,
        expected_reasoning: str,
        actual_signal: str | None,
        actual_reasoning: str | None,
    ) -> tuple[float, str]:
        """Use LLM to judge correctness of agent output.

        Returns (score 0.0-1.0, judge_reasoning).
        """
        # Simple rule-based scoring if no LLM judge
        if self._judge is None:
            return self._rule_based_score(expected_signal, actual_signal)

        # LLM-as-judge prompt
        prompt = f"""Đánh giá chất lượng phân tích của trading agent.

Câu hỏi: {question}
Tín hiệu kỳ vọng: {expected_signal}
Lý do kỳ vọng: {expected_reasoning}

Tín hiệu thực tế: {actual_signal or 'Không có'}
Lý do thực tế: {actual_reasoning or 'Không có'}

Hãy đánh giá:
1. Tín hiệu có đúng không? (BUY/SELL/NEUTRAL phải khớp hoặc gần đúng)
2. Lý do có hợp lý không?
3. Phân tích có đầy đủ không?

Trả về JSON: {{"score": 0.0-1.0, "reasoning": "giải thích ngắn gọn"}}
"""
        try:
            response = await self._judge(prompt)
            data = json.loads(response)
            return float(data.get("score", 0.5)), str(data.get("reasoning", ""))
        except Exception:
            return self._rule_based_score(expected_signal, actual_signal)

    @staticmethod
    def _rule_based_score(expected: str, actual: str | None) -> tuple[float, str]:
        """Simple rule-based scoring when no LLM judge available."""
        if actual is None:
            return 0.0, "No signal produced"

        expected_norm = expected.upper().replace("_", "")
        actual_norm = actual.upper().replace("_", "")

        if expected_norm == actual_norm:
            return 1.0, "Exact match"

        # Partial credit for directional match
        buy_signals = {"BUY", "STRONGBUY"}
        sell_signals = {"SELL", "STRONGSELL"}
        neutral_signals = {"NEUTRAL", "HOLD"}

        expected_dir = "buy" if expected_norm in buy_signals else ("sell" if expected_norm in sell_signals else "neutral")
        actual_dir = "buy" if actual_norm in buy_signals else ("sell" if actual_norm in sell_signals else "neutral")

        if expected_dir == actual_dir:
            return 0.7, "Directional match (different strength)"
        return 0.0, f"Mismatch: expected {expected}, got {actual}"

    def _save_results(self, results: list[EvalResult], accuracy: float) -> None:
        """Save evaluation results to JSON file."""
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d-%H%M%S")
        output_path = RESULTS_DIR / f"eval_{timestamp}.json"

        data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "accuracy": accuracy,
            "total": len(results),
            "passed": sum(1 for r in results if r.passed),
            "results": [
                {
                    "question": r.question,
                    "expected_signal": r.expected_signal,
                    "actual_signal": r.actual_signal,
                    "score": r.score,
                    "passed": r.passed,
                    "judge_reasoning": r.judge_reasoning,
                    "duration_ms": r.duration_ms,
                }
                for r in results
            ],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info("Eval results saved to %s", output_path)

    @staticmethod
    def _get_sample_dataset() -> list[EvalExample]:
        """Return sample dataset for testing."""
        return [
            EvalExample(
                question="Phân tích kỹ thuật FPT: RSI=28, MACD bullish cross, volume spike 3x",
                expected_signal="BUY",
                expected_reasoning="RSI oversold + MACD bullish cross + volume confirmation",
            ),
            EvalExample(
                question="Đánh giá VNM: P/E=25, tăng trưởng doanh thu 5%, ROE=18%",
                expected_signal="NEUTRAL",
                expected_reasoning="P/E cao so với tăng trưởng, ROE tốt nhưng không đủ để BUY mạnh",
            ),
            EvalExample(
                question="Phân tích HPG: RSI=75, MACD bearish cross, giá tại BB upper",
                expected_signal="SELL",
                expected_reasoning="RSI overbought + MACD bearish cross + giá tại kháng cự",
            ),
        ]


async def main() -> None:
    """Main entry point for eval runner."""
    parser = argparse.ArgumentParser(description="Run agent quality evaluation")
    parser.add_argument("--sample", type=int, help="Run on random sample of N examples")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    evaluator = AgentEvaluator(
        agent_runner=None,  # Replace with actual agent
        judge_llm=None,     # Replace with LLM judge
        sample_size=args.sample,
    )

    examples = evaluator.load_dataset()
    results = await evaluator.run(examples)

    # Print summary
    accuracy = sum(1 for r in results if r.passed) / len(results) if results else 0
    print(f"\nFinal accuracy: {accuracy:.1%}")
    sys.exit(0 if accuracy >= 0.7 else 1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
