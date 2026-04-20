import pandas as pd
from typing import List, Dict
from app.models.schemas import StatementSchema, ReconciliationResult

def reconcile_with_erp(statement_data: StatementSchema, erp_data: List[Dict]) -> ReconciliationResult:
    """
    Matches bank statement transactions with ERP AP data.
    Matching criteria:
    1. Amount (exact or within tolerance)
    2. Date window (+/- 3 days)
    3. (Optional/Future) Description similarity
    """

    # Convert to DataFrames for easier matching
    df_bank = pd.DataFrame([t.dict() for t in statement_data.transactions])
    df_erp = pd.DataFrame(erp_data)

    matched = []
    unmatched_bank = []
    suspected_duplicates = []

    # Track used ERP indices to find unmatched ERP entries
    used_erp_indices = set()

    if df_bank.empty or df_erp.empty:
        return ReconciliationResult(
            matched=[],
            unmatched_statement=df_bank.to_dict('records') if not df_bank.empty else [],
            unmatched_erp=df_erp.to_dict('records') if not df_erp.empty else [],
            suspected_duplicates=[]
        )

    # Basic Date parsing (assuming YYYY-MM-DD or similar standard format from LLM)
    df_bank['parsed_date'] = pd.to_datetime(df_bank['date'], errors='coerce')
    if 'date' in df_erp.columns:
        df_erp['parsed_date'] = pd.to_datetime(df_erp['date'], errors='coerce')
    else:
        df_erp['parsed_date'] = pd.NaT

    for bank_idx, bank_row in df_bank.iterrows():
        # Match primarily on Debit (Payments out)
        amount_to_match = bank_row['debit']
        if amount_to_match == 0:
            # If it's a credit, we might not reconcile it against AP (Accounts Payable), but maybe AR.
            # For this exercise, we will just add it to unmatched or handle if needed.
            unmatched_bank.append(bank_row.to_dict())
            continue

        bank_date = bank_row['parsed_date']

        # 1. Filter ERP by amount (exact match for now)
        potential_matches = df_erp[df_erp['amount'] == amount_to_match]

        # 2. Filter by date window (+/- 3 days)
        if not pd.isna(bank_date):
            date_window = pd.Timedelta(days=3)
            potential_matches = potential_matches[
                (potential_matches['parsed_date'] >= bank_date - date_window) &
                (potential_matches['parsed_date'] <= bank_date + date_window)
            ]

        # Check results
        if len(potential_matches) == 1:
            erp_idx = potential_matches.index[0]
            if erp_idx in used_erp_indices:
                suspected_duplicates.append({
                    "bank_transaction": bank_row.to_dict(),
                    "erp_transaction": df_erp.loc[erp_idx].to_dict()
                })
            else:
                matched.append({
                    "bank_transaction": bank_row.to_dict(),
                    "erp_transaction": df_erp.loc[erp_idx].to_dict()
                })
                used_erp_indices.add(erp_idx)

        elif len(potential_matches) > 1:
             # Multiple matches found - suspected duplicates or need manual review
             for idx, row in potential_matches.iterrows():
                 suspected_duplicates.append({
                    "bank_transaction": bank_row.to_dict(),
                    "erp_transaction": row.to_dict()
                 })
        else:
            # No matches found
            unmatched_bank.append(bank_row.to_dict())

    # Find unmatched ERP
    unmatched_erp_indices = set(df_erp.index) - used_erp_indices
    unmatched_erp = df_erp.loc[list(unmatched_erp_indices)].to_dict('records')

    # Cleanup parsed dates before returning
    for m in matched:
        m['bank_transaction'].pop('parsed_date', None)
        m['erp_transaction'].pop('parsed_date', None)
    for u in unmatched_bank:
        u.pop('parsed_date', None)
    for u in unmatched_erp:
        u.pop('parsed_date', None)
    for d in suspected_duplicates:
        d['bank_transaction'].pop('parsed_date', None)
        d['erp_transaction'].pop('parsed_date', None)


    return ReconciliationResult(
        matched=matched,
        unmatched_statement=unmatched_bank,
        unmatched_erp=unmatched_erp,
        suspected_duplicates=suspected_duplicates
    )
