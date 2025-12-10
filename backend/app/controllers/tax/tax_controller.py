from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.tax.tax_model import OwnerCreate, PropertyCreate, TaxCreate, TaxResponse
from app.schema.tax.tax_schema import CukaiTaksiran, Owner, Property 

router = APIRouter(prefix="/tax", tags=["Cukai Taksiran"])

# --- Create new owner ---
@router.post("/owner", response_model=OwnerCreate)
def create_owner(owner: OwnerCreate, db: Session = Depends(get_db)):
    new_owner = Owner(**owner.dict())
    db.add(new_owner)
    db.commit()
    db.refresh(new_owner)
    return new_owner

# --- Create new property ---
@router.post("/property", response_model=PropertyCreate)
def create_property(prop: PropertyCreate, db: Session = Depends(get_db)):
    new_prop = Property(**prop.dict())
    db.add(new_prop)
    db.commit()
    db.refresh(new_prop)
    return new_prop

# --- Create multiple taxes ---
@router.post("/", response_model=List[TaxResponse])
def create_multiple_taxes(taxes: List[TaxCreate], db: Session = Depends(get_db)):
    created_taxes = []
    for tax in taxes:
        # Fetch owner to set correct owner_name
        owner = db.query(Owner).filter(Owner.id == tax.owner_id).first()
        if not owner:
            raise HTTPException(status_code=404, detail=f"Owner ID {tax.owner_id} not found")

        tax_data = tax.dict()
        tax_data['owner_name'] = owner.name

        new_tax = CukaiTaksiran(**tax_data)

        # Adjust issue_date and due_date to Malaysia time (UTC+8)
        if new_tax.issue_date:
            new_tax.issue_date += timedelta(hours=8)
        if new_tax.due_date:
            new_tax.due_date += timedelta(hours=8)

        db.add(new_tax)
        db.commit()
        db.refresh(new_tax)
        created_taxes.append(new_tax)
    return created_taxes

# --- Get all taxes ---
@router.get("/", response_model=List[TaxResponse])
def get_taxes(db: Session = Depends(get_db)):
    return db.query(CukaiTaksiran).all()

# --- Get single tax by bill_no ---
@router.get("/{bill_no}", response_model=TaxResponse)
def get_tax(bill_no: str, db: Session = Depends(get_db)):
    tax = db.query(CukaiTaksiran).filter(CukaiTaksiran.bill_no == bill_no).first()
    if not tax:
        raise HTTPException(status_code=404, detail="Tax not found")

    # Dynamically add property_type
    result = tax.__dict__
    result['property_type'] = tax.property.property_type
    return result


# --- Get taxes by owner IC ---
@router.get("/by-ic/{ic}", response_model=List[TaxResponse])
def get_taxes_by_ic(ic: str, db: Session = Depends(get_db)):
    owner = db.query(Owner).filter(Owner.ic == ic).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    taxes = db.query(CukaiTaksiran).filter(CukaiTaksiran.owner_id == owner.id).all()
    if not taxes:
        raise HTTPException(status_code=404, detail="No taxes found for this owner")
    
    return taxes

# --- Renew tax by extending due_date or creating new record ---
@router.post("/renew/{bill_no}", response_model=TaxResponse)
def renew_tax(bill_no: str, db: Session = Depends(get_db), extra_days: int = 180):
    tax = db.query(CukaiTaksiran).filter(CukaiTaksiran.bill_no == bill_no).first()
    if not tax:
        raise HTTPException(status_code=404, detail="Tax bill not found")
    
    # Extend the due_date by extra_days (default 180 days = 6 months)
    tax.due_date += timedelta(days=extra_days)

    db.add(tax)
    db.commit()
    db.refresh(tax)
    return tax
