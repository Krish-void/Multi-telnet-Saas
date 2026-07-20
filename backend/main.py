from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes import auth, users, companies

app = FastAPI(
    title="SaaS DBMS MVP",
    description="Multi-tenant role-based database management system",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(companies.router)


@app.get("/")
def root():
    return {"message": "SaaS DBMS API is running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
