from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.tax.tax_model import CukaiTaksiran, Owner, TaxPaymentRequest
from app.schema.tax.tax_schema import TaxCreate, TaxResponse

router = APIRouter(prefix="/tax", tags=["Cukai Taksiran"])

# --- Create new tax record ---
@router.post("/", response_model=TaxResponse)
def create_tax(tax: TaxCreate, db: Session = Depends(get_db)):
    new_tax = CukaiTaksiran(**tax.dict())
    db.add(new_tax)
    db.commit()
    db.refresh(new_tax)
    return new_tax


# --- Get all taxes ---
@router.get("/", response_model=list[TaxResponse])
def get_taxes(db: Session = Depends(get_db)):
    return db.query(CukaiTaksiran).all()


# --- Get single tax by bill_no ---
@router.get("/{bill_no}", response_model=TaxResponse)
def get_tax(bill_no: str, db: Session = Depends(get_db)):
    tax = db.query(CukaiTaksiran).filter(CukaiTaksiran.bill_no == bill_no).first()
    if not tax:
        raise HTTPException(status_code=404, detail="Tax not found")
    return tax

# -----------------------------
# Get taxes by owner IC
# -----------------------------
@router.get("/by-ic/{ic}", response_model=list[TaxResponse])
def get_taxes_by_ic(ic: str, db: Session = Depends(get_db)):
    # Find owner by IC
    owner = db.query(Owner).filter(Owner.ic == ic).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    # Get all taxes linked to this owner
    taxes = db.query(CukaiTaksiran).filter(CukaiTaksiran.owner_id == owner.id).all()
    
    if not taxes:
        raise HTTPException(status_code=404, detail="No taxes found for this owner")
    
    return taxes


@router.post("/pay", response_model=list[TaxResponse])
def pay_taxes(payment_request: TaxPaymentRequest, db: Session = Depends(get_db)):
    updated_taxes = []

    for item in payment_request.payments:
        tax = db.query(CukaiTaksiran).filter(CukaiTaksiran.bill_no == item.bill_no).first()
        if not tax:
            raise HTTPException(status_code=404, detail=f"Tax bill {item.bill_no} not found")
        
        # Update payment fields
        tax.status = "paid"
        tax.paid_amount = item.paid_amount
        tax.payment_ref = item.payment_ref
        tax.paid_date = payment_request.paid_date or datetime.utcnow()

        db.add(tax)
        updated_taxes.append(tax)

    db.commit()

    # Refresh each tax to get latest data
    for tax in updated_taxes:
        db.refresh(tax)

    return updated_taxes