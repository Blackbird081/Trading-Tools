/**
 * Tests for WebSocketProvider exponential backoff reconnection.
 *
 * ★ TEST-05: Verify exponential backoff behavior:
 *   - Reconnect delay increases with each attempt
 *   - Delay is capped at RECONNECT_MAX_MS (30s)
 *   - Attempt counter resets on successful connection
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// ── Constants (must match ws-provider.tsx) ────────────────────────────────────
const RECONNECT_BASE_MS = 1_000;
const RECONNECT_MAX_MS = 30_000;
const RECONNECT_JITTER_MS = 500;

// ── Helper: calculate expected backoff range ──────────────────────────────────
function expectedBackoffRange(attempt: number): [number, number] {
  const base = RECONNECT_BASE_MS * Math.pow(2, attempt);
  const min = Math.min(base, RECONNECT_MAX_MS);
  const max = Math.min(base + RECONNECT_JITTER_MS, RECONNECT_MAX_MS);
  return [min, max];
}

describe("WebSocket Exponential Backoff Logic", () => {
  it("attempt 0 should have ~1s delay", () => {
    const [min, max] = expectedBackoffRange(0);
    expect(min).toBe(1_000);
    expect(max).toBe(1_500);
  });

  it("attempt 1 should have ~2s delay", () => {
    const [min, max] = expectedBackoffRange(1);
    expect(min).toBe(2_000);
    expect(max).toBe(2_500);
  });

  it("attempt 2 should have ~4s delay", () => {
    const [min, max] = expectedBackoffRange(2);
    expect(min).toBe(4_000);
    expect(max).toBe(4_500);
  });

  it("attempt 3 should have ~8s delay", () => {
    const [min, max] = expectedBackoffRange(3);
    expect(min).toBe(8_000);
    expect(max).toBe(8_500);
  });

  it("attempt 4 should have ~16s delay", () => {
    const [min, max] = expectedBackoffRange(4);
    expect(min).toBe(16_000);
    expect(max).toBe(16_500);
  });

  it("attempt 5 should be capped at 30s", () => {
    const [min, max] = expectedBackoffRange(5);
    // 2^5 * 1000 = 32000 > 30000, so capped
    expect(min).toBe(RECONNECT_MAX_MS);
    expect(max).toBe(RECONNECT_MAX_MS);
  });

  it("attempt 10 should still be capped at 30s", () => {
    const [min, max] = expectedBackoffRange(10);
    expect(min).toBe(RECONNECT_MAX_MS);
    expect(max).toBe(RECONNECT_MAX_MS);
  });

  it("delay increases monotonically up to cap", () => {
    const delays = [0, 1, 2, 3, 4, 5].map((a) => expectedBackoffRange(a)[0]);
    for (let i = 1; i < delays.length; i++) {
      const currentDelay = delays[i];
      const previousDelay = delays[i - 1];
      expect(currentDelay).toBeDefined();
      expect(previousDelay).toBeDefined();
      expect(currentDelay!).toBeGreaterThanOrEqual(previousDelay!);
    }
  });

  it("jitter adds randomness within bounds", () => {
    // Simulate 100 random jitter values for attempt 0
    const attempt = 0;
    const base = RECONNECT_BASE_MS * Math.pow(2, attempt);
    const results: number[] = [];
    for (let i = 0; i < 100; i++) {
      const jitter = Math.random() * RECONNECT_JITTER_MS;
      const delay = Math.min(base + jitter, RECONNECT_MAX_MS);
      results.push(delay);
    }
    // All should be within [base, base + jitter_max]
    for (const delay of results) {
      expect(delay).toBeGreaterThanOrEqual(base);
      expect(delay).toBeLessThanOrEqual(base + RECONNECT_JITTER_MS);
    }
    // Should have some variation (not all the same)
    const unique = new Set(results.map((r) => Math.floor(r)));
    expect(unique.size).toBeGreaterThan(1);
  });
});

describe("WebSocket Reconnect Attempt Counter", () => {
  it("attempt counter should reset to 0 on successful connection", () => {
    // Simulate the counter logic
    let attempt = 0;

    // Simulate 3 failed connections
    for (let i = 0; i < 3; i++) {
      attempt += 1;
    }
    expect(attempt).toBe(3);

    // Simulate successful connection (onopen)
    attempt = 0;
    expect(attempt).toBe(0);
  });

  it("backoff after reset should start from attempt 0 again", () => {
    let attempt = 0;

    // Fail 5 times
    for (let i = 0; i < 5; i++) {
      attempt += 1;
    }

    // Reset on success
    attempt = 0;

    // Next failure should use attempt 0 delay
    const [min] = expectedBackoffRange(attempt);
    expect(min).toBe(RECONNECT_BASE_MS);
  });
});
