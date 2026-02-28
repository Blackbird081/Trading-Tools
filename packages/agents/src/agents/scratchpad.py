"""Agent Scratchpad — JSONL append-only audit trail for agent pipeline.

★ Inspired by Dexter's scratchpad.ts (github.com/Blackbird081/dexter).
★ Tracks all agent work: queries, tool calls, thinking, results.
★ Persisted to .trading/scratchpad/ for debugging and compliance.
★ Context clearing: removes oldest results from LLM context (not from file).
★ Tool call limiting: warns when tool called too many times (never blocks).

Usage:
    scratchpad = AgentScratchpad(query="Phân tích FPT")
    scratchpad.add_thinking("Đang phân tích RSI...")
    scratchpad.add_tool_result("technical_analysis", {"symbol": "FPT"}, result)
    context = scratchpad.get_tool_results()  # For LLM prompt
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("agents.scratchpad")

# Tool call limits (warn, never block)
DEFAULT_MAX_CALLS_PER_TOOL = 3
SIMILARITY_THRESHOLD = 0.7

SCRATCHPAD_DIR = Path(".trading/scratchpad")


class AgentScratchpad:
    """Append-only JSONL scratchpad for tracking agent work.

    ★ Single source of truth for all agent work on a query.
    ★ JSONL format: resilient to partial writes, easy to parse.
    ★ Context clearing is in-memory only — file is never modified.
    ★ Tool call counting with soft limits (warnings, not blocks).
    """

    def __init__(
        self,
        query: str,
        max_calls_per_tool: int = DEFAULT_MAX_CALLS_PER_TOOL,
    ) -> None:
        self._query = query
        self._max_calls_per_tool = max_calls_per_tool

        # Create scratchpad directory
        SCRATCHPAD_DIR.mkdir(parents=True, exist_ok=True)

        # Generate unique filename: TIMESTAMP_HASH.jsonl
        query_hash = hashlib.md5(query.encode()).hexdigest()[:12]
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d-%H%M%S")
        self._filepath = SCRATCHPAD_DIR / f"{timestamp}_{query_hash}.jsonl"

        # In-memory tracking
        self._tool_call_counts: dict[str, int] = {}
        self._tool_queries: dict[str, list[str]] = {}
        self._cleared_tool_indices: set[int] = set()

        # Write initial entry
        self._append({"type": "init", "content": query, "timestamp": datetime.now(UTC).isoformat()})

    # ── Write Methods ─────────────────────────────────────────────────────────

    def add_thinking(self, thought: str) -> None:
        """Record agent reasoning step."""
        self._append({"type": "thinking", "content": thought, "timestamp": datetime.now(UTC).isoformat()})

    def add_tool_result(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: str,
    ) -> None:
        """Record a tool call result."""
        # Try to parse result as JSON for cleaner storage
        try:
            parsed_result: Any = json.loads(result)
        except (json.JSONDecodeError, TypeError):
            parsed_result = result

        self._append({
            "type": "tool_result",
            "timestamp": datetime.now(UTC).isoformat(),
            "toolName": tool_name,
            "args": args,
            "result": parsed_result,
        })

    # ── Tool Limit Methods ────────────────────────────────────────────────────

    def can_call_tool(self, tool_name: str, query: str | None = None) -> dict[str, Any]:
        """Check if tool call can proceed. Returns {allowed: bool, warning?: str}.

        ★ Always allows the call but provides warnings to guide the LLM.
        ★ Warns when approaching/exceeding suggested limit.
        ★ Warns when query is similar to previous calls (retry loop detection).
        """
        current_count = self._tool_call_counts.get(tool_name, 0)
        max_calls = self._max_calls_per_tool

        if current_count >= max_calls:
            return {
                "allowed": True,
                "warning": (
                    f"Tool '{tool_name}' đã được gọi {current_count} lần "
                    f"(giới hạn khuyến nghị: {max_calls}). "
                    f"Nếu không có kết quả hữu ích, hãy thử: "
                    f"(1) dùng tool khác, (2) thay đổi tham số, "
                    f"(3) tiếp tục với dữ liệu hiện có."
                ),
            }

        if query:
            previous_queries = self._tool_queries.get(tool_name, [])
            similar = self._find_similar_query(query, previous_queries)
            if similar:
                remaining = max_calls - current_count
                return {
                    "allowed": True,
                    "warning": (
                        f"Query này rất giống với lần gọi '{tool_name}' trước. "
                        f"Còn {remaining} lần trước khi đạt giới hạn. "
                        f"Cân nhắc thay đổi cách tiếp cận."
                    ),
                }

        if current_count == max_calls - 1:
            return {
                "allowed": True,
                "warning": (
                    f"Sắp đạt giới hạn cho '{tool_name}' "
                    f"({current_count + 1}/{max_calls}). "
                    f"Nếu không có kết quả, hãy thử cách khác."
                ),
            }

        return {"allowed": True}

    def record_tool_call(self, tool_name: str, query: str | None = None) -> None:
        """Record a tool call attempt (call AFTER tool executes)."""
        self._tool_call_counts[tool_name] = self._tool_call_counts.get(tool_name, 0) + 1
        if query:
            self._tool_queries.setdefault(tool_name, []).append(query)

    def format_tool_usage_for_prompt(self) -> str | None:
        """Format tool usage status for injection into LLM prompts."""
        if not self._tool_call_counts:
            return None

        lines = []
        for tool_name, count in self._tool_call_counts.items():
            max_calls = self._max_calls_per_tool
            if count >= max_calls:
                status = f"{count} lần (vượt giới hạn {max_calls})"
            else:
                status = f"{count}/{max_calls} lần"
            lines.append(f"- {tool_name}: {status}")

        return (
            "## Lịch Sử Gọi Tool\n\n"
            + "\n".join(lines)
            + "\n\nLưu ý: Nếu tool không trả về kết quả hữu ích sau nhiều lần, hãy thử cách khác."
        )

    # ── Context Management ────────────────────────────────────────────────────

    def get_tool_results(self) -> str:
        """Get formatted tool results for LLM prompt (excluding cleared entries)."""
        entries = self._read_entries()
        tool_result_index = 0
        formatted: list[str] = []

        for entry in entries:
            if entry.get("type") != "tool_result":
                continue

            if tool_result_index in self._cleared_tool_indices:
                formatted.append(f"[Tool result #{tool_result_index + 1} cleared from context]")
                tool_result_index += 1
                continue

            tool_name = entry.get("toolName", "unknown")
            args = entry.get("args", {})
            result = entry.get("result", "")
            args_str = ", ".join(f"{k}={v}" for k, v in args.items())
            result_str = json.dumps(result) if not isinstance(result, str) else result
            formatted.append(f"### {tool_name}({args_str})\n{result_str}")
            tool_result_index += 1

        return "\n\n".join(formatted)

    def clear_oldest_tool_results(self, keep_count: int) -> int:
        """Clear oldest tool results from context (in-memory only, file unchanged).

        ★ Anthropic-style: removes oldest results, keeps most recent N.
        ★ Returns number of results cleared.
        """
        entries = self._read_entries()
        tool_result_indices: list[int] = []

        index = 0
        for entry in entries:
            if entry.get("type") == "tool_result":
                if index not in self._cleared_tool_indices:
                    tool_result_indices.append(index)
                index += 1

        to_clear = max(0, len(tool_result_indices) - keep_count)
        if to_clear == 0:
            return 0

        for i in range(to_clear):
            self._cleared_tool_indices.add(tool_result_indices[i])

        logger.debug("Cleared %d oldest tool results from context", to_clear)
        return to_clear

    def get_tool_call_records(self) -> list[dict[str, Any]]:
        """Get all tool call records for audit/reporting."""
        return [
            {
                "tool": e["toolName"],
                "args": e.get("args", {}),
                "result": json.dumps(e["result"]) if not isinstance(e.get("result"), str) else e["result"],
                "timestamp": e.get("timestamp", ""),
            }
            for e in self._read_entries()
            if e.get("type") == "tool_result" and "toolName" in e
        ]

    def has_tool_results(self) -> bool:
        return any(e.get("type") == "tool_result" for e in self._read_entries())

    @property
    def filepath(self) -> Path:
        return self._filepath

    # ── Private Methods ───────────────────────────────────────────────────────

    def _append(self, entry: dict[str, Any]) -> None:
        """Append-only write to JSONL file."""
        try:
            with open(self._filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            logger.exception("Failed to write scratchpad entry")

    def _read_entries(self) -> list[dict[str, Any]]:
        """Read all entries from JSONL file. Skips malformed lines."""
        if not self._filepath.exists():
            return []
        entries: list[dict[str, Any]] = []
        try:
            with open(self._filepath, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if isinstance(entry, dict) and "type" in entry:
                            entries.append(entry)
                    except json.JSONDecodeError:
                        pass  # Skip malformed lines
        except Exception:
            logger.exception("Failed to read scratchpad")
        return entries

    def _find_similar_query(self, new_query: str, previous_queries: list[str]) -> str | None:
        """Find a similar previous query using Jaccard similarity."""
        new_words = self._tokenize(new_query)
        for prev_query in previous_queries:
            prev_words = self._tokenize(prev_query)
            similarity = self._jaccard_similarity(new_words, prev_words)
            if similarity >= SIMILARITY_THRESHOLD:
                return prev_query
        return None

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """Tokenize text into normalized words."""
        import re
        words = re.sub(r"[^\w\s]", " ", text.lower()).split()
        return {w for w in words if len(w) > 2}

    @staticmethod
    def _jaccard_similarity(set1: set[str], set2: set[str]) -> float:
        """Calculate Jaccard similarity between two word sets."""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
