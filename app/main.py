from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import endpoints
from app.db.database import engine, Base
import app.models.db_models # Important: import models before creating tables

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Finance RPA App", description="API for extracting and reconciling bank statements")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(endpoints.router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Finance RPA API"}
