from fastapi import APIRouter, Depends

from ..deps import get_current_user
from ..models import User
from ..services.config_service import config_service


router = APIRouter(tags=["config"])


@router.get("/api/config/effective")
def effective_configs(_: User = Depends(get_current_user)) -> dict:
    return {
        "default_scenario": config_service.get("analysis.default_scenario", "auto"),
        "low_ctr_threshold": config_service.get_float("analysis.low_ctr_threshold", 0.035),
        "low_cvr_threshold": config_service.get_float("analysis.low_cvr_threshold", 0.025),
        "websocket_token_ttl_seconds": config_service.get_int(
            "system.websocket_token_ttl_seconds", 120
        ),
        "features": {
            "attachments": config_service.get_bool("feature.attachments", True),
            "command_tool": config_service.get_bool("feature.command_tool", True),
            "result_export": config_service.get_bool("feature.result_export", True),
        },
    }
