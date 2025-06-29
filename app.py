import streamlit as st
import requests
import pandas as pd
import datetime
import os

WATCHLIST_FILE = "watchlist.txt"
TRIALS_HISTORY_FILE = "trial_history.csv"
SPONSOR_CSV = "sponsor_lookup.csv"

# --- Sponsor Lookup from CSV ---
@st.cache_data
def load_sponsor_lookup():
    if not os.path.exists(SPONSOR_CSV):
        return {}
    df = pd.read_csv(SPONSOR_CSV)
    lookup = {}
    for _, row in df.iterrows():
        friendly = str(row['friendly_name']).strip()
        sponsor = str(row['sponsor_name']).strip()
        if friendly not in lookup:
            lookup[friendly] = []
        lookup[friendly].append(sponsor)
    return lookup

def get_sponsor_names(friendly_name):
    lookup = load_sponsor_lookup()
    return lookup.get(friendly_name, [])

def fetch_trials_for_sponsor(sponsor_name):
    url = (
        f"https://clinicaltrials.gov/api/query/study_fields?"
        f"sponsor={sponsor_name.replace(' ', '%20')}"
        f"&fields=NCTId,BriefTitle,Phase,StartDate,PrimaryCompletionDate,OverallStatus,LastUpdatePostDate"
        f"&min_rnk=1&max_rnk=500&fmt=json"
    )
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        if "StudyFieldsResponse" not in data or "StudyFields" not in data["StudyFieldsResponse"]:
            return pd.DataFrame()
        data = data['StudyFieldsResponse']['StudyFields']
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        for col in ['NCTId', 'BriefTitle', 'Phase', 'StartDate', 'PrimaryCompletionDate', 'OverallStatus', 'LastUpdatePostDate']:
            df[col] = df[col].apply(lambda x: x[0] if isinstance(x, list) and x else None)
        df['Sponsor'] = sponsor_name  # Track which sponsor this is from
        return df
    except Exception as e:
        st.warning(f"Error fetching data for sponsor '{sponsor_name}': {e}")
        return pd.DataFrame()

def fetch_trials(friendly_company):
    sponsor_names = get_sponsor_names(friendly_company)
    if not sponsor_names:
        return pd.DataFrame()
    all_dfs = []
    for sponsor in sponsor_names:
        df = fetch_trials_for_sponsor(sponsor)
        all_dfs.append(df)
    result = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
    result['FriendlyName'] = friendly_company
    return result

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
    try:
        return pd.read_csv(TRIALS_HISTORY_FILE)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()

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
st.markdown("""
**Search and add companies to watch clinical catalysts.**
You'll see upcoming readouts (calendar view), new trials, and phase changes. Notifications will pop up at the top right when there are updates.
""", unsafe_allow_html=True)

# 1. Sidebar: Add/Remove Companies
st.sidebar.header("Watchlist")
watchlist = load_watchlist()
add_company = st.sidebar.text_input("Add company (e.g. Immutep)", "")
if st.sidebar.button("Add to Watchlist") and add_company and add_company not in watchlist:
    if not get_sponsor_names(add_company):
        st.sidebar.error(
            f"No official sponsor mapping found for '{add_company}'.\n"
            "Please update sponsor_lookup.csv to include this company and its sponsor name(s)."
        )
    else:
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
    if trials.empty:
        st.warning(
            f"No trials found for company '{company}'.\n"
            "Check sponsor mapping or spelling."
        )
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
                <b>{row['FriendlyName']}</b> | <b>Sponsor:</b> {row['Sponsor']}<br>
                <b>{row['BriefTitle']}</b><br>
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
    st.dataframe(all_trials[['FriendlyName','Sponsor','BriefTitle','Phase','PrimaryCompletionDate','OverallStatus','LastUpdatePostDate']])

st.markdown("—\n*Made for Coronet Investments: User-friendly, no code needed, automatic monitoring of key clinical catalysts.*")
