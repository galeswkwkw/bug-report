from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, profile, admin, assets, reports, reviews, dashboard, leaderboard, monitoring, notifications
from app.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Bug Report Management System API",
    description="API for Bug Bounty Platform with MinIO storage",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",           # React/Vite
        "http://localhost:3000",           # React
        "http://localhost:8080",           # Vue
        "https://bugbounty.sprintasia.net", # Production FE
        "https://api-bugbounty.sprintasia.net", # API domain (opsional)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin"],
    expose_headers=["Content-Disposition"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(admin.router)
app.include_router(assets.router)
app.include_router(reports.router)
app.include_router(reviews.router)
app.include_router(dashboard.router)
app.include_router(leaderboard.router)
app.include_router(monitoring.router)
app.include_router(notifications.router)

@app.get("/")
async def root():
    return {
        "message": "Bug Report Management System API",
        "docs": "/docs",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}