# Local API Contracts (Portfolio / Orders / Screener)

## CVF Traceability
- CVF-Doc-ID: CVF-TT-LOCAL-CONTRACT-20260303-R1
- Last-Updated: 2026-03-03
- Owner: Engineering
- Plan Mapping: `LOCAL_PERSONAL_TRADING_ROADMAP.md` -> Phase 0

## Scope
This document locks the API contract baseline for local personal trading migration.
It distinguishes:
- `Current` = what runtime provides now.
- `Target` = required contract to complete roadmap phases.

## 1) Portfolio Contract

### Current
- `GET /api/portfolio`
  - Status: stub
  - Current response:
    ```json
    {
      "status": "stub",
      "message": "Portfolio endpoint pending Phase 5 integration"
    }
    ```

### Target
- `GET /api/portfolio`
  - Response:
    ```json
    {
      "account_id": "string",
      "mode": "dry-run|live",
      "cash": 0,
      "nav": 0,
      "purchasing_power": 0,
      "last_sync_at": "ISO-8601"
    }
    ```
- `GET /api/portfolio/positions`
  - Response:
    ```json
    {
      "positions": [
        {
          "symbol": "FPT",
          "quantity": 0,
          "sellable_qty": 0,
          "avg_price": 0,
          "market_price": 0,
          "unrealized_pnl": 0,
          "unrealized_pnl_pct": 0
        }
      ],
      "source": "broker|dry-run-cache",
      "last_sync_at": "ISO-8601"
    }
    ```
- `GET /api/portfolio/pnl?days=30`
  - Response:
    ```json
    {
      "series": [
        { "date": "YYYY-MM-DD", "pnl": 0, "nav": 0 }
      ],
      "days": 30
    }
    ```

## 2) Orders Contract

### Current
- No public REST order API is exposed in `interface.rest`.
- Frontend order flow currently runs local UI state only.

### Target
- `POST /api/orders`
  - Request:
    ```json
    {
      "symbol": "FPT",
      "side": "BUY",
      "order_type": "LO",
      "quantity": 100,
      "price": 95.5,
      "idempotency_key": "run-20260303-fpt-buy-01",
      "mode": "dry-run|live"
    }
    ```
  - Response:
    ```json
    {
      "success": true,
      "order_id": "uuid",
      "broker_order_id": "string|null",
      "was_duplicate": false,
      "error": null
    }
    ```
- `POST /api/orders/{order_id}/cancel`
  - Response:
    ```json
    {
      "success": true,
      "order_id": "uuid",
      "status": "CANCELLED|REJECTED|PENDING"
    }
    ```
- `GET /api/orders`
  - Query: `status`, `symbol`, `limit`
  - Response:
    ```json
    {
      "orders": [],
      "count": 0
    }
    ```

## 3) Screener Contract

### Current
- `GET /api/run-screener?preset=VN30|TOP100`
  - SSE stream is simulated (mock progression + mock recommendations).

### Target
- `GET /api/run-screener?preset=VN30|TOP100&mode=dry-run|live`
  - SSE event contracts:
    - `pipeline_start`
    - `agent_start`
    - `agent_progress`
    - `agent_done`
    - `pipeline_complete`
    - `error`
  - `pipeline_complete` payload must include:
    ```json
    {
      "run_id": "uuid",
      "preset": "VN30",
      "total_symbols": 30,
      "buy_count": 0,
      "sell_count": 0,
      "hold_count": 0,
      "avg_score": 0,
      "results": [
        {
          "symbol": "FPT",
          "score": 0,
          "confidence": 0,
          "action": "BUY|SELL|HOLD",
          "risk": "LOW|MEDIUM|HIGH",
          "reasoning": "string",
          "reproducibility": {
            "model": "string",
            "model_version": "string",
            "prompt_version": "string"
          }
        }
      ]
    }
    ```

## 4) Compatibility Rules
- New target endpoints must remain backward-compatible with current UI until integration is switched.
- All breaking response changes require:
  - roadmap update,
  - CVF trace entry,
  - migration note for frontend consumers.

