from pydantic import BaseModel, field_validator
import json


class UserConfig(BaseModel):
    assets: list[str]
    max_risk_per_trade_pct: float
    max_daily_loss_pct: float
    max_open_positions: int
    max_exposure_pct: float
    min_risk_reward: float
    max_holding_days: int

    @field_validator("max_risk_per_trade_pct")
    @classmethod
    def check_risk_pct(cls, v):
        if not (0 < v <= 100):
            raise ValueError("max_risk_per_trade_pct must be between 0 and 100")
        return v

    @field_validator("assets")
    @classmethod
    def check_assets_not_empty(cls, v):
        if len(v) == 0:
            raise ValueError("assets list cannot be empty")
        return v


def load_config(path: str) -> UserConfig:
    with open(path) as f:
        data = json.load(f)
    return UserConfig(**data)