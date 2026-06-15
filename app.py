import streamlit as st
import tempfile
import os
from agent import app

st.set_page_config(page_title="PE Due Diligence Agent", layout="wide")

st.title("📊 Private Equity Due Diligence Agent")
st.caption("Upload a financial filing (PDF) to generate an investment memo.")

uploaded_file = st.file_uploader("Upload a financial filing", type=["pdf"])

if uploaded_file is not None:
    if st.button("🚀 Run Analysis"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        try:
            with st.spinner("Analyzing filing... this may take 30–60 seconds."):
                final_output = app.invoke({"pdf_path": tmp_path})

            st.success("✅ Analysis Complete")

            st.markdown("---")
            st.markdown(final_output["investment_memo"])

            with st.expander("🔍 Raw Extracted Financials"):
                st.json(final_output["extracted_financials"])

            with st.expander("📐 Calculated Metrics"):
                st.json(final_output["calculated_metrics"])

        except ValueError as e:
            st.error(f"Validation failed: {e}")
        except Exception as e:
            st.error(f"Something went wrong: {e}")
        finally:
            os.unlink(tmp_path)  # clean up temp file

#whenever there is an validation error there needs to be only a message, not a traceback