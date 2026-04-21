from app.models.schemas import StatementSchema, ValidationResult

def validate_statement_data(statement: StatementSchema) -> ValidationResult:
    """
    Validates the extracted statement data.
    Checks for:
    - Missing fields (bank_name, account_number, etc.)
    - Running balance consistency
    - Debit/Credit alignment (ensure they aren't both populated for one transaction)
    """
    anomalies = []

    # 1. Basic field checks
    if not statement.bank_name:
        anomalies.append("Missing bank name.")
    if not statement.account_number:
        anomalies.append("Missing account number.")
    if not statement.transactions:
        anomalies.append("No transactions extracted.")
        return ValidationResult(is_valid=False, anomalies=anomalies)

    # 2. Transaction Level Checks
    previous_balance = None
    for i, txn in enumerate(statement.transactions):
        # Debit/Credit check
        if txn.debit > 0 and txn.credit > 0:
            anomalies.append(f"Row {i+1} ({txn.date}): Both debit ({txn.debit}) and credit ({txn.credit}) are present.")

        if txn.debit == 0 and txn.credit == 0:
            anomalies.append(f"Row {i+1} ({txn.date}): Both debit and credit are zero.")

        # Balance Consistency Check
        if previous_balance is not None and txn.balance != 0:
            expected_balance = previous_balance - txn.debit + txn.credit
            # Handle float precision issues
            if abs(expected_balance - txn.balance) > 0.01:
                 anomalies.append(
                     f"Row {i+1} ({txn.date}): Balance mismatch. "
                     f"Expected {expected_balance:.2f}, got {txn.balance:.2f}"
                 )

        # Update previous balance if current is available
        if txn.balance != 0:
            previous_balance = txn.balance

    is_valid = len(anomalies) == 0
    return ValidationResult(is_valid=is_valid, anomalies=anomalies)
