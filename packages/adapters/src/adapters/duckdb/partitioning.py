"""Parquet partition manager — Hive-style partitioned Parquet writes.

★ Uses DuckDB's native COPY with PARTITION_BY for zero-copy export.
★ Partition pruning: queries only read relevant partitions.

Ref: Doc 02 §3.2
"""

from __future__ import annotations

from pathlib import Path

import duckdb


class ParquetPartitionManager:
    """Manages Hive-style partitioned Parquet writes."""

    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        base_path: Path,
    ) -> None:
        self._conn = conn
        self._base_path = base_path

    def flush_ticks_to_parquet(self) -> int:
        """Export today's buffered ticks to partitioned Parquet files.

        Called by Data Agent at end-of-day or periodically.
        Uses DuckDB's native COPY with PARTITION_BY for zero-copy export.

        Returns:
            Number of rows exported.
        """
        base = str(self._base_path).replace("\\", "/")
        result = self._conn.execute(f"""
            COPY (
                SELECT
                    *,
                    YEAR(ts)  AS year,
                    MONTH(ts) AS month,
                    DAY(ts)   AS day
                FROM ticks
                WHERE ts >= CURRENT_DATE
            )
            TO '{base}/ticks'
            (FORMAT PARQUET, PARTITION_BY (year, month, day),
             COMPRESSION 'zstd', ROW_GROUP_SIZE 100000)
        """)
        row = result.fetchone()
        return int(row[0]) if row else 0

    def register_parquet_view(self) -> None:
        """Register partitioned Parquet as queryable view.

        DuckDB reads only relevant partitions (partition pruning)
        when WHERE clause filters on year/month/day.
        """
        base = str(self._base_path).replace("\\", "/")
        self._conn.execute(f"""
            CREATE OR REPLACE VIEW ticks_historical AS
            SELECT * FROM read_parquet(
                '{base}/ticks/**/*.parquet',
                hive_partitioning = true
            )
        """)
