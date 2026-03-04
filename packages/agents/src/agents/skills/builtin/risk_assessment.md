---
name: "risk_assessment"
description: "Comprehensive risk assessment: VaR, position sizing, stop-loss, kill switch"
---

# Risk Assessment Process

## Step 1: Kill Switch Check
- Check kill_switch_active first
- If active: STOP IMMEDIATELY, do not analyze further

## Step 2: Price Band Validation
- HOSE: ±7% from reference price
- HNX: ±10%
- UPCOM: ±15%
- The order must be within the band

## Step 3: Lot Size Check
- Quantity must be a multiple of 100
- For example: 100, 200, 500, 1000 ✓
- 150, 250 ✗

## Step 4: Position Size Limit
- Calculate order value = price × quantity
- Calculate % NAV = order value / NAV
- Limit: ≤ 20% NAV per order
- If exceeded: refuse the order

## Step 5: Buying Power (BUY orders)
- Check purchasing_power ≥ command value
- If not enough: refuse the command

## Step 6: Sellable Quantity (SELL orders)
- Check sellable_qty ≥ the quantity you want to sell
- Note T+2.5: only settled shares can be sold
- Subtract pending_sell_qty if there is a pending sell order

## Step 7: Daily Loss Limit
- Check daily_pnl < -max_daily_loss
- If exceeded: STOP trading today

## Step 8: VaR Calculation
- Historical VaR 95% with 252 days of data
- If VaR > 5% NAV: high risk warning

## Step 9: Stop-Loss & Take-Profit
- Stop-loss: -7% from entry price (equivalent to HOSE floor price)
- Take-profit: +10% from entry price
- Trailing stop: 5% from peak

## Conclude
Summary of all checks:
- All passes: APPROVED
- Any failure: REJECTED + specific reason
