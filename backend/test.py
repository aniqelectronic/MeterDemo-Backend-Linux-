# parking.py
from fastapi import APIRouter, HTTPException  # FastAPI tools
from pydantic import BaseModel  # For data validation and modeling
from typing import List  # To type hint lists of objects
from enum import Enum  # For fixed choices (payment status)
from datetime import datetime  # For timestamps
import pytz  # For timezone handling (Malaysia time)

# -------------------------
# Enum for payment status
# -------------------------
class PaymentStatus(str, Enum):
    """Defines allowed payment status values."""
    yes = "yes"
    no = "no"

# -------------------------
# Data models
# -------------------------
class Parking(BaseModel):
    """
    Represents a single parking record.
    Attributes:
        parking_id: License plate or unique identifier
        time_used: Number of hours used
        payment_status: Payment status (yes/no)
        timestamp: Malaysia local time when the record was added or updated
    """
    parking_id: str
    time_used: int  # hours only
    payment_status: PaymentStatus = PaymentStatus.no  # default is "no"
    timestamp: str = None  # Malaysia timestamp

class Parkings(BaseModel):
    """
    Represents a list of Parking records.
    Useful for GET responses returning multiple parkings.
    """
    parkings: List[Parking]

# -------------------------
# In-memory "database"
# -------------------------
memory_db = {"parkings": []}  # Stores parking records temporarily in memory

# -------------------------
# Helper function
# -------------------------
def malaysia_time():
    """
    Returns the current time in Malaysia timezone as a string.
    Format: YYYY-MM-DD HH:MM:SS
    """
    tz = pytz.timezone("Asia/Kuala_Lumpur")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

# -------------------------
# Create APIRouter
# -------------------------
router = APIRouter()  # Allows us to modularize endpoints for parking

# -------------------------
# Endpoints
# -------------------------

@router.get("/parking", response_model=Parkings)
def get_parking():
    """
    GET /parking
    Returns all parking records stored in memory.
    """
    return Parkings(parkings=memory_db["parkings"])

@router.post("/parking", response_model=Parking)
def add_parking(new_parking: Parking):
    """
    POST /parking
    Adds a new parking record.
    If there is an existing unpaid record for the same parking_id, it is overwritten.
    Automatically adds Malaysia timestamp.
    """
    # Add current Malaysia timestamp
    new_parking.timestamp = malaysia_time()

    # Remove old unpaid records with the same parking_id
    memory_db["parkings"] = [
        p for p in memory_db["parkings"]
        if not (p.parking_id == new_parking.parking_id and p.payment_status == PaymentStatus.no)
    ]

    # Append the new parking record
    memory_db["parkings"].append(new_parking)
    return new_parking

@router.get("/parking/{parking_id}/time", response_model=int)
def get_time_used_by_id(parking_id: str):
    """
    GET /parking/{parking_id}/time
    Returns time_used (hours) for a specific parking_id.
    - Prioritizes unpaid records.
    - If no unpaid records exist, returns latest paid record.
    - Raises 404 if parking_id not found.
    """
    # Check unpaid records first
    for p in memory_db["parkings"]:
        if p.parking_id == parking_id and p.payment_status == PaymentStatus.no:
            return p.time_used

    # Check paid records (latest first)
    for p in reversed(memory_db["parkings"]):
        if p.parking_id == parking_id:
            return p.time_used

    # If not found, raise error
    raise HTTPException(status_code=404, detail="Parking ID not found")

@router.put("/parking/{parking_id}/payment", response_model=Parking)
def update_payment_status(parking_id: str, status: PaymentStatus):
    """
    PUT /parking/{parking_id}/payment
    Updates payment status of a specific parking_id.
    - Only updates unpaid records (payment_status="no").
    - Updates timestamp when payment is made.
    - Raises 404 if unpaid record not found.
    """
    for p in memory_db["parkings"]:
        if p.parking_id == parking_id and p.payment_status == PaymentStatus.no:
            p.payment_status = status  # Update payment status
            p.timestamp = malaysia_time()  # Update timestamp to payment time
            return p

    # If no unpaid record exists, return 404
    raise HTTPException(status_code=404, detail="Unpaid parking ID not found")
