-- ASOF JOIN: Khớp lệnh với giá thị trường gần nhất
-- Tìm giá thị trường gần nhất TRƯỚC hoặc TẠI thời điểm đặt lệnh
-- Complexity: O(N + M) merge-sort — vastly faster than LATERAL JOIN
-- Ref: Doc 02 §3.1

SELECT
    o.order_id,
    o.symbol,
    o.side,
    o.quantity,
    o.req_price,
    o.created_at   AS order_time,
    t.price        AS market_price_at_order,
    t.ts           AS tick_time,
    -- Slippage: chênh lệch giữa giá đặt và giá thị trường thực tế
    ABS(o.req_price - t.price) AS slippage,
    -- PnL estimation (cho lệnh SELL)
    CASE
        WHEN o.side = 'SELL'
        THEN (o.req_price - t.price) * o.quantity
        ELSE NULL
    END AS estimated_pnl
FROM orders o
ASOF JOIN ticks t
    ON  o.symbol = t.symbol        -- Match cùng mã chứng khoán
    AND o.created_at >= t.ts       -- Tick phải xảy ra TRƯỚC hoặc ĐÚNG lúc đặt lệnh
ORDER BY o.created_at DESC;
