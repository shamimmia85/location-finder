import os
import glob
import math
import streamlit as st
import pandas as pd
import folium
from folium.plugins import Fullscreen
from streamlit_folium import st_folium
from math import radians, cos, sin, asin, sqrt

# ১. পেজ কনফিগারেশন
st.set_page_config(page_title="Location Finder Dashboard", page_icon="📡", layout="wide")

# কাস্টম সিএসএস (ফন্ট সাইজ ও লেআউট)
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
        .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            margin-bottom: 0.3rem !important;
        }
        .profile-name-text {
            font-size: 20px;
            font-weight: bold;
            color: #1a1a1a;
            margin-bottom: 5px;
        }
        .role-badge {
            background-color: #007bff;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
            display: inline-block;
            margin-bottom: 10px;
        }
        .site-card {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 14px 18px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.06);
            margin-top: 5px;
            margin-bottom: 10px;
        }
        .site-details-inline {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            align-items: center;
            font-size: 17px;
            color: #1a1a1a;
        }
        .site-details-inline div {
            font-size: 17px;
        }
        .site-address-text {
            margin-top: 10px;
            font-size: 17px;
            color: #1a1a1a;
        }
        iframe {
            width: 100% !important;
        }
    </style>
""", unsafe_allow_html=True)

# ------------------ ২. ইউজার ডেটাবেস ও লগইন সিস্টেম ------------------
USER_DB = {
    "admin": {"password": "admin123", "role": "Admin", "name": "ASI Shamim BPM"},
    "user": {"password": "user123", "role": "User", "name": "General User"}
}

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None

def login():
    st.title("🔒 Location Finder Dashboard - Login")
    col1, col2 = st.columns([1, 2])
    with col1:
        username = st.text_input("Username").strip()
        password = st.text_input("Password", type="password").strip()
        submit = st.button("Log In", type="primary", use_container_width=True)
        
        if submit:
            if username in USER_DB and USER_DB[username]["password"] == password:
                st.session_state['authenticated'] = True
                st.session_state['user_info'] = USER_DB[username]
                st.rerun()
            else:
                st.error("❌ ইউজারনেম অথবা পাসওয়ার্ড ভুল হয়েছে!")

if not st.session_state['authenticated']:
    login()
    st.stop()

# ------------------ ৩. লগইন পরবর্তী মূল অ্যাপ্লিকেশন ------------------
user_info = st.session_state['user_info']
is_admin = user_info['role'] == "Admin"

# সাইডবার ইউজার প্রোফাইল
st.sidebar.markdown(f'<div class="profile-name-text">{user_info["name"]}</div>', unsafe_allow_html=True)
st.sidebar.markdown(f'<span class="role-badge">{user_info["role"]} Panel</span>', unsafe_allow_html=True)

if st.sidebar.button("🚪 Logout", key="logout_btn"):
    st.session_state['authenticated'] = False
    st.session_state['user_info'] = None
    st.rerun()

st.sidebar.markdown("---")

# টাইটেল
st.title("📡 Location Finder Dashboard")
st.write("সহজ ও দ্রুত উপায়ে লাখ লাখ বিটিএস ডেটা থেকে অনুসন্ধান করুন।")

# ডেটা লোড ফাংশন
@st.cache_data(show_spinner="ডেটা দ্রুত প্রক্রিয়াকরণ হচ্ছে...")
def load_data_optimized(file_or_path):
    filename = file_or_path if isinstance(file_or_path, str) else file_or_path.name
    
    if filename.endswith('.parquet'):
        df = pd.read_parquet(file_or_path)
    elif filename.endswith('.csv'):
        encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
        df = None
        for enc in encodings:
            try:
                df = pd.read_csv(file_or_path, low_memory=False, encoding=enc)
                break
            except Exception:
                continue
        if df is None:
            df = pd.read_csv(file_or_path, low_memory=False, on_bad_lines='skip')
    else:
        df = pd.read_excel(file_or_path, engine='openpyxl')
    
    lac_c = next((c for c in df.columns if 'lac' in c.lower()), None)
    cell_c = next((c for c in df.columns if 'cell' in c.lower()), None)
    
    if lac_c:
        df['_search_lac'] = df[lac_c].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    if cell_c:
        df['_search_cell'] = df[cell_c].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        
    return df

def get_operator_color(provider_name):
    prov = str(provider_name).lower()
    if 'gp' in prov or 'grameen' in prov:
        return '#007bff'
    elif 'robi' in prov or 'airtel' in prov:
        return '#e6121b'
    elif 'banglalink' in prov or 'bl' in prov:
        return '#ff7300'
    elif 'teletalk' in prov:
        return '#28a745'
    else:
        return '#6c757d'

def create_sector_wedge(lat, lon, azimuth, distance_meters=350, beamwidth=60):
    points = [[lat, lon]]
    start_angle = azimuth - (beamwidth / 2)
    end_angle = azimuth + (beamwidth / 2)
    
    for angle in range(int(start_angle), int(end_angle) + 1, 5):
        rad = math.radians(angle)
        d_lat = (distance_meters * math.cos(rad)) / 111320.0
        d_lon = (distance_meters * math.sin(rad)) / (111320.0 * math.cos(math.radians(lat)))
        points.append([lat + d_lat, lon + d_lon])
        
    points.append([lat, lon])
    
    label_dist = distance_meters * 0.60
    label_rad = math.radians(azimuth)
    label_lat = lat + ((label_dist * math.cos(label_rad)) / 111320.0)
    label_lon = lon + ((label_dist * math.sin(label_rad)) / (111320.0 * math.cos(math.radians(lat))))
    
    return points, label_lat, label_lon

def clean_val(val):
    if pd.isna(val) or val is None or str(val).strip() == "":
        return "N/A"
    try:
        f = float(val)
        if f.is_integer():
            return str(int(f))
        return str(f)
    except Exception:
        return str(val).replace('.0', '')

# ------------------ ৪. ডেটা ফাইল লোড (এডমিন ও ইউজার পারমিশন) ------------------
st.sidebar.header("📁 ডেটা সোর্স")

df = None
all_files = glob.glob("*.parquet") + glob.glob("*.csv") + glob.glob("*.xlsx") + glob.glob("*.xls")

if all_files:
    auto_file = all_files[0]
    try:
        df = load_data_optimized(auto_file)
        st.sidebar.success(f"📂 **{auto_file}** লোড হয়েছে! মোট রো: {len(df):,}")
    except Exception as e:
        st.sidebar.error(f"ফাইল লোড ত্রুটি: {e}")

# কেবল এডমিন নতুন ফাইল আপলোড করতে পারবেন
if is_admin:
    uploaded_file = st.sidebar.file_uploader("অন্য কোনো ফাইল আপলোড করুন (Admin Only):", type=["parquet", "csv", "xlsx"])
    if uploaded_file is not None:
        try:
            df = load_data_optimized(uploaded_file)
            st.sidebar.success(f"নতুন ফাইল সফলভাবে লোড হয়েছে! মোট রো: {len(df):,}")
        except Exception as e:
            st.sidebar.error(f"ফাইল লোড ত্রুটি: {e}")
else:
    st.sidebar.info("💡 সাধারণ ইউজারগণ শুধুমাত্র প্রস্তুতকৃত ডেটাবেস অনুসন্ধান করতে পারবেন।")

# সাইডবার ম্যাপ সেটিংস
st.sidebar.markdown("---")
st.sidebar.header("🗺️ ম্যাপ ও সেক্টর সেটিংস")
map_theme = st.sidebar.selectbox(
    "ম্যাপের স্টাইল:",
    ["OpenStreetMap", "CartoDB positron", "CartoDB dark_matter", "Esri WorldImagery"]
)
sector_radius = st.sidebar.slider("সেক্টর কভারেজ (মিটার):", min_value=100, max_value=1000, value=350, step=50)
beam_angle = st.sidebar.slider("সেক্টর অ্যাঙ্গেল (ডিগ্রি):", min_value=30, max_value=120, value=60, step=10)

# ------------------ ৫. মূল সার্চ ইন্টারফেস ------------------
if df is not None:
    st.markdown("---")
    
    col_names = df.columns.tolist()

    lac_col = next((c for c in col_names if 'lac' in c.lower() and c != '_search_lac'), col_names[0])
    cell_col = next((c for c in col_names if 'cell' in c.lower() and c != '_search_cell'), col_names[0])
    provider_col = next((c for c in col_names if any(x in c.lower() for x in ['provider', 'operator', 'company'])), col_names[0])
    dir_col = next((c for c in col_names if 'dir' in c.lower()), None)
    lat_col = next((c for c in col_names if 'lat' in c.lower()), None)
    lon_col = next((c for c in col_names if 'lon' in c.lower() or 'lng' in c.lower()), None)
    addr_col = next((c for c in col_names if any(x in c.lower() for x in ['address', 'site', 'location'])), None)

    # এডমিন সব সুবিধা পাবেন, ইউজারদের জন্য সার্চ নিয়ন্ত্রণ রাখা যাবে
    tab1, tab2 = st.tabs(["🔍 Tower Search (Single)", "📑 Multiple Search (একাধিক সার্চ)"])

    # ------------------ ট্যাব ১: একক সার্চ ------------------
    with tab1:
        p_col1, p_col2 = st.columns(2)

        with p_col1:
            selected_provider = st.selectbox(
                "Provider", 
                ["All Providers", "Grameenphone", "Robi And Airtel", "Banglalink", "Teletalk"],
                key="single_prov"
            )

        with p_col2:
            if selected_provider == "All Providers":
                method_options = ["Lac & Cell", "BTS Address"]
            else:
                method_options = ["LAC", "Cell ID", "BTS Address"]
                
            selected_method = st.selectbox("Search Method", method_options, key="single_method")

        lac_val_in, cell_val_in, address_val_in = "", "", ""
        
        if selected_method == "Lac & Cell":
            i_col1, i_col2 = st.columns(2)
            with i_col1:
                lac_val_in = st.text_input("LAC", placeholder="LAC লিখুন", key="s_lac").strip()
            with i_col2:
                cell_val_in = st.text_input("Cell ID", placeholder="CELL ID লিখুন", key="s_cell").strip()
        elif selected_method == "LAC":
            lac_val_in = st.text_input("LAC", placeholder="LAC লিখুন", key="s_lac_only").strip()
        elif selected_method == "Cell ID":
            cell_val_in = st.text_input("CELL ID", placeholder="CELL ID লিখুন", key="s_cell_only").strip()
        elif selected_method == "BTS Address":
            address_val_in = st.text_input("BTS Address", placeholder="ঠিকানা বা এলাকার নাম লিখুন (যেমন: Uttara, Askona)", key="s_addr_only").strip()

        search_button = st.button("🔍 সার্চ করুন", type="primary", use_container_width=True, key="single_btn")

        if 'single_search_df' not in st.session_state:
            st.session_state['single_search_df'] = None

        if search_button:
            temp_df = df.copy()

            if selected_provider != "All Providers":
                prov_kw = {
                    "Grameenphone": ["gp", "grameen"],
                    "Robi And Airtel": ["robi", "airtel"],
                    "Banglalink": ["banglalink", "bl"],
                    "Teletalk": ["teletalk"]
                }.get(selected_provider, [])

                pattern = "|".join(prov_kw)
                temp_df = temp_df[temp_df[provider_col].astype(str).str.lower().str.contains(pattern, na=False)]

            s_lac = '_search_lac' if '_search_lac' in temp_df.columns else lac_col
            s_cell = '_search_cell' if '_search_cell' in temp_df.columns else cell_col

            if selected_method == "Lac & Cell":
                if lac_val_in and cell_val_in:
                    l_clean = lac_val_in.replace('.0', '')
                    c_clean = cell_val_in.replace('.0', '')
                    temp_df = temp_df[(temp_df[s_lac] == l_clean) & (temp_df[s_cell] == c_clean)]
                else:
                    st.warning("⚠️ LAC এবং CELL ID দুটিই দিন।")
                    temp_df = pd.DataFrame()
            elif selected_method == "LAC":
                if lac_val_in:
                    l_clean = lac_val_in.replace('.0', '')
                    temp_df = temp_df[temp_df[s_lac] == l_clean]
                else:
                    st.warning("⚠️ LAC প্রদান করুন।")
                    temp_df = pd.DataFrame()
            elif selected_method == "Cell ID":
                if cell_val_in:
                    c_clean = cell_val_in.replace('.0', '')
                    temp_df = temp_df[temp_df[s_cell] == c_clean]
                else:
                    st.warning("⚠️ CELL ID প্রদান করুন।")
                    temp_df = pd.DataFrame()
            elif selected_method == "BTS Address":
                if address_val_in and addr_col:
                    temp_df = temp_df[temp_df[addr_col].astype(str).str.lower().str.contains(address_val_in.lower(), na=False)]
                elif not addr_col:
                    st.error("⚠️ ডেটাসেটে কোনো Address কলাম খুঁজে পাওয়া যায়নি।")
                    temp_df = pd.DataFrame()
                else:
                    st.warning("⚠️ ঠিকানা বা এলাকার নাম লিখুন।")
                    temp_df = pd.DataFrame()

            st.session_state['single_search_df'] = temp_df

    # ------------------ ট্যাব ২: মাল্টি সার্চ (একাধিক সার্চ) ------------------
    with tab2:
        col1, col2 = st.columns(2)
        with col1: 
            lac_list_input = st.text_area("LAC সমূহ (কমা দিয়ে লিখুন):", value="", placeholder="46, 838, 1200", key="m_lac")
        with col2: 
            cell_list_input = st.text_area("CELL ID সমূহ (কমা দিয়ে লিখুন):", value="", placeholder="1945, 32271", key="m_cell")

        multi_search_button = st.button("🔍 একাধিক সার্চ করুন", type="primary", use_container_width=True, key="multi_btn")

        if 'multi_search_df' not in st.session_state:
            st.session_state['multi_search_df'] = None

        if multi_search_button:
            lacs = [x.strip().replace('.0', '') for x in lac_list_input.split(",") if x.strip()]
            cells = [x.strip().replace('.0', '') for x in cell_list_input.split(",") if x.strip()]

            s_lac = '_search_lac' if '_search_lac' in df.columns else lac_col
            s_cell = '_search_cell' if '_search_cell' in df.columns else cell_col

            if lacs and cells:
                search_pairs = set(zip(lacs, cells))
                st.session_state['multi_search_df'] = df[df.set_index([s_lac, s_cell]).index.isin(search_pairs)]
            elif lacs:
                st.session_state['multi_search_df'] = df[df[s_lac].isin(lacs)]
            elif cells:
                st.session_state['multi_search_df'] = df[df[s_cell].isin(cells)]
            else:
                st.session_state['multi_search_df'] = pd.DataFrame()

    filtered_df = st.session_state.get('single_search_df') if tab1 else st.session_state.get('multi_search_df')

    if filtered_df is None and st.session_state.get('multi_search_df') is not None:
        filtered_df = st.session_state.get('multi_search_df')

    if filtered_df is not None:
        if not filtered_df.empty:
            st.success(f"🎉 মোট {len(filtered_df)} টি তথ্য পাওয়া গেছে!")

            if len(filtered_df) == 1:
                row = filtered_df.iloc[0]
                st.subheader("📌 বিটিএস সাইট বিস্তারিত (Site Details)")

                lac_val = clean_val(row.get(lac_col))
                cell_val = clean_val(row.get(cell_col))
                dir_val = clean_val(row.get(dir_col, '0'))
                provider_val = str(row.get(provider_col, 'N/A'))
                lat_val_str = str(row.get(lat_col, 'N/A'))
                lon_val_str = str(row.get(lon_col, 'N/A'))
                address_val = str(row.get(addr_col, 'N/A')) if addr_col else "N/A"

                st.markdown(f"""
                <div class="site-card">
                    <div class="site-details-inline">
                        <div><strong>Provider:</strong> {provider_val}</div>
                        <div><strong>LAC:</strong> {lac_val}</div>
                        <div><strong>CELL ID:</strong> {cell_val}</div>
                        <div><strong>Direction:</strong> {dir_val}°</div>
                        <div><strong>Latitude:</strong> {lat_val_str}</div>
                        <div><strong>Longitude:</strong> {lon_val_str}</div>
                    </div>
                    <div class="site-address-text">
                        <strong>Site Address:</strong> {address_val}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                lat, lon = row.get(lat_col), row.get(lon_col)
                if pd.notnull(lat) and pd.notnull(lon):
                    try:
                        lat_val, lon_val = float(lat), float(lon)
                        st.markdown("---")
                        st.subheader("🗺️ লোকেশন ও ডিরেকশন ম্যাপ")
                        
                        m = folium.Map(location=[lat_val, lon_val], zoom_start=15, tiles=map_theme)
                        Fullscreen(position='topright').add_to(m)

                        color = get_operator_color(row.get(provider_col, ''))
                        label_text = f"{lac_val}|{cell_val}|{dir_val}°"

                        lbl_lat, lbl_lon = lat_val, lon_val
                        try:
                            azimuth_val = float(dir_val)
                            wedge_points, lbl_lat, lbl_lon = create_sector_wedge(
                                lat_val, lon_val, azimuth_val, distance_meters=sector_radius, beamwidth=beam_angle
                            )
                            folium.Polygon(locations=wedge_points, color=color, weight=2, fill=True, fill_color=color, fill_opacity=0.35).add_to(m)
                        except Exception:
                            pass

                        folium.Marker([lat_val, lon_val], icon=folium.Icon(color="red", icon="signal", prefix="fa")).add_to(m)
                        folium.Marker(
                            [lbl_lat, lbl_lon],
                            icon=folium.DivIcon(
                                html=f'''<div style="font-size: 11pt; font-weight: 800; color: #000; 
                                        background-color: #fff; border: 2px solid #222; padding: 4px 8px; 
                                        border-radius: 5px; text-align: center; box-shadow: 0px 3px 6px rgba(0,0,0,0.4); 
                                        white-space: nowrap; transform: translate(-50%, -50%); display: inline-block;">{label_text}</div>'''
                            )
                        ).add_to(m)
                        
                        st_folium(m, use_container_width=True, height=520, key="map_single")
                        st.markdown(f"### [🔗 Google map link](https://www.google.com/maps?q={lat_val},{lon_val})")
                    except ValueError:
                        st.error("Latitude/Longitude মান সঠিক নয়।")
            else:
                st.dataframe(filtered_df, use_container_width=True)
                if lat_col and lon_col:
                    map_df = filtered_df.dropna(subset=[lat_col, lon_col]).copy()
                    try:
                        map_df[lat_col] = map_df[lat_col].astype(float)
                        map_df[lon_col] = map_df[lon_col].astype(float)
                        records = map_df.to_dict('records')
                        
                        if len(records) > 0:
                            st.markdown("---")
                            st.subheader("🗺️ লোকেশন ও সেক্টর ডিরেকশন ম্যাপ")
                            
                            def haversine(lat1, lon1, lat2, lon2):
                                R = 6371.0
                                dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
                                a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
                                return R * 2 * asin(sqrt(a))

                            m = folium.Map(location=[records[0][lat_col], records[0][lon_col]], zoom_start=13, tiles=map_theme)
                            Fullscreen(position='topright').add_to(m)

                            coords = []
                            for row in records:
                                p_lat, p_lon = row[lat_col], row[lon_col]
                                color = get_operator_color(row.get(provider_col, ''))
                                coords.append({'lat': p_lat, 'lon': p_lon})

                                m_lac = clean_val(row.get(lac_col))
                                m_cell = clean_val(row.get(cell_col))
                                m_dir = clean_val(row.get(dir_col, '0'))

                                label_text = f"{m_lac}|{m_cell}|{m_dir}°"
                                lbl_lat, lbl_lon = p_lat, p_lon

                                try:
                                    azimuth_val = float(m_dir)
                                    wedge_points, lbl_lat, lbl_lon = create_sector_wedge(
                                        p_lat, p_lon, azimuth_val, distance_meters=sector_radius, beamwidth=beam_angle
                                    )
                                    folium.Polygon(locations=wedge_points, color=color, weight=2, fill=True, fill_color=color, fill_opacity=0.35).add_to(m)
                                except Exception:
                                    pass

                                folium.CircleMarker(location=[p_lat, p_lon], radius=7, color="#d9534f", fill=True, fill_color="#d9534f", fill_opacity=0.9).add_to(m)
                                folium.Marker(
                                    [lbl_lat, lbl_lon],
                                    icon=folium.DivIcon(
                                        html=f'''<div style="font-size: 10pt; font-weight: 800; color: #000; 
                                                background-color: #fff; border: 2px solid #222; padding: 3px 7px; 
                                                border-radius: 5px; text-align: center; box-shadow: 0px 3px 6px rgba(0,0,0,0.4); 
                                                white-space: nowrap; transform: translate(-50%, -50%); display: inline-block;">{label_text}</div>'''
                                    )
                                ).add_to(m)

                            for i in range(len(coords) - 1):
                                p1, p2 = coords[i], coords[i+1]
                                dist_km = haversine(p1['lat'], p1['lon'], p2['lat'], p2['lon'])
                                dist_str = f"📏 {int(dist_km * 1000)} M" if dist_km < 1.0 else f"📏 {dist_km:.2f} KM"
                                mid_lat, mid_lon = (p1['lat'] + p2['lat']) / 2, (p1['lon'] + p2['lon']) / 2

                                folium.PolyLine(locations=[[p1['lat'], p1['lon']], [p2['lat'], p2['lon']]], color="#0056b3", weight=4, opacity=0.85, dash_array='6, 6').add_to(m)
                                
                                folium.Marker(
                                    [mid_lat, mid_lon], 
                                    icon=folium.DivIcon(
                                        html=f'''<div style="font-size: 11pt; font-weight: 900; color: #000; 
                                                background-color: #ffffff; border: 2.5px solid #d9534f; padding: 4px 10px; 
                                                border-radius: 6px; text-align: center; box-shadow: 0px 4px 8px rgba(0,0,0,0.5); 
                                                white-space: nowrap; transform: translate(-50%, -50%); display: inline-block;">{dist_str}</div>'''
                                    )
                                ).add_to(m)

                            st_folium(m, use_container_width=True, height=520, key="map_multi")

                            origin = f"{coords[0]['lat']},{coords[0]['lon']}"
                            destination = f"{coords[-1]['lat']},{coords[-1]['lon']}"
                            
                            if len(coords) > 2:
                                waypoints = "|".join([f"{c['lat']},{c['lon']}" for c in coords[1:-1]])
                                multi_gmap_link = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&waypoints={waypoints}&travelmode=driving"
                            elif len(coords) == 2:
                                multi_gmap_link = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}&travelmode=driving"
                            else:
                                multi_gmap_link = f"https://www.google.com/maps?q={origin}"

                            st.markdown(f"### [🔗 Google map link (সকল লোকেশন একসাথে)]({multi_gmap_link})")

                    except Exception as e:
                        st.error(f"ম্যাপ প্রদর্শনে সমস্যা হয়েছে: {e}")
        else:
            st.error("❌ কোনো তথ্য পাওয়া যায়নি।")

else:
    st.info("👈 ফোল্ডারে কোনো ডেটা ফাইল পাওয়া যায়নি।")
