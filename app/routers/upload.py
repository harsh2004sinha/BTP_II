from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.plan import Plan
from app.models.consumption import ConsumptionData
from app.models.user import User
from app.utils.dependencies import get_current_user
from app.utils.helpers import create_api_response, save_upload_file, validate_file_extension
from app.services.bill_parser import BillParser
from app.config import settings
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/upload",
    tags=["File Upload"]
)

# Allowed file types
ALLOWED_EXTENSIONS = ['.pdf', '.csv', '.png', '.jpg', '.jpeg']
MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10MB


@router.post(
    "/bill/{plan_id}",
    summary="Upload electricity bill for a plan"
)
async def upload_bill(
    plan_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload electricity bill (PDF or CSV).

    - Saves file to disk
    - Parses consumption data automatically
    - Stores extracted data in database
    """
    # Verify plan belongs to user
    plan = db.query(Plan).filter(
        Plan.planId == plan_id,
        Plan.userId == current_user.id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan '{plan_id}' not found"
        )

    # Validate file extension
    if not validate_file_extension(file.filename, ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: {ALLOWED_EXTENSIONS}"
        )

    try:
        # Read file content
        file_content = await file.read()

        # Check file size
        if len(file_content) > MAX_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Max size: 10MB"
            )

        # Save file to disk
        file_path = await save_upload_file(
            file_content=file_content,
            filename=file.filename,
            upload_dir=settings.UPLOAD_DIR
        )

        logger.info(f"File saved: {file_path}")

        # Update plan with file path
        plan.billFile = file_path
        db.commit()

        # Parse the bill
        parsed_records = []
        parse_errors   = []

        file_ext = os.path.splitext(file.filename)[1].lower()

        try:
            if file_ext == '.pdf':
                parsed_records = BillParser.parse_pdf(file_path)
            elif file_ext == '.csv':
                parsed_records = BillParser.parse_csv(file_path)
            else:
                parse_errors.append(
                    "Image parsing not yet supported. "
                    "Please upload PDF or CSV."
                )

        except ValueError as e:
            parse_errors.append(str(e))
            logger.warning(f"Bill parsing warning: {e}")

        # Save parsed records to DB
        saved_count = 0
        if parsed_records:
            # Remove old consumption data for this plan
            db.query(ConsumptionData).filter(
                ConsumptionData.planId == plan_id
            ).delete()

            for record in parsed_records:
                units = record.get('units')
                if units and float(units) > 0:
                    consumption = ConsumptionData(
                        planId      = plan_id,
                        date        = str(record.get('date', '')),
                        month       = record.get('month', ''),
                        year        = record.get('year'),
                        units       = float(units),
                        totalAmount = record.get('totalAmount')
                    )
                    db.add(consumption)
                    saved_count += 1

            db.commit()
            plan.status = "bill_uploaded"
            db.commit()

        return create_api_response(
            success=True,
            message=f"Bill uploaded. Extracted {saved_count} consumption record(s).",
            data={
                "planId":       plan_id,
                "fileName":     file.filename,
                "filePath":     file_path,
                "fileSize":     len(file_content),
                "recordsSaved": saved_count,
                "parsedData":   parsed_records[:5],  # Preview first 5
                "parseErrors":  parse_errors,
                "status":       plan.status
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.get(
    "/consumption/{plan_id}",
    summary="Get parsed consumption data for a plan"
)
def get_consumption(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all consumption records extracted from uploaded bill."""
    # Verify plan ownership
    plan = db.query(Plan).filter(
        Plan.planId == plan_id,
        Plan.userId == current_user.id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan '{plan_id}' not found"
        )

    records = db.query(ConsumptionData).filter(
        ConsumptionData.planId == plan_id
    ).all()

    data = []
    total_units = 0

    for r in records:
        total_units += r.units
        data.append({
            "id":          r.id,
            "date":        r.date,
            "month":       r.month,
            "year":        r.year,
            "units":       r.units,
            "totalAmount": r.totalAmount
        })

    return create_api_response(
        success=True,
        message=f"Found {len(data)} consumption record(s)",
        data={
            "planId":     plan_id,
            "records":    data,
            "total":      len(data),
            "totalUnits": round(total_units, 2),
            "avgMonthly": round(total_units / len(data), 2) if data else 0
        }
    )


@router.post(
    "/manual/{plan_id}",
    summary="Manually enter consumption data"
)
def add_manual_consumption(
    plan_id: str,
    monthly_units: float,
    pattern: str = "flat",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually enter annual consumption if no bill available.

    - **monthly_units**: Average monthly kWh usage
    - **pattern**: flat or seasonal distribution
    """
    plan = db.query(Plan).filter(
        Plan.planId == plan_id,
        Plan.userId == current_user.id
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan '{plan_id}' not found"
        )

    try:
        annual_total = monthly_units * 12
        records = BillParser.estimate_monthly_consumption(annual_total, pattern)

        # Clear old records
        db.query(ConsumptionData).filter(
            ConsumptionData.planId == plan_id
        ).delete()

        # Save new records
        for r in records:
            consumption = ConsumptionData(
                planId = plan_id,
                month  = r['month'],
                year   = r['year'],
                units  = r['units'],
                date   = r['date']
            )
            db.add(consumption)

        plan.status = "bill_uploaded"
        db.commit()

        return create_api_response(
            success=True,
            message=f"Manual consumption data saved ({len(records)} months)",
            data={
                "planId":       plan_id,
                "totalAnnual":  annual_total,
                "recordsSaved": len(records),
                "preview":      records[:3]
            }
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save consumption data: {str(e)}"
        )