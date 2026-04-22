from pydantic import BaseModel, Field
from typing import List, Optional, Any

class TransactionSchema(BaseModel):
    date: str = Field(description="Date of the transaction")
    time: str = Field(default="", description="Time of the transaction if available (e.g., '14:30:00' or '')")
    description: str = Field(description="Description or details of the transaction")
    debit: float = Field(default=0.0, description="Amount withdrawn or debited")
    credit: float = Field(default=0.0, description="Amount deposited or credited")
    balance: float = Field(default=0.0, description="Running balance after the transaction")

class StatementSchema(BaseModel):
    bank_name: str = Field(description="Name of the bank")
    account_number: str = Field(description="Account number")
    account_holder: str = Field(description="Name of the account holder")
    statement_period: str = Field(description="Period the statement covers (e.g., 'Jan 1 - Jan 31, 2023')")
    opening_balance: float = Field(default=0.0, description="Opening balance of the statement period")
    closing_balance: float = Field(default=0.0, description="Closing balance of the statement period")
    total_debit_amount: float = Field(default=0.0, description="Total amount of all debits")
    total_credit_amount: float = Field(default=0.0, description="Total amount of all credits")
    debit_transaction_count: int = Field(default=0, description="Number of debit transactions")
    credit_transaction_count: int = Field(default=0, description="Number of credit transactions")
    transactions: List[TransactionSchema]

class ValidationResult(BaseModel):
    is_valid: bool
    anomalies: List[str]

class ReconciliationRequest(BaseModel):
    statement_id: int
    erp_data: List[dict] # Represents ERP AP data passed from client for matching

class ReconciliationResult(BaseModel):
    matched: List[dict]
    unmatched_statement: List[dict]
    unmatched_erp: List[dict]
    suspected_duplicates: List[dict]
