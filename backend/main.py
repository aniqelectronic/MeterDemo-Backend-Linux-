import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers.parking import parking_controller
from app.controllers.parking import transaction_parking_controller
from app.controllers.compound import compound_controller
from app.controllers.tax import tax_controller
from app.controllers.licenses import licenses_controller
from app.controllers.pegepay import pegepay_controller
from app.controllers.sewaan import sewaan_controller

from app.db.database import Base, engine
from app.utils.sirim_time import sync_sirim_time


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
            print("[SirimTime] Initial synchronization successful.")
        else:
            print(
                "[SirimTime] Initial synchronization failed. "
                "Using server time as fallback."
            )

    except Exception as error:
        # Do not stop the backend if SIRIM synchronization fails.
        print(
            f"[SirimTime] Startup synchronization error: {error}. "
            "Using server time as fallback."
        )

    yield


Base.metadata.create_all(bind=engine)  # recreate with new columns

app = FastAPI(
    debug=True,
    lifespan=lifespan,
)

origins = [
    "http://localhost:3000",        # local development frontend
    "http://4.194.122.32",          # VM backend
    "http://4.194.122.32:3000",     # optional frontend hosted on same VM
    "*",                            # allow IoT or external testing
]

app.add_middleware(
    CORSMiddleware,
    # allow_origins=origins,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(parking_controller.router)
app.include_router(transaction_parking_controller.router)
app.include_router(compound_controller.router)
app.include_router(tax_controller.router)
app.include_router(licenses_controller.router)
app.include_router(pegepay_controller.router)
app.include_router(sewaan_controller.router)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )
