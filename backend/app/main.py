from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.services.identity import router as identity_router
from app.services.assessment import router as assessment_router
from app.modules.assessment.router import router as assessments_modular_router
from app.services.recommender import router as recommender_router
from app.services.taxonomy import router as taxonomy_router
from app.services.gap_roadmap_engine import router as roadmap_router
from app.services.llamaindex_rag_orchestrator import router as rag_governance_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    print("Starting AI CareerGuide Backend Core...")
    try:
        from sqlalchemy import text
        from app.core.database import engine, Base
        import app.models  # load models
        async with engine.begin() as conn:
            if settings.DATABASE_URL.startswith("postgresql"):
                try:
                    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                except Exception as ext_err:
                    print(f"pgvector extension check: {ext_err}")
            await conn.run_sync(Base.metadata.create_all)
        print("Database schema tables verified successfully.")
    except Exception as db_err:
        print(f"Database startup check notice (offline or uninitialized): {db_err}")
    yield
    # Shutdown tasks
    print("Shutting down AI CareerGuide Backend Core...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
    ## AI CareerGuide: Personalized Major Guidance for Vietnamese High School Students
    Backend Core REST API built on FastAPI, SQLAlchemy 2.0 Async, PostgreSQL 16 + pgvector.
    
    ### 6 Modular Services Architecture:
    1. **identity**: OWASP ASVS Level 2 Argon2id authentication, RBAC, and Personal Data Consent tracking under Law 91/2025/QH15.
    2. **assessment**: Holland RIASEC questionnaires, cognitive preference mapping, and national Z-score normalization for admission subject blocks.
    3. **recommender**: Deterministic 3-pillar hybrid compatibility scoring model (RIASEC Cosine Similarity, Z-score CDF, Cognitive trait matching).
    4. **taxonomy**: Level-IV MOET major catalog (Circular 09/2022/TT-BGDĐT), Phoenix Ho career tree, subject blocks, and skill taxonomies. (Pure Guidance Scope: strictly no tuition or geographic bias).
    5. **gap_roadmap_engine**: Cached standardized study roadmaps (write-once/read-many indexed by major_code <= 1s) with verified static fallback templates.
    6. **llamaindex_rag_orchestrator**: Dual RAG orchestration, Human-in-the-Loop staging review (STREAM_A & STREAM_B), PII sanitization, and 1536-dim vector retrieval.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register 6 Modular Service Routers under /api/v1 and /api (dual prefix for complete FE sync)
app.include_router(identity_router, prefix=settings.API_V1_STR)
app.include_router(assessment_router, prefix=settings.API_V1_STR)
app.include_router(assessments_modular_router, prefix=settings.API_V1_STR)
app.include_router(recommender_router, prefix=settings.API_V1_STR)
app.include_router(taxonomy_router, prefix=settings.API_V1_STR)
app.include_router(roadmap_router, prefix=settings.API_V1_STR)
app.include_router(rag_governance_router, prefix=settings.API_V1_STR)

# Direct /api prefix aliases for frontend apiRequest routes
if settings.API_V1_STR != "/api":
    app.include_router(identity_router, prefix="/api")
    app.include_router(assessment_router, prefix="/api")
    app.include_router(assessments_modular_router, prefix="/api")
    app.include_router(recommender_router, prefix="/api")
    app.include_router(taxonomy_router, prefix="/api")
    app.include_router(roadmap_router, prefix="/api")
    app.include_router(rag_governance_router, prefix="/api")


@app.get("/health", tags=["Health & Status"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }


@app.get("/health/db", tags=["Health & Status"])
@app.get("/api/health/db", tags=["Health & Status"])
async def db_health_check():
    from app.core.database import get_db, engine
    from sqlalchemy import text
    try:
        async for db in get_db():
            if not db:
                return {"status": "offline", "message": "Database session unavailable"}
            majors_count = (await db.execute(text("SELECT COUNT(*) FROM majors;"))).scalar()
            questions_count = (await db.execute(text("SELECT COUNT(*) FROM assessment_questions;"))).scalar()
            users_count = (await db.execute(text("SELECT COUNT(*) FROM users;"))).scalar()
            return {
                "status": "connected",
                "database_engine": engine.name,
                "majors_count": majors_count,
                "questions_count": questions_count,
                "users_count": users_count,
                "message": "Cơ sở dữ liệu đã kết nối thành công và đầy đủ dữ liệu hoạt động!"
            }
    except Exception as e:
        return {
            "status": "error",
            "detail": str(e)
        }


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to AI CareerGuide Backend API",
        "docs": "/docs",
        "health": "/health"
    }
