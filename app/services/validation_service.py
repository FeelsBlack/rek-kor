from app.models.schemas import StatementSchema, ValidationResult
import datetime

def validate_statement_data(statement: StatementSchema) -> ValidationResult:
    """
    Validates the extracted statement data.
    Checks for:
    - Missing fields (bank_name, account_number, etc.)
    - Debit/Credit alignment
    - Running balance consistency (supports both chronologically and reverse-chronologically sorted statements)
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

    # 2. Determine chronological order (ascending or descending)
    # We guess based on dates or fallback to assuming it's descending (most recent first)
    # as this is common for bank statements, but we should handle both.

    # Simple check: try to find if balance increases/decreases logically top-down or bottom-up
    # To avoid date parsing issues, we'll try to find the mathematical direction.

    # Let's check top-down first
    is_top_down_consistent = True
    previous_balance = None
    for txn in statement.transactions:
        if txn.balance != 0:
            if previous_balance is not None:
                expected = round(previous_balance - txn.debit + txn.credit, 2)
                if abs(expected - round(txn.balance, 2)) > 0.01:
                    is_top_down_consistent = False
                    break
            previous_balance = txn.balance

    # If not top-down, let's check bottom-up (reverse chronological)
    is_bottom_up_consistent = True
    previous_balance = None
    for txn in reversed(statement.transactions):
         if txn.balance != 0:
            if previous_balance is not None:
                # In reverse, current row's balance = previous row's balance - debit + credit
                # Wait, if we are going bottom-up:
                # Top row is newest. Bottom row is oldest.
                # So `previous_balance` (which is older) - debit + credit = `txn.balance` (which is newer)
                expected = round(previous_balance - txn.debit + txn.credit, 2)
                if abs(expected - round(txn.balance, 2)) > 0.01:
                    is_bottom_up_consistent = False
                    break
            previous_balance = txn.balance


    # 3. Apply the logic based on the detected order
    previous_balance = None
    transactions_to_check = statement.transactions

    # If bottom-up is consistent but top-down is not, we evaluate in reverse
    if is_bottom_up_consistent and not is_top_down_consistent:
        transactions_to_check = reversed(statement.transactions)

    for i, txn in enumerate(transactions_to_check):
        # We need the real index for the error message
        real_i = len(statement.transactions) - 1 - i if (is_bottom_up_consistent and not is_top_down_consistent) else i

        # Debit/Credit check
        if txn.debit > 0 and txn.credit > 0:
            anomalies.append(f"Row {real_i+1} ({txn.date}): Both debit ({txn.debit}) and credit ({txn.credit}) are present.")

        if txn.debit == 0 and txn.credit == 0:
             # Just a warning, some banks have 0 value rows for info, but usually anomalous
            pass

        # Balance Consistency Check
        if previous_balance is not None and txn.balance != 0:
            expected_balance = previous_balance - txn.debit + txn.credit
            if abs(expected_balance - txn.balance) > 0.01:
                 anomalies.append(
                     f"Row {real_i+1} ({txn.date}): Balance mismatch. "
                     f"Expected {expected_balance:.2f}, got {txn.balance:.2f}"
                 )

        if txn.balance != 0:
            previous_balance = txn.balance


    # Check opening and closing balances if they exist
    if statement.opening_balance != 0 and statement.closing_balance != 0 and statement.transactions:
        # Calculate expected total change
        total_debit = sum(t.debit for t in statement.transactions)
        total_credit = sum(t.credit for t in statement.transactions)
        expected_closing = statement.opening_balance - total_debit + total_credit

        if abs(expected_closing - statement.closing_balance) > 0.01:
             anomalies.append(
                 f"Statement Totals Mismatch: Opening Balance ({statement.opening_balance}) - Total Debit ({total_debit}) + Total Credit ({total_credit}) "
                 f"equals {expected_closing:.2f}, but extracted Closing Balance is {statement.closing_balance}."
             )

    is_valid = len(anomalies) == 0
    return ValidationResult(is_valid=is_valid, anomalies=anomalies)
