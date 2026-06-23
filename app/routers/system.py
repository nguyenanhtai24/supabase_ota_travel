from fastapi import APIRouter, Response

router = APIRouter()

@router.api_route("/health", methods=["GET", "HEAD"], tags=["System"])
def health_check():
    return Response(status_code=200)
