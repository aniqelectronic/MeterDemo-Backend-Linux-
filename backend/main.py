import uvicorn
import time
import psutil
import os

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.security.hmac_auth import (
    require_api_key_and_hmac,
)

# =========================================================
# VERSION 1 CONTROLLERS
# =========================================================

# from app.controllers.parking import (
#     parking_controller as parking_controller_v1,
# )

# from app.controllers.parking import (
#     transaction_parking_controller
#     as transaction_parking_controller_v1,
# )

# from app.controllers.compound import (
#     compound_controller as compound_controller_v1,
# )

# from app.controllers.tax import (
#     tax_controller as tax_controller_v1,
# )

# from app.controllers.licenses import (
#     licenses_controller as licenses_controller_v1,
# )

# from app.controllers.pegepay import (
#     pegepay_controller as pegepay_controller_v1,
# )

# from app.controllers.sewaan import (
#     sewaan_controller as sewaan_controller_v1,
# )


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

from app.controllers.v2.bill import (
    bill_receipt_route,
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

    # Browser websites permitted to call this API.
    allow_origins=[
        "https://tipintar.juaraipasifik.com",
    ],

    # Keep False unless browser authentication uses cookies.
    allow_credentials=False,

    # Current and possible future API methods.
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "OPTIONS",
        "HEAD",
    ],

    # Request headers accepted from browser applications.
    allow_headers=[
        "Accept",
        "Content-Type",
        "Authorization",
        "X-API-Key",
        "X-Timestamp",
        "X-Nonce",
        "X-Signature",
        "Idempotency-Key",
        "X-Request-ID",
    ],

    # Optional response headers that browser JavaScript
    # is permitted to read.
    expose_headers=[
        "X-Request-ID",
    ],

    # Browser may cache the preflight result for 1 hour.
    max_age=3600,
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
            # "v1",
            "v2",
        ],
    }

# =========================================================
# SYSTEM RESOURCE HEALTH
# =========================================================

@app.get(
    "/system-health",
    tags=["System"],
)
def system_health():
    """
    Return current Azure VM resource utilization.

    This endpoint reports:
    - CPU usage
    - memory usage
    - swap usage
    - disk usage
    - Linux load average
    - system uptime
    """

    cpu_percent = psutil.cpu_percent(interval=0.2)
    cpu_logical_count = psutil.cpu_count(logical=True)
    cpu_physical_count = psutil.cpu_count(logical=False)

    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage("/")

    load_1, load_5, load_15 = os.getloadavg()

    boot_time = psutil.boot_time()
    uptime_seconds = int(time.time() - boot_time)

    uptime_days = uptime_seconds // 86400
    uptime_hours = (uptime_seconds % 86400) // 3600
    uptime_minutes = (uptime_seconds % 3600) // 60

    status = "healthy"
    warnings = []

    if cpu_percent >= 90:
        status = "critical"
        warnings.append("CPU usage is critically high.")
    elif cpu_percent >= 75:
        status = "warning"
        warnings.append("CPU usage is high.")

    if memory.percent >= 90:
        status = "critical"
        warnings.append("Memory usage is critically high.")
    elif memory.percent >= 80:
        if status != "critical":
            status = "warning"
        warnings.append("Memory usage is high.")

    if disk.percent >= 90:
        status = "critical"
        warnings.append("Disk usage is critically high.")
    elif disk.percent >= 80:
        if status != "critical":
            status = "warning"
        warnings.append("Disk usage is high.")

    logical_cores = cpu_logical_count or 1

    normalized_load_1 = round(
        load_1 / logical_cores,
        2,
    )

    if normalized_load_1 >= 1.5:
        status = "critical"
        warnings.append(
            "Server load average is critically high."
        )
    elif normalized_load_1 >= 1.0:
        if status != "critical":
            status = "warning"
        warnings.append(
            "Server load average is high."
        )

    return {
        "status": status,
        "service": "TIP Azure Server",
        "checked_at": time.strftime(
            "%Y-%m-%d %H:%M:%S",
            time.localtime(),
        ),
        "cpu": {
            "usage_percent": round(cpu_percent, 2),
            "physical_cores": cpu_physical_count,
            "logical_cores": cpu_logical_count,
        },
        "memory": {
            "usage_percent": round(memory.percent, 2),
            "used_gb": round(
                memory.used / (1024 ** 3),
                2,
            ),
            "available_gb": round(
                memory.available / (1024 ** 3),
                2,
            ),
            "total_gb": round(
                memory.total / (1024 ** 3),
                2,
            ),
        },
        "swap": {
            "usage_percent": round(swap.percent, 2),
            "used_gb": round(
                swap.used / (1024 ** 3),
                2,
            ),
            "total_gb": round(
                swap.total / (1024 ** 3),
                2,
            ),
        },
        "disk": {
            "usage_percent": round(disk.percent, 2),
            "used_gb": round(
                disk.used / (1024 ** 3),
                2,
            ),
            "free_gb": round(
                disk.free / (1024 ** 3),
                2,
            ),
            "total_gb": round(
                disk.total / (1024 ** 3),
                2,
            ),
        },
        "load_average": {
            "one_minute": round(load_1, 2),
            "five_minutes": round(load_5, 2),
            "fifteen_minutes": round(load_15, 2),
            "normalized_one_minute": normalized_load_1,
        },
        "uptime": {
            "seconds": uptime_seconds,
            "display": (
                f"{uptime_days} days, "
                f"{uptime_hours} hours, "
                f"{uptime_minutes} minutes"
            ),
        },
        "warnings": warnings,
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

# app.include_router(
#     parking_controller_v1.router
# )

# app.include_router(
#     transaction_parking_controller_v1.router
# )

# app.include_router(
#     compound_controller_v1.router
# )

# app.include_router(
#     tax_controller_v1.router
# )

# app.include_router(
#     licenses_controller_v1.router
# )

# app.include_router(
#     pegepay_controller_v1.router
# )

# app.include_router(
#     sewaan_controller_v1.router
# )


# =========================================================
# API VERSION 1
# =========================================================
#
# Examples:
# /api/v1/tax/...
# /api/v1/sewaan/...
# /api/v1/parking/...
# =========================================================

# api_v1_router = APIRouter(
#     prefix="/api/v1",
# )

# api_v1_router.include_router(
#     parking_controller_v1.router
# )

# api_v1_router.include_router(
#     transaction_parking_controller_v1.router
# )

# api_v1_router.include_router(
#     compound_controller_v1.router
# )

# api_v1_router.include_router(
#     tax_controller_v1.router
# )

# api_v1_router.include_router(
#     licenses_controller_v1.router
# )

# api_v1_router.include_router(
#     pegepay_controller_v1.router
# )

# api_v1_router.include_router(
#     sewaan_controller_v1.router
# )

# app.include_router(
#     api_v1_router
# )


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
    dependencies=[
        Depends(require_api_key_and_hmac),
    ],
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

api_v2_router.include_router(
    bill_receipt_route.router
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