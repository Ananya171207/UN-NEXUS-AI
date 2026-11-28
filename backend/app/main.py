from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import configure_logging, settings
from app.routes import ai, comparison, countries, country_events, country_sdg, events, situation

configure_logging()

app = FastAPI(
    title="UN NEXUS AI",
    description="Global Intelligence and Sustainable Development Platform",
    version="1.0.0"
)

# Lets the React dev server (http://localhost:5173) call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Data-Warnings", "X-Data-Status"],
)

app.include_router(
    countries.router,
    prefix="/api",
    tags=["Global Situation Room"]
)

app.include_router(
    country_events.router,
    prefix="/api",
    tags=["Global Situation Room"]
)

app.include_router(
    country_sdg.router,
    prefix="/api",
    tags=["Global Situation Room"]
)

app.include_router(
    comparison.router,
    prefix="/api",
    tags=["India vs World"]
)

app.include_router(
    situation.router,
    prefix="/api",
    tags=["Global Situation Room"]
)

app.include_router(
    ai.router,
    prefix="/api",
    tags=["AI Intelligence"]
)

app.include_router(
    events.router,
    prefix="/api",
    tags=["Global Situation Room"]
)

@app.get("/")
def home():
    return {
        "message": "Welcome to UN NEXUS AI!",
        "status": "Backend is running"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
