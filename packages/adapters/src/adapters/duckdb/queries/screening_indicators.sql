-- Screening indicators: tính toán chỉ báo kỹ thuật cơ bản cho screening
-- Sử dụng cho Screener Agent
-- Ref: Doc 04 §1.6

SELECT
    symbol,
    COUNT(*)                               AS tick_count,
    SUM(volume)                            AS total_volume,
    FIRST(price ORDER BY ts)               AS open_price,
    LAST(price ORDER BY ts)                AS close_price,
    MAX(price)                             AS high_price,
    MIN(price)                             AS low_price,
    (LAST(price ORDER BY ts) - FIRST(price ORDER BY ts))
        / NULLIF(FIRST(price ORDER BY ts), 0) * 100 AS change_pct
FROM ticks
WHERE CAST(ts AS DATE) = CURRENT_DATE
GROUP BY symbol
HAVING total_volume > 100000
ORDER BY total_volume DESC;
