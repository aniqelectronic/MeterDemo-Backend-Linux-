import uvicorn
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware


# =========================================================
# VERSION 1 CONTROLLERS
# =========================================================

from app.controllers.parking import (
    parking_controller as parking_controller_v1,
)

from app.controllers.parking import (
    transaction_parking_controller
    as transaction_parking_controller_v1,
)

from app.controllers.compound import (
    compound_controller as compound_controller_v1,
)

from app.controllers.tax import (
    tax_controller as tax_controller_v1,
)

from app.controllers.licenses import (
    licenses_controller as licenses_controller_v1,
)

from app.controllers.pegepay import (
    pegepay_controller as pegepay_controller_v1,
)

from app.controllers.sewaan import (
    sewaan_controller as sewaan_controller_v1,
)


# =========================================================
# VERSION 2 CONTROLLERS
# =========================================================

from app.controllers.v2.parking import (
    parking_controller as parking_controller_v2,
)

from app.controllers.v2.parking import (
    transaction_parking_controller
    as transaction_parking_controller_v2,
)

from app.controllers.v2.compound import (
    compound_controller as compound_controller_v2,
)

from app.controllers.v2.tax import (
    tax_controller as tax_controller_v2,
)

from app.controllers.v2.licenses import (
    licenses_controller as licenses_controller_v2,
)

from app.controllers.v2.pegepay import (
    pegepay_controller as pegepay_controller_v2,
)

from app.controllers.v2.sewaan import (
    sewaan_controller as sewaan_controller_v2,
)


# =========================================================
# DATABASE AND UTILITIES
# =========================================================

from app.db.database import Base, engine
from app.utils.sirim_time import sync_sirim_time


# =========================================================
# APPLICATION LIFESPAN
# =========================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Synchronize the backend clock with SIRIM when FastAPI starts.

    If SIRIM cannot be reached, the application will still start and
    the time utility will temporarily use the server's Malaysia time.
    """
    try:
        synchronized = sync_sirim_time(force=True)

        if synchronized:
            print(
                "[SirimTime] Initial synchronization successful."
            )
        else:
            print(
                "[SirimTime] Initial synchronization failed. "
                "Using server time as fallback."
            )

    except Exception as error:
        print(
            f"[SirimTime] Startup synchronization error: {error}. "
            "Using server time as fallback."
        )

    yield


# =========================================================
# DATABASE
# =========================================================

Base.metadata.create_all(bind=engine)


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="Terminal Integrasi Pintar API",
    description=(
        "Backend API for the Terminal Integrasi Pintar system."
    ),
    version="2.0.0",
    debug=False,
    lifespan=lifespan,
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get(
    "/health",
    tags=["System"],
)
def health_check():
    return {
        "status": "ok",
        "service": "TIP Backend",
        "api_versions": [
            "legacy",
            "v1",
            "v2",
        ],
    }


# =========================================================
# LEGACY ROUTES
# =========================================================
#
# These routes use the original V1 controllers.
#
# Examples:
# /tax/...
# /sewaan/...
# /parking/...
#
# Keep these until all old kiosks have migrated.
# =========================================================

app.include_router(
    parking_controller_v1.router
)

app.include_router(
    transaction_parking_controller_v1.router
)

app.include_router(
    compound_controller_v1.router
)

app.include_router(
    tax_controller_v1.router
)

app.include_router(
    licenses_controller_v1.router
)

app.include_router(
    pegepay_controller_v1.router
)

app.include_router(
    sewaan_controller_v1.router
)


# =========================================================
# API VERSION 1
# =========================================================
#
# Examples:
# /api/v1/tax/...
# /api/v1/sewaan/...
# /api/v1/parking/...
# =========================================================

api_v1_router = APIRouter(
    prefix="/api/v1",
)

api_v1_router.include_router(
    parking_controller_v1.router
)

api_v1_router.include_router(
    transaction_parking_controller_v1.router
)

api_v1_router.include_router(
    compound_controller_v1.router
)

api_v1_router.include_router(
    tax_controller_v1.router
)

api_v1_router.include_router(
    licenses_controller_v1.router
)

api_v1_router.include_router(
    pegepay_controller_v1.router
)

api_v1_router.include_router(
    sewaan_controller_v1.router
)

app.include_router(
    api_v1_router
)


# =========================================================
# API VERSION 2
# =========================================================
#
# These routes use the separate controllers under:
#
# app/controllers/v2/
#
# Examples:
# /api/v2/tax/...
# /api/v2/sewaan/...
# /api/v2/parking/...
# =========================================================

api_v2_router = APIRouter(
    prefix="/api/v2",
)

api_v2_router.include_router(
    parking_controller_v2.router
)

api_v2_router.include_router(
    transaction_parking_controller_v2.router
)

api_v2_router.include_router(
    compound_controller_v2.router
)

api_v2_router.include_router(
    tax_controller_v2.router
)

api_v2_router.include_router(
    licenses_controller_v2.router
)

api_v2_router.include_router(
    pegepay_controller_v2.router
)

api_v2_router.include_router(
    sewaan_controller_v2.router
)

app.include_router(
    api_v2_router
)


# =========================================================
# LOCAL DEVELOPMENT
# =========================================================

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )