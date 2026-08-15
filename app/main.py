# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, profile, admin, assets, reports, reviews, dashboard, leaderboard, monitoring, notifications, point_rules
from app.database import engine, Base
from app.config import Config 

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Bug Report Management System API",
    description="API for Bug Bounty Platform with MinIO storage",
    version="1.0.0",
    docs_url=None,      
    redoc_url=None,      
    openapi_url=None     
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.ALLOWED_ORIGINS,  
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
app.include_router(point_rules.router)

@app.get("/")
async def root():
    return {
        "message": "Bug Report Management System API",
        "version": "1.0.0"
    }

# 
# @app.get("/health")
# async def health_check():
#     return {"status": "healthy"}