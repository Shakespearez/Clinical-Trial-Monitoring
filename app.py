import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime

# Define key events (for demo: IMP321 expiry only, but you can add more)
# Format: {'date': datetime.date, 'label': 'Display Text'}
key_events = [
    {'date': datetime.date(2036, 1, 8), 'label': 'IMP321: Patent Expiry\n8 January 2036'},
    # Add more like:
    # {'date': datetime.date(2027, 6, 1), 'label': 'DrugX: FDA Decision\n1 June 2027'},
]

# UI: pick a year
years = list(set([d['date'].year for d in key_events] + list(range(2023, 2041))))
years = sorted(years)
year = st.selectbox("Select year", years, index=years.index(2036) if 2036 in years else 0)

# Build day grid for the selected year
start_date = datetime.date(year, 1, 1)
end_date = datetime.date(year, 12, 31)
date_range = pd.date_range(start=start_date, end=end_date)

# For each day, default color is grey; special days get highlight and tooltip
z = []
hover = []
for date in date_range:
    found = False
    for event in key_events:
        if date.date() == event['date']:
            z.append(2)  # Highlight
            hover.append(event['label'])
            found = True
            break
    if not found:
        z.append(1)
        hover.append(date.strftime('%d %b %Y'))

# Calendar as grid (7 rows for days of week, columns for weeks)
weeks = (date_range.dayofyear - 1) // 7
dow = date_range.weekday
grid = pd.DataFrame({'week': weeks, 'dow': dow, 'z': z, 'hover': hover})

# Build Plotly figure
fig = go.Figure()
for idx, row in grid.iterrows():
    fig.add_trace(go.Scatter(
        x=[row['week']],
        y=[row['dow']],
        mode='markers',
        marker=dict(
            size=18,
            color='gold' if row['z'] == 2 else 'rgba(200,200,200,0.9)',
            line=dict(color='black', width=1) if row['z'] == 2 else dict(color='rgba(60,60,60,0.6)', width=1),
        ),
        hovertemplate=row['hover'],
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

st.title("Key Catalyst Calendar")
st.plotly_chart(fig, use_container_width=True)

st.caption("Click through years and hover highlighted days for catalyst details. Add more events to key_events as needed.")
