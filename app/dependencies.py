from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from app.config import API_SECRET_KEY

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(_api_key_header)):
    """Xác thực API Key. Bỏ qua nếu API_SECRET_KEY chưa cấu hình (dev mode)."""
    if not API_SECRET_KEY:
        return True  # Dev mode — không có key cấu hình thì cho qua
    if api_key != API_SECRET_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API Key. Provide it via 'X-API-Key' header."
        )
    return True
