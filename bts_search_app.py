import streamlit as st

# ১. পেজ কনফিগারেশন (সাইডবারের অবস্থা নির্ধারণের আগে সেট করতে হয়)
st.set_page_config(
    page_title="Location Finder Dashboard",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ২. CSS কোড - সাইডবার টগল বাটন (Arrow) যেন কখনোই লুকিয়ে না যায়
st.markdown("""
    <style>
    /* সাইডবার বন্ধ থাকলেও টগল বাটন যেন সবসময় দৃশ্যমান থাকে */
    [data-testid="stSidebarCollapsedControl"] {
        display: block !important;
        visibility: visible !important;
        z-index: 999999 !important;
        top: 0.75rem !important;
        left: 0.75rem !important;
        background-color: rgba(255, 255, 255, 0.1) !important;
        border-radius: 5px !important;
    }
    
    /* সাইডবার বাটন হোভার ইফেক্ট */
    [data-testid="stSidebarCollapsedControl"]:hover {
        background-color: rgba(255, 255, 255, 0.2) !important;
    }
    
    /* মেইন কন্টেন্ট প্যাডিং ঠিক রাখা */
    .main .block-container {
        padding-top: 2rem;
    }
    </style>
""", unsafe_allow_html=True)


# ৩. সাইডবার (Sidebar) প্যানেল কন্টেন্ট
with st.sidebar:
    st.markdown("### 👤 mohon mia")
    st.markdown("`General User Panel`")
    
    if st.button("🚪 Logout"):
        st.info("Logged out successfully!")

    st.markdown("---")
    
    with st.expander("🔑 সেটিং (Password Change)"):
        st.text_input("পুরাতন পাসওয়ার্ড", type="password")
        st.text_input("নতুন পাসওয়ার্ড", type="password")
        st.button("পাসওয়ার্ড আপডেট করুন")
        
    st.markdown("---")
    st.markdown("### 🗺️ ম্যাপ ও সেক্টর সেটিং")
    
    map_style = st.selectbox(
        "ম্যাপের স্টাইল:",
        ["Google Hybrid", "OpenStreetMap", "Satellite", "Terrain"]
    )
    
    sector_coverage = st.slider(
        "সেক্টর কাভারেজ (মিটার):",
        min_value=50,
        max_value=2000,
        value=350,
        step=50
    )
    
    sector_angle = st.slider(
        "সেক্টর এ্যাঙ্গেল (ডিগ্রি):",
        min_value=10,
        max_value=360,
        value=60,
        step=5
    )


# ৪. মূল ড্যাশবোর্ড কন্টেন্ট (Main Body)
st.title("📡 Location Finder Dashboard")
st.write("সহজ ও দ্রুত উপায়ে লাখ লাখ বিটিএস ডেটা থেকে অনুসন্ধান করুন।")

# সার্চ ট্যাব
tab1, tab2 = st.tabs(["🔍 Tower Search (Single)", "📑 Multiple Search (একাধিক সার্চ)"])

with tab1:
    st.subheader("একক অনুসন্ধান")
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("LAC লিখুন:")
    with col2:
        st.text_input("CELL ID লিখুন:")
    st.button("সার্চ করুন", key="single_search")

with tab2:
    col_lac, col_cell = st.columns(2)
    with col_lac:
        lac_input = st.text_area("LAC সমূহ (কমা দিয়ে লিখুন):", value="58711, 58711")
    with col_cell:
        cell_input = st.text_area("CELL ID সমূহ (কমা দিয়ে লিখুন):", value="27133987, 27133963")
    
    search_btn = st.button("🔍 একাধিক সার্চ করুন", type="primary", use_container_width=True)
    
    if search_btn or lac_input:
        st.success("🎉 মোট ২ টি তথ্য পাওয়া গেছে!")
        
        # নমুনা ডেটা ডেমো টেবিল
        sample_data = [
            {"provider": "GP", "LAC": 58711, "CELL": 27133987, "2G/3G/4G": "4G", "DIRECTION": 140, "LATITUDE": 23.994141, "LONGITUDE": 90.802701, "SITE ADDRESS": "Jankhartec more, Raipura, Narsingdi"},
            {"provider": "GP", "LAC": 58711, "CELL": 27133963, "2G/3G/4G": "4G", "DIRECTION": 140, "LATITUDE": 23.994141, "LONGITUDE": 90.802701, "SITE ADDRESS": "Jankhartec more, Raipura, Narsingdi"}
        ]
        
        st.dataframe(sample_data, use_container_width=True)
