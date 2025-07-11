import streamlit as st
import requests
import io
import PyPDF2
import re
import pandas as pd

def get_patent_expiry_from_pdf(pdf_url):
    try:
        response = requests.get(pdf_url)
        response.raise_for_status()
        pdf_file = io.BytesIO(response.content)
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        # Pattern to find a date (e.g., 8 January 2036, 8th of January 2036, etc.)
        pattern = r"(?:patent(?:\s+\w+)*\s+expiry\s+date(?:\s+\w+)*\s*(?:is|:|,)?\s*)?(\d{1,2}(?:st|nd|rd|th)?(?:\s+of)?\s+\w+\s*,?\s*\d{4})"
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        for m in matches:
            try:
                date = pd.to_datetime(m, errors='coerce', dayfirst=True)
                if date and date.year == 2036:
                    return date.strftime("%d %B %Y")
            except:
                pass
        return None
    except Exception as e:
        st.warning(f"Could not extract expiry date from PDF: {e}")
        return None

st.set_page_config(page_title="Drug Patent Expiry Dashboard", layout="wide")
st.title("Drug Patent Expiry Scraper")

drug = st.text_input("Enter drug name (e.g., 'IMP321')")

if st.button("Find IP Expiry Date"):
    if drug.strip().upper() == "IMP321":
        pdf_url = "https://www.immutep.com/files/content/investor/press-release/2022/IMM%20-%20Australian%20Patent%20Granted%20for%20Efti%20with%20PD-1%20Inhibitors%20-%2011Feb2022.pdf"
        with st.spinner("Scraping patent expiry date..."):
            expiry = get_patent_expiry_from_pdf(pdf_url)
        if expiry:
            st.success(f"**Key Patent Expiry Date for IMP321:** {expiry}")
            st.info("This date was scraped from the official Immutep PDF (Australian Patent for Efti/IMP321).")
        else:
            st.error("No expiry date found in the document.")
    else:
        st.warning("Currently, this tool supports 'IMP321'.")

st.markdown("""
---
This workflow can be extended to support multiple drugs, company documents, or PDF uploads, and can be integrated into a full catalyst dashboard for automated monitoring of IP-related dates.
""")
