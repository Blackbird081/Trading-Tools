-- Historical VaR: tính Value at Risk dựa trên dữ liệu lịch sử
-- Sử dụng phương pháp Historical Simulation
-- Ref: Doc 02 §3.1

WITH daily_returns AS (
    SELECT
        symbol,
        DATE_TRUNC('day', ts)  AS trading_date,
        LAST(price ORDER BY ts) AS close_price,
        LAG(LAST(price ORDER BY ts)) OVER (
            PARTITION BY symbol ORDER BY DATE_TRUNC('day', ts)
        ) AS prev_close,
        (LAST(price ORDER BY ts) - LAG(LAST(price ORDER BY ts)) OVER (
            PARTITION BY symbol ORDER BY DATE_TRUNC('day', ts)
        )) / NULLIF(LAG(LAST(price ORDER BY ts)) OVER (
            PARTITION BY symbol ORDER BY DATE_TRUNC('day', ts)
        ), 0) AS daily_return
    FROM ticks
    GROUP BY symbol, DATE_TRUNC('day', ts)
),
portfolio_returns AS (
    SELECT
        trading_date,
        SUM(daily_return) AS portfolio_return  -- Simplified equal-weight
    FROM daily_returns
    WHERE daily_return IS NOT NULL
    GROUP BY trading_date
)
SELECT
    PERCENTILE_CONT(0.05) WITHIN GROUP (ORDER BY portfolio_return) AS var_95,
    PERCENTILE_CONT(0.01) WITHIN GROUP (ORDER BY portfolio_return) AS var_99,
    COUNT(*) AS sample_size
FROM portfolio_returns;
