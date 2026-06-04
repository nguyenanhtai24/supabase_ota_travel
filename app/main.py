import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.dependencies import verify_api_key
from app.routers import system, hotels, rooms, places, activities, combo

app = FastAPI(
    title="OTA Travel Assistant API",
    description=(
        "FastAPI Backend kết nối Supabase PostgreSQL cho hệ thống OTA du lịch.\n\n"
        "**Xác thực:** Tất cả endpoint (trừ `/health`) yêu cầu header `X-API-Key: <token>`."
    ),
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các router
app.include_router(system.router)
app.include_router(combo.router, dependencies=[Depends(verify_api_key)])
app.include_router(hotels.router, dependencies=[Depends(verify_api_key)])
app.include_router(rooms.router, dependencies=[Depends(verify_api_key)])
app.include_router(places.router, dependencies=[Depends(verify_api_key)])
app.include_router(activities.router, dependencies=[Depends(verify_api_key)])

if __name__ == "__main__":
    import uvicorn
    from app.config import PORT
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)
