import os
import glob
import math
import streamlit as st
import pandas as pd
import folium
from folium.plugins import Fullscreen
from streamlit_folium import st_folium

# ১. পেজ কনফিগারেশন
st.set_page_config(page_title="Location Finder Dashboard", page_icon="📡", layout="wide")

# কাস্টম সিএসএস
st.markdown("""
    <style>
        .block-container {
            padding-top: 1.2rem !important;
            padding-bottom: 1rem !important;
            max-width: 100% !important;
        }
        hr {
            margin-top: 0.8rem !important;
            margin-bottom: 0.8rem !important;
        }
        .contact-box {
            background-color: #f0f2f6;
            padding: 10px;
            border-radius: 8px;
            border-left: 4px solid #ff4b4b;
            margin-top: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# ২. স্টেট ও ইউজার ডাটাবেস ইনিশিয়ালাইজেশন
if 'users_db' not in st.session_state:
    st.session_state.users_db = {
        "admin": {"password": "adminpassword", "role": "admin", "name": "Admin"},
        "user": {"password": "user123", "role": "user", "name": "General User"}
    }

if 'active_sessions' not in st.session_state:
    st.session_state.active_sessions = set()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.user_role = ""

# ৩. লগইন স্ক্রিন
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 📡 Location Finder Dashboard")
        st.subheader("লগইন করুন")
        
        login_user = st.text_input("User ID / Username")
        login_pass = st.text_input("Password", type="password")
        
        if st.button("Log In", use_container_width=True):
            if login_user in st.session_state.users_db and st.session_state.users_db[login_user]["password"] == login_pass:
                st.session_state.logged_in = True
                st.session_state.username = login_user
                st.session_state.user_role = st.session_state.users_db[login_user]["role"]
                
                # প্রথমবার প্রবেশের নোটিফিকেশন ও অ্যাক্টিভ সেশন ট্র্যাক করা
                if login_user not in st.session_state.active_sessions:
                    st.session_state.active_sessions.add(login_user)
                    st.session_state.new_user_alert = f"🔔 নতুন ইউজার '{login_user}' সিস্টেমে প্রবেশ করেছেন!"
                
                st.rerun()
            else:
                st.error("ভুল ইউজার আইডি অথবা পাসওয়ার্ড!")

        # হেল্পলাইন মোবাইল নম্বর প্রদর্শনী
        st.markdown("""
            <div class="contact-box">
                📞 <b>প্রয়োজনে এডমিনের সাথে যোগাযোগ করুন:</b><br>
                মোবাইল নম্বর: <b>01914594294</b>
            </div>
        """, unsafe_allow_html=True)
    st.stop()

# ৪. সাইডবার কনফিগারেশন
st.sidebar.markdown(f"### 👤 {st.session_state.users_db[st.session_state.username]['name']}")
if st.session_state.user_role == "admin":
    st.sidebar.markdown('<span style="background-color:#007bff; color:white; padding:2px 8px; border-radius:10px; font-size:12px;">Admin Panel</span>', unsafe_allow_html=True)

if st.sidebar.button("🚪 Logout"):
    if st.session_state.username in st.session_state.active_sessions:
        st.session_state.active_sessions.remove(st.session_state.username)
    st.session_state.logged_in = False
    st.rerun()

st.sidebar.divider()

# ৫. এডমিন প্যানেল (ব্যবহারকারী ব্যবস্থাপনা ও অ্যাক্টিভ স্ট্যাটাস)
if st.session_state.user_role == "admin":
    with st.sidebar.expander("⚙️ Admin Control Panel", expanded=True):
        st.write(f"👥 **বর্তমানে মোট অ্যাক্টিভ ইউজার:** `{len(st.session_state.active_sessions)}` জন")
        
        # নোটিফিকেশন পপআপ
        if 'new_user_alert' in st.session_state and st.session_state.new_user_alert:
            st.toast(st.session_state.new_user_alert, icon="🔔")
        
        st.markdown("---")
        st.markdown("**➕ নতুন ইউজার আইডি তৈরি করুন**")
        new_name = st.text_input("ইউজারের পুরো নাম")
        new_userid = st.text_input("নতুন User ID (নাম/আইডি)")
        new_password = st.text_input("পাসওয়ার্ড সেট করুন", type="password")
        
        if st.button("নতুন ইউজার তৈরি করুন"):
            if new_userid and new_password:
                if new_userid not in st.session_state.users_db:
                    st.session_state.users_db[new_userid] = {
                        "password": new_password,
                        "role": "user",
                        "name": new_name if new_name else new_userid
                    }
                    st.success(f"ইউজার '{new_userid}' সফলভাবে তৈরি হয়েছে!")
                else:
                    st.warning("এই ইউজার আইডিটি ইতিমধ্যে বিদ্যমান!")
            else:
                st.error("আইডি এবং পাসওয়ার্ড উভয়ই পূরণ করুন।")

st.sidebar.divider()

# ৬. ডাটা সোর্স লোডিং logic (Parquet/CSV)
@st.cache_data
def load_data():
    file_path = None
    if os.path.exists("bts_data.parquet"):
        file_path = "bts_data.parquet"
    else:
        csv_files = glob.glob("*.csv")
        if csv_files:
            file_path = csv_files[0]
            
    if file_path:
        if file_path.endswith('.parquet'):
            df = pd.read_parquet(file_path)
        else:
            df = pd.read_csv(file_path, encoding='latin-1', low_memory=False)
        return df, file_path
    return None, None

df, current_file = load_data()

st.sidebar.markdown("📁 **ডেটা সোর্স**")
uploaded_file = st.sidebar.file_uploader("অন্য কোনো ফাইল আপলোড করুন (Admin Only):", type=['csv', 'parquet'])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.parquet'):
            df = pd.read_parquet(uploaded_file)
        else:
            df = pd.read_csv(uploaded_file, encoding='latin-1', low_memory=False)
        st.sidebar.success(f"নতুন ফাইল সফলভাবে লোড হয়েছে! মোট রো: {len(df):,}")
    except Exception as e:
        st.sidebar.error(f"ফাইল লোড করতে সমস্যা হয়েছে: {e}")
elif df is not None:
    st.sidebar.info(f"ফাইল লোড করা আছে ({current_file})। মোট রো: {len(df):,}")
else:
    st.sidebar.warning("কোনো ডেটা ফাইল পাওয়া যায়নি!")

# হেল্পলাইন নোটিশ সাইডবারেও যুক্ত
st.sidebar.markdown("""
    <div class="contact-box">
        📞 <b>এডমিন হটলাইন:</b><br>
        01914594294
    </div>
""", unsafe_allow_html=True)

# ----------------- মূল ড্যাশবোর্ড ইন্টারফেস -----------------
st.title("📡 Location Finder Dashboard")
st.write("সহজ ও দ্রুত উপায়ে লাখ লাখ বিটিএস ডেটা থেকে অনুসন্ধান করুন।")

if df is None:
    st.warning("👉 ফোল্ডারে কোনো ডেটা ফাইল পাওয়া যায়নি। অনুগ্রহ করে আপলোড করুন।")
    st.stop()

# অনুসন্ধান ট্যাব
tab1, tab2 = st.tabs(["🔍 Tower Search (Single)", "📋 Multiple Search (একাধিক সার্চ)"])

with tab1:
    col_p, col_m = st.columns(2)
    with col_p:
        provider = st.selectbox("Provider", ["All Providers"] + list(df['Provider'].unique()) if 'Provider' in df.columns else ["All Providers"])
    with col_m:
        search_method = st.selectbox("Search Method", ["Lac & Cell", "Lat & Long", "Address/Location"])

    if search_method == "Lac & Cell":
        c1, c2 = st.columns(2)
        lac = c1.text_input("LAC")
        cell = c2.text_input("Cell ID")
        
        if st.button("🔍 সার্চ করুন", type="primary"):
            st.info("অনুসন্ধানের ফলাফল ম্যাপে দেখানো হবে।")

with tab2:
    st.write("একাধিক LAC/Cell ID একসাথে সার্চ করার সুবিধা।")
