from fastapi import APIRouter, Depends , HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schema.tax.tax_schema import Tax
from app.models.tax.tax_model import TaxCreate, TaxResponse

router = APIRouter(prefix="/tax", tags=["Tax"])

# --- Create new tax record ---
@router.post("/", response_model=TaxResponse)
def create_tax(tax: TaxCreate, db: Session = Depends(get_db)):
    new_tax = Tax(**tax.dict())
    db.add(new_tax)
    db.commit()
    db.refresh(new_tax)
    return new_tax

# --- Get all taxes ---
@router.get("/", response_model=list[TaxResponse])
def get_taxes(db: Session = Depends(get_db)):
    return db.query(Tax).all()

# ✅ Get single tax by ID
@router.get("/{tax_id}", response_model=TaxResponse)
def get_tax(tax_id: str, db: Session = Depends(get_db)):
    tax = db.query(Tax).filter(Tax.taxnum == tax_id).first()
    if not tax:
        raise HTTPException(status_code=404, detail="Tax not found")
    return tax