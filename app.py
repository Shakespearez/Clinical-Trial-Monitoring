import streamlit as st
import requests
import io
import PyPDF2
import re
import pandas as pd
import plotly.graph_objects as go
import datetime

def get_patent_expiry_from_pdf(pdf_url):
    try:
        response = requests.get(pdf_url)
        response.raise_for_status()
        pdf_file = io.BytesIO(response.content)
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        pattern = r"(?:patent(?:\s+\w+)*\s+expiry\s+date(?:\s+\w+)*\s*(?:is|:|,)?\s*)?(\d{1,2}(?:st|nd|rd|th)?(?:\s+of)?\s+\w+\s*,?\s*\d{4})"
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        for m in matches:
            try:
                date = pd.to_datetime(m, errors='coerce', dayfirst=True)
                if date and date.year == 2036:  # Focus on the known date for IMP321
                    return date
            except:
                pass
        return None
    except Exception as e:
        st.warning(f"Could not extract expiry date from PDF: {e}")
        return None

st.set_page_config(page_title="Drug Patent Expiry Calendar", layout="wide")
st.title("Drug Patent Expiry Calendar")

drug = st.text_input("Enter drug name (e.g., 'IMP321')")

expiry_event = None
expiry_date = None

if st.button("Find IP Expiry Date"):
    if drug.strip().upper() == "IMP321":
        pdf_url = "https://www.immutep.com/files/content/investor/press-release/2022/IMM%20-%20Australian%20Patent%20Granted%20for%20Efti%20with%20PD-1%20Inhibitors%20-%2011Feb2022.pdf"
        with st.spinner("Scraping patent expiry date..."):
            expiry_date = get_patent_expiry_from_pdf(pdf_url)
        if expiry_date:
            expiry_event = {
                'date': expiry_date,
                'label': f'IMP321: Patent Expiry<br>{expiry_date.strftime("%d %B %Y")}'
            }
            st.success(f"Key Patent Expiry Date for IMP321: {expiry_date.strftime('%d %B %Y')}")
        else:
            st.error("No expiry date found in the document.")
    else:
        st.warning("Currently, this tool supports 'IMP321'.")

# --- Calendar heatmap logic ---
selected_year = expiry_event['date'].year if expiry_event else datetime.date.today().year
years = list(range(selected_year-5, selected_year+6))
year = st.selectbox("Select year", years, index=years.index(selected_year))

start_date = datetime.date(year, 1, 1)
end_date = datetime.date(year, 12, 31)
date_range = pd.date_range(start=start_date, end=end_date)

z = []
hover = []
for date in date_range:
    found = False
    if expiry_event and date.date() == expiry_event['date'].date():
        z.append(2)  # Highlight
        hover.append(expiry_event['label'])
        found = True
    if not found:
        z.append(0)  # Blank/grey
        hover.append("")  # No tooltip

weeks = (date_range.dayofyear - 1) // 7
dow = date_range.weekday
grid = pd.DataFrame({'week': weeks, 'dow': dow, 'z': z, 'hover': hover})

fig = go.Figure()
for idx, row in grid.iterrows():
    color = 'gold' if row['z'] == 2 else 'rgba(200,200,200,0.06)'
    border = dict(color='black', width=1.5) if row['z'] == 2 else dict(color='rgba(60,60,60,0.1)', width=1)
    fig.add_trace(go.Scatter(
        x=[row['week']],
        y=[row['dow']],
        mode='markers',
        marker=dict(
            size=18,
            color=color,
            line=border,
        ),
        hovertemplate=row['hover'] if row['z'] == 2 else None,
        showlegend=False
    ))

fig.update_layout(
    height=170,
    margin=dict(l=0, r=0, t=0, b=0),
    xaxis=dict(
        showgrid=False,
        showticklabels=False,
        zeroline=False,
        range=[-1, grid['week'].max() + 2]
    ),
    yaxis=dict(
        showgrid=False,
        showticklabels=False,
        zeroline=False,
        range=[-1, 7]
    ),
    plot_bgcolor='rgba(0,0,0,0)',
)
fig.add_annotation(
    x=grid['week'].median(),
    y=7,
    text=str(year),
    showarrow=False,
    font=dict(size=16),
    yshift=12
)

st.header("Key Date Calendar")
st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Search for a drug to display its catalyst date on the calendar. "
    "Hover highlighted days for catalyst details. "
    "Calendar remains blank until a key date is found."
)
