import streamlit as st
import requests
import pandas as pd
import os
import json

API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")

st.set_page_config(page_title="Finance RPA App", layout="wide")

st.title("Finance RPA: Statement Extraction & Reconciliation")

# Tabs
tab1, tab2, tab3 = st.tabs(["1. Extract Data", "2. Validate", "3. Reconcile"])

# Use session state to store data across tabs
if 'extracted_data' not in st.session_state:
    st.session_state['extracted_data'] = None

with tab1:
    st.header("Upload Bank Statement")
    uploaded_file = st.file_uploader("Choose a PDF or Image file", type=["pdf", "png", "jpg", "jpeg"])

    if st.button("Process Document") and uploaded_file is not None:
        with st.status("Processing document...", expanded=True) as status:
            st.write("Uploading file to server...")
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}

            st.write("Extracting data via Gemini AI (This may take 5-10 seconds)...")
            response = requests.post(f"{API_URL}/process-document", files=files)

            if response.status_code == 200:
                st.write("Saving to database...")
                st.session_state['extracted_data'] = response.json()
                status.update(label="Document processed successfully!", state="complete", expanded=False)
            else:
                status.update(label="Error processing document.", state="error", expanded=True)
                st.error(f"Error details: {response.text}")

    if st.session_state['extracted_data']:
        st.subheader("Extracted Data")
        data = st.session_state['extracted_data']

        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Bank:** {data.get('bank_name')}")
            st.write(f"**Account:** {data.get('account_number')}")
            st.write(f"**Opening Balance:** {data.get('opening_balance')}")
        with col2:
            st.write(f"**Holder:** {data.get('account_holder')}")
            st.write(f"**Period:** {data.get('statement_period')}")
            st.write(f"**Closing Balance:** {data.get('closing_balance')}")

        st.write("### Transactions")
        df_transactions = pd.DataFrame(data.get('transactions', []))
        st.dataframe(df_transactions)


with tab2:
    st.header("Validate Extracted Data")
    if st.session_state['extracted_data']:
        if st.button("Run Validation Checks"):
            with st.spinner("Validating..."):
                response = requests.post(f"{API_URL}/validate", json=st.session_state['extracted_data'])
                if response.status_code == 200:
                    val_result = response.json()
                    if val_result['is_valid']:
                        st.success("Data is valid! No anomalies detected.")
                    else:
                        st.error("Anomalies detected in the data:")
                        for anomaly in val_result['anomalies']:
                            st.warning(anomaly)
                else:
                    st.error(f"Validation failed: {response.text}")
    else:
        st.info("Please extract data first in Tab 1.")


with tab3:
    st.header("Reconcile with ERP")
    if st.session_state['extracted_data']:
        st.write("Simulate uploading ERP data (JSON format).")
        st.write("Expected schema: `[{\"date\": \"YYYY-MM-DD\", \"description\": \"...\", \"amount\": 100.0}]`")

        erp_data_input = st.text_area("ERP AP Data (JSON)", value="""[
    {"date": "2023-01-05", "description": "Vendor Payment A", "amount": 150.0},
    {"date": "2023-01-10", "description": "Office Supplies", "amount": 45.50}
]""")
        # We need the statement ID, assuming we just uploaded it, we'd need to fetch it or pass it back from the API
        # For this UI, let's hardcode ID 1 if we just did a fresh DB, or modify API to return the DB ID.
        # Let's assume we can get the latest from DB or we modify endpoint to return it.
        # *Note: The /process-document endpoint currently returns StatementSchema which doesn't have an ID.*
        # *For a full production app, the schema would include the DB ID.*
        st.info("Note: In a full app, we would select a specific Statement ID from the database.")
        statement_id = st.number_input("Statement ID (from DB)", min_value=1, value=1)

        if st.button("Run Reconciliation"):
            try:
                erp_data_parsed = json.loads(erp_data_input)
                payload = {
                    "statement_id": statement_id,
                    "erp_data": erp_data_parsed
                }

                response = requests.post(f"{API_URL}/reconcile", json=payload)
                if response.status_code == 200:
                    recon_result = response.json()
                    st.success("Reconciliation Complete!")

                    st.subheader(f"Matched ({len(recon_result['matched'])})")
                    if recon_result['matched']:
                         st.json(recon_result['matched'])

                    st.subheader(f"Unmatched Bank ({len(recon_result['unmatched_statement'])})")
                    if recon_result['unmatched_statement']:
                         st.dataframe(pd.DataFrame(recon_result['unmatched_statement']))

                    st.subheader(f"Unmatched ERP ({len(recon_result['unmatched_erp'])})")
                    if recon_result['unmatched_erp']:
                         st.dataframe(pd.DataFrame(recon_result['unmatched_erp']))

                    if recon_result['suspected_duplicates']:
                        st.subheader(f"Suspected Duplicates ({len(recon_result['suspected_duplicates'])})")
                        st.json(recon_result['suspected_duplicates'])
                else:
                    st.error(f"Reconciliation error: {response.text}")
            except json.JSONDecodeError:
                st.error("Invalid JSON format for ERP Data.")
    else:
         st.info("Please extract data first in Tab 1.")
