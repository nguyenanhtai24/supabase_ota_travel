from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["System"])
def health_check():
    """Kiểm tra trạng thái server. Không cần API Key."""
    return {
        "status": "OK",
        "version": "2.0.0",
        "message": "OTA Travel Assistant API đang hoạt động bình thường."
    }
