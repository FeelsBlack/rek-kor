from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
import json
from app.db.database import get_db
from app.models.db_models import Statement, Transaction, ReconciliationReport
from app.models.schemas import StatementSchema, ValidationResult, ReconciliationRequest, ReconciliationResult
from app.services.extraction_service import process_document
from app.services.validation_service import validate_statement_data
from app.services.reconciliation_service import reconcile_with_erp

router = APIRouter()

@router.post("/process-document", response_model=StatementSchema)
def upload_and_process(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Uploads a bank statement (PDF/Image), extracts data using Gemini, and saves to DB."""
    try:
        contents = file.file.read()
        extracted_data = process_document(contents, file.filename)

        # Fallback calculation for summaries if Gemini fails to extract them
        if extracted_data.transactions:
            if extracted_data.total_debit_amount == 0.0:
                extracted_data.total_debit_amount = sum(t.debit for t in extracted_data.transactions)
            if extracted_data.total_credit_amount == 0.0:
                extracted_data.total_credit_amount = sum(t.credit for t in extracted_data.transactions)
            if extracted_data.debit_transaction_count == 0:
                extracted_data.debit_transaction_count = sum(1 for t in extracted_data.transactions if t.debit > 0)
            if extracted_data.credit_transaction_count == 0:
                extracted_data.credit_transaction_count = sum(1 for t in extracted_data.transactions if t.credit > 0)

        # Save to database
        db_statement = Statement(
            filename=file.filename,
            bank_name=extracted_data.bank_name,
            account_number=extracted_data.account_number,
            account_holder=extracted_data.account_holder,
            statement_period=extracted_data.statement_period,
            opening_balance=extracted_data.opening_balance,
            closing_balance=extracted_data.closing_balance,
            total_debit_amount=extracted_data.total_debit_amount,
            total_credit_amount=extracted_data.total_credit_amount,
            debit_transaction_count=extracted_data.debit_transaction_count,
            credit_transaction_count=extracted_data.credit_transaction_count
        )
        db.add(db_statement)
        db.flush() # get the ID

        for txn in extracted_data.transactions:
            db_txn = Transaction(
                statement_id=db_statement.id,
                date=txn.date,
                time=txn.time,
                description=txn.description,
                debit=txn.debit,
                credit=txn.credit,
                balance=txn.balance
            )
            db.add(db_txn)

        db.commit()
        db.refresh(db_statement)
        return extracted_data

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate")
def validate_extracted_data(data: StatementSchema) -> ValidationResult:
    """Validates the extracted data for consistency."""
    return validate_statement_data(data)

@router.post("/reconcile", response_model=ReconciliationResult)
def reconcile_data(request: ReconciliationRequest, db: Session = Depends(get_db)):
    """Reconciles a saved statement against provided ERP data."""
    # 1. Fetch statement from DB
    db_statement = db.query(Statement).filter(Statement.id == request.statement_id).first()
    if not db_statement:
        raise HTTPException(status_code=404, detail="Statement not found")

    # Reconstruct Schema object for processing
    transactions = [
        {
            "date": t.date,
            "time": t.time,
            "description": t.description,
            "debit": t.debit,
            "credit": t.credit,
            "balance": t.balance
        } for t in db_statement.transactions
    ]
    statement_schema = StatementSchema(
        bank_name=db_statement.bank_name,
        account_number=db_statement.account_number,
        account_holder=db_statement.account_holder,
        statement_period=db_statement.statement_period,
        opening_balance=db_statement.opening_balance,
        closing_balance=db_statement.closing_balance,
        total_debit_amount=db_statement.total_debit_amount,
        total_credit_amount=db_statement.total_credit_amount,
        debit_transaction_count=db_statement.debit_transaction_count,
        credit_transaction_count=db_statement.credit_transaction_count,
        transactions=transactions
    )

    # 2. Run Reconciliation
    result = reconcile_with_erp(statement_schema, request.erp_data)

    # 3. Save report to DB
    report = ReconciliationReport(
        statement_id=request.statement_id,
        report_data=result.dict()
    )
    db.add(report)
    db.commit()

    return result
