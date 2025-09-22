import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.controllers.parking import parking_controller
from app.db.database import Base, engine
from app.controllers.parking import transaction_parking_controller 
from app.controllers.compound import compound_controller


Base.metadata.create_all(bind=engine) # recreate with new columns
app = FastAPI(debug=True)

# Allow frontend to access API
origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Include API routes
app.include_router(parking_controller.router)
app.include_router(transaction_parking_controller.router)
app.include_router(compound_controller.router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
