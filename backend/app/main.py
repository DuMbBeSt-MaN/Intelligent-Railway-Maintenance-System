from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

app = FastAPI(
    title="RailGuard Optimizer API",
    version="0.1.0",
    description="Proof-of-concept railway maintenance scheduling backend using OR-Tools CP-SAT.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
def root():
    return {
        "name": "RailGuard Optimizer API",
        "docs": "/docs",
        "health": "/api/health",
    }
