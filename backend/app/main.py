from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat_router, festivals_router, health_router, places_router, posts_router, travel_test_router
from app.core.config import load_settings
from app.core.exceptions import register_exception_handlers
from app.db.base import Base
from app.db.session import create_db_engine, create_session_factory


def create_app() -> FastAPI:
    settings = load_settings()
    engine = create_db_engine(str(settings["database_url"]))
    session_factory = create_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Base.metadata.create_all(bind=engine)
        app.state.engine = engine
        app.state.session_factory = session_factory
        yield

    app = FastAPI(title="LocalHub API", version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings["cors_origins"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health_router, prefix="/api")
    app.include_router(posts_router, prefix="/api")
    app.include_router(places_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    app.include_router(travel_test_router, prefix="/api")
    app.include_router(festivals_router, prefix="/api")
    return app


app = create_app()
