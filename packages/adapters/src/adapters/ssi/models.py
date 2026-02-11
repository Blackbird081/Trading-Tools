from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class SSITickMessage(BaseModel):
    """Raw tick message from SSI WebSocket."""

    symbol: str = Field(alias="Symbol")
    price: Decimal = Field(alias="LastPrice")
    volume: int = Field(alias="LastVol")
    exchange: str = Field(alias="Exchange")
    timestamp: str = Field(alias="TradingDate")

    model_config = {"populate_by_name": True}


class SSIAuthResponse(BaseModel):
    """SSI authentication API response."""

    status: int
    message: str = ""
    data: SSIAuthData | None = None


class SSIAuthData(BaseModel):
    access_token: str = Field(alias="accessToken")
    expires_in: int = Field(default=1800, alias="expiresIn")

    model_config = {"populate_by_name": True}


class SSIOrderResponse(BaseModel):
    """SSI order placement API response."""

    status: int
    message: str = ""
    data: dict[str, object] | None = None
