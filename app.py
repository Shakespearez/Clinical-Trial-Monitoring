import streamlit as st
import requests
import pandas as pd
import datetime
import os

WATCHLIST_FILE = "watchlist.txt"
TRIALS_HISTORY_FILE = "trial_history.csv"

# --- Helper functions ---
def fetch_trials(company):
    url = (
        f"https://clinicaltrials.gov/api/query/study_fields?expr={company}"
        f"&fields=NCTId,BriefTitle,Phase,StartDate,PrimaryCompletionDate,OverallStatus,LastUpdatePostDate"
        f"&min_rnk=1&max_rnk=500&fmt=json"
    )
    r = requests.get(url)
    data = r.json()['StudyFieldsResponse']['StudyFields']
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    # Clean up
    for col in ['NCTId', 'BriefTitle', 'Phase', 'StartDate', 'PrimaryCompletionDate', 'OverallStatus', 'LastUpdatePostDate']:
        df[col] = df[col].apply(lambda x: x[0] if isinstance(x, list) and x else None)
    return df

def flag_catalysts(df, months_ahead=12):
    now = datetime.datetime.now()
    df['PrimaryCompletionDate'] = pd.to_datetime(df['PrimaryCompletionDate'], errors='coerce')
    df['Catalyst'] = df['PrimaryCompletionDate'].apply(lambda d: d and (0 <= (d - now).days <= months_ahead*30))
    return df

def save_watchlist(watchlist):
    with open(WATCHLIST_FILE, "w") as f:
        for item in watchlist:
            f.write(item + "\n")

def load_watchlist():
    if not os.path.exists(WATCHLIST_FILE):
        return []
    with open(WATCHLIST_FILE, "r") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def save_trial_history(df):
    df.to_csv(TRIALS_HISTORY_FILE, index=False)

def load_trial_history():
    if not os.path.exists(TRIALS_HISTORY_FILE):
        return pd.DataFrame()
    return pd.read_csv(TRIALS_HISTORY_FILE)

def compare_trials(df_new, df_old):
    if df_old.empty or 'NCTId' not in df_old.columns:
        return [], []
    new_ids = set(df_new['NCTId']) - set(df_old['NCTId'])
    changed_phase = []
    for nct in set(df_new['NCTId']).intersection(df_old['NCTId']):
        phase_old = df_old[df_old['NCTId'] == nct]['Phase'].values[0]
        phase_new = df_new[df_new['NCTId'] == nct]['Phase'].values[0]
        if phase_old != phase_new:
            changed_phase.append(nct)
    return list(new_ids), changed_phase

# --- Streamlit UI ---
st.set_page_config(page_title="Clinical Trial Catalyst Dashboard", layout="wide")
st.title("Clinical Trial & Drug Pipeline Monitoring")
st.markdown("**Search and add companies to watch clinical catalysts.**<br>"
            "You'll see upcoming readouts (calendar view), new trials, and phase changes. Notifications will pop up at the top right when there are updates.",
            unsafe_allow_html=True)

# 1. Sidebar: Add/Remove Companies
st.sidebar.header("Watchlist")
watchlist = load_watchlist()
add_company = st.sidebar.text_input("Add company (e.g. Immutep)", "")
if st.sidebar.button("Add to Watchlist") and add_company and add_company not in watchlist:
    watchlist.append(add_company)
    save_watchlist(watchlist)
    st.sidebar.success(f"Added {add_company} to watchlist.")
if watchlist:
    remove_company = st.sidebar.selectbox("Remove from Watchlist", [""] + watchlist)
    if st.sidebar.button("Remove Company") and remove_company:
        watchlist = [w for w in watchlist if w != remove_company]
        save_watchlist(watchlist)
        st.sidebar.success(f"Removed {remove_company}.")

# 2. Sidebar: Alert settings
months_ahead = st.sidebar.slider("Alert window (months ahead for catalyst)", 1, 24, 12)

# 3. Main panel: Show all company trials
all_trials = pd.DataFrame()
for company in watchlist:
    trials = fetch_trials(company)
    trials['Company'] = company
    all_trials = pd.concat([all_trials, trials], ignore_index=True)
if not all_trials.empty:
    all_trials = flag_catalysts(all_trials, months_ahead=months_ahead)

# 4. In-dashboard notifications for new catalysts or phase changes
trial_history = load_trial_history()
new_trials, changed_phase = compare_trials(all_trials, trial_history)
if new_trials or changed_phase:
    msg = ""
    if new_trials:
        msg += f"🟢 **New trials:** {', '.join(new_trials)}\n"
    if changed_phase:
        msg += f"🟡 **Phase changes:** {', '.join(changed_phase)}\n"
    if msg:
        st.toast(msg, icon="🔔")
save_trial_history(all_trials)

# 5. Dashboard: Calendar view of catalysts
st.header("Catalyst Calendar")
if not all_trials.empty:
    catalysts = all_trials[all_trials['Catalyst']]
    if catalysts.empty:
        st.info("No catalysts within selected window.")
    else:
        for idx, row in catalysts.iterrows():
            st.markdown(
                f"""
                <div style="border-left:4px solid #36a2ef; margin-bottom:12px; padding:8px;">
                <b>{row['Company']}:</b> {row['BriefTitle']}<br>
                <b>Phase:</b> {row['Phase']}<br>
                <b>Primary Completion:</b> {row['PrimaryCompletionDate'].date() if pd.notnull(row['PrimaryCompletionDate']) else 'N/A'}<br>
                <b>Status:</b> {row['OverallStatus']}<br>
                <b>Last Updated:</b> {row['LastUpdatePostDate']}<br>
                <a href="https://clinicaltrials.gov/ct2/show/{row['NCTId']}" target="_blank">ClinicalTrials.gov link</a>
                </div>
                """, unsafe_allow_html=True)
else:
    st.info("Add a company to your watchlist to see catalysts.")

# 6. Table: All trials
st.header("All Trials")
if not all_trials.empty:
    st.dataframe(all_trials[['Company','BriefTitle','Phase','PrimaryCompletionDate','OverallStatus','LastUpdatePostDate']])

st.markdown("—\n*Made for Coronet Investments: User-friendly, no code needed, automatic monitoring of key clinical catalysts.*")

