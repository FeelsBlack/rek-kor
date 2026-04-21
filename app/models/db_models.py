from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.database import Base

class Statement(Base):
    __tablename__ = "statements"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    bank_name = Column(String, index=True)
    account_number = Column(String, index=True)
    account_holder = Column(String)
    statement_period = Column(String)

    transactions = relationship("Transaction", back_populates="statement", cascade="all, delete")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    statement_id = Column(Integer, ForeignKey("statements.id"))
    date = Column(String) # Storing as string initially to handle parsing issues, can refine to Date later
    description = Column(String)
    debit = Column(Float, default=0.0)
    credit = Column(Float, default=0.0)
    balance = Column(Float, default=0.0)

    statement = relationship("Statement", back_populates="transactions")

class ReconciliationReport(Base):
    __tablename__ = "reconciliation_reports"

    id = Column(Integer, primary_key=True, index=True)
    statement_id = Column(Integer, ForeignKey("statements.id"))
    report_data = Column(JSON) # Store matched/unmatched JSON
