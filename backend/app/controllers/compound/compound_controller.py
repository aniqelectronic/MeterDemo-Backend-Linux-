from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.compound.compound_models import Compound
from app.schemas.compound.compound_schema import CompoundCreate, CompoundResponse

router = APIRouter(prefix="/compound", tags=["Compound"])

# --- Create compound ---

   
  # this is how to post data (for dummy test only)
  # {
   #  "compoundnum": "MBMBCMP2025000123",
   #  "plate": "ABC1234",
   # "date": "2025-09-22",
   #  "time": "15:45:00",
   #  "offense": "Illegal Parking",
   #  "amount": 50.0
 #   }
   
   
@router.post("/", response_model=CompoundResponse)
def create_compound(compound: CompoundCreate, db: Session = Depends(get_db)):
    new_compound = Compound(**compound.dict())
    db.add(new_compound)
    db.commit()
    db.refresh(new_compound)
    return new_compound

# --- Get all compounds ---
@router.get("/", response_model=list[CompoundResponse])
def get_compounds(db: Session = Depends(get_db)):
    return db.query(Compound).all()