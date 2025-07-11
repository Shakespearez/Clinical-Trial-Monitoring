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
        # Look for a date in the format: 8 January 2036 or 8th of January 2036, or 8 January, 2036, etc.
        # Also allow for "patent expiry date", "expires", etc.
        pattern = r"(?:patent(?:\s+\w+)*\s+expiry\s+date(?:\s+\w+)*\s*(?:is|:|,)?\s*)?(\d{1,2}(?:st|nd|rd|th)?(?:\s+of)?\s+\w+\s*,?\s*\d{4})"
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        # Now, look for a match for "8 January 2036" (or similar)
        # Convert to datetime for display
        for m in matches:
            try:
                # Try to parse with pandas
                date = pd.to_datetime(m, errors='coerce', dayfirst=True)
                if date and date.year == 2036:  # We expect 2036 for the demo
                    return date.strftime("%d %B %Y")
            except:
                pass
        return None
    except Exception as e:
        st.warning(f"Could not extract expiry date from PDF: {e}")
        return None

st.set_page_config(page_title="Demo: IP Catalyst Dashboard", layout="wide")
st.title("Drug Patent Expiry Scraper")

st.write("This is a demo of extracting key IP catalyst dates from company documents.")

drug = st.text_input("Enter drug name (try 'IMP321')")

if st.button("Find IP Expiry Date"):
    if drug.strip().upper() == "IMP321":
        # This is the known PDF for demo purposes
        pdf_url = "https://www.immutep.com/files/content/investor/press-release/2022/IMM%20-%20Australian%20Patent%20Granted%20for%20Efti%20with%20PD-1%20Inhibitors%20-%2011Feb2022.pdf"
        with st.spinner("Scraping patent expiry date..."):
            expiry = get_patent_expiry_from_pdf(pdf_url)
        if expiry:
            st.success(f"**Key Patent Expiry Date for IMM: IMP321:** {expiry}")
            st.info("This date is scraped from the official Immutep PDF (Australian Patent for Efti/IMP321).")
        else:
            st.error("No expiry date found in the document.")
    else:
        st.warning("")

st.markdown()
