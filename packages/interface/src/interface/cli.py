from __future__ import annotations

import uvicorn


def main() -> None:
    """Launch the AlgoTrading API server."""
    uvicorn.run(
        "interface.app:app",
        host="0.0.0.0",  # noqa: S104
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
