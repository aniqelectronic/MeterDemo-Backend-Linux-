from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.licenses.licenses_model import License
from app.schemas.licenses.licenses_schema import LicenseCreate, LicenseResponse

router = APIRouter(prefix="/license", tags=["License"])

# --- Helper function to detect license type & year ---
def parse_license_details(licensenum: str):
    # Extract type from string
    if "BIZ" in licensenum:
        licensetype = "Business License"
    elif "HBR" in licensenum:
        licensetype = "Entertainment / Buskers License"
    elif "IKL" in licensenum:
        licensetype = "Advertisement License"
    elif "KOM" in licensenum:
        licensetype = "Composite License"
    else:
        licensetype = "Unknown"

    # Extract year (assumes format MBPPXXXYYYYnnnnnn)
    year = int(licensenum[7:11])  

    return licensetype, year


# --- Create a new license ---
@router.post("/", response_model=LicenseResponse)
def create_license(license: LicenseCreate, db: Session = Depends(get_db)):
    licensetype, year = parse_license_details(license.licensenum)

    new_license = License(
        licensenum=license.licensenum,
        licensetype=licensetype,
        owner_id=license.owner_id,
        year=year,
        amount=license.amount,
        status=license.status
    )
    db.add(new_license)
    db.commit()
    db.refresh(new_license)
    return new_license


# --- Get all licenses ---
@router.get("/", response_model=list[LicenseResponse])
def get_licenses(db: Session = Depends(get_db)):
    return db.query(License).all()


# --- Get single license by ID ---
@router.get("/{license_id}", response_model=LicenseResponse)
def get_license(license_id: str, db: Session = Depends(get_db)):
    license_obj = db.query(License).filter(License.licensenum == license_id).first()
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
    return license_obj
