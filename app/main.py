from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, profile, admin
from app.database import engine, Base
from app.routes import auth, profile, admin, assets, reports, reviews, dashboard,leaderboard

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Bug Report Management System API",
    description="API for Bug Bounty Platform with MinIO storage",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(admin.router)
app.include_router(assets.router)
app.include_router(reports.router)
app.include_router(reviews.router) 
app.include_router(dashboard.router) 
app.include_router(leaderboard.router)

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

