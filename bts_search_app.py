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
st.set_page_config(
    page_title="Location Finder Dashboard", 
    page_icon="📡", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ২. কাস্টম প্রফেশনাল সিএসএস
st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            display: none !important;
        }
        [data-testid="stSidebarCollapsedControl"] {
            display: none !important;
        }

        #MainMenu, footer, [data-testid="stStatusWidget"], .viewerBadge_container__1A5G2 {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
        }

        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 1rem !important;
            max-width: 100% !important;
        }

        /* ছোট ও প্রফেশনাল স্লাইডার কার্ড */
        .slider-card {
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 4px 12px;
            margin-bottom: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }

        .stSlider label {
            font-size: 11px !important;
            font-weight: 600 !important;
            color: #38bdf8 !important;
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

st.title("📡 Location Finder Dashboard")
st.write("সহজ ও দ্রুত উপায়ে লাখ লাখ বিটিএস ডেটা থেকে অনুসন্ধান করুন।[cite: 10]")

@st.cache_data(show_spinner="ডেটা প্রক্রিয়াকরণ হচ্ছে...")
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
    prov = str(provider_name).lower().strip()
    
    if any(x in prov for x in ['gp', 'grameen', 'grameenphone']):
        return '#00a3e0'
    elif 'robi' in prov or 'airtel' in prov:
        return '#ea4335'
    elif any(x in prov for x in ['bl', 'banglalink']):
        return '#ff6600'
    elif any(x in prov for x in ['teletalk', 'tl']):
        return '#28a745'
    else:
        return '#ea4335'

def create_sector_wedge(lat, lon, azimuth, distance_meters=600, beamwidth=90):
    points = [[lat, lon]]
    start_angle = azimuth - (beamwidth / 2)
    end_angle = azimuth + (beamwidth / 2)
    
    for angle in range(int(start_angle), int(end_angle) + 1, 5):
        rad = math.radians(angle)
        d_lat = (distance_meters * math.cos(rad)) / 111320.0
        d_lon = (distance_meters * math.sin(rad)) / (111320.0 * math.cos(math.radians(lat)))
        points.append([lat + d_lat, lon + d_lon])
        
    points.append([lat, lon])
    
    target_rad = math.radians(azimuth)
    target_lat = lat + ((distance_meters * math.cos(target_rad)) / 111320.0)
    target_lon = lon + ((distance_meters * math.sin(target_rad)) / (111320.0 * math.cos(math.radians(lat))))
    
    label_dist = distance_meters * 0.55
    label_lat = lat + ((label_dist * math.cos(target_rad)) / 111320.0)
    label_lon = lon + ((label_dist * math.sin(target_rad)) / (111320.0 * math.cos(math.radians(lat))))
    
    return points, label_lat, label_lon, target_lat, target_lon

def clean_val(val):
    if pd.isna(val) or val is None or str(val).strip() == "":
        return "N/A"
    try:
        f = float(val)
        if f.is_integer():
            return str(int(f))
        return str(f)
    except Exception:
        return str(val).replace('.0', '', regex=True)

# ------------------ অটো ফাইল লোড (ফোল্ডার থেকে) ------------------
df = None
all_files = glob.glob("*.parquet") + glob.glob("*.csv") + glob.glob("*.xlsx") + glob.glob("*.xls")

if all_files:
    try:
        df = load_data_optimized(all_files[0])
    except Exception:
        pass

def render_folium_map(center_lat=23.8103, center_lon=90.4125, zoom=11):
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, max_zoom=21, tiles=None)
    
    folium.TileLayer('OpenStreetMap', name='Street').add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite'
    ).add_to(m)
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
        attr='Google',
        name='Hybrid'
    ).add_to(m)
    
    Fullscreen(position='topright').add_to(m)
    folium.LayerControl(position='topleft', collapsed=False).add_to(m)
    return m

# ------------------ মূল সার্চ ইন্টারফেস ------------------
if df is not None:
    col_names = df.columns.tolist()

    lac_col = next((c for c in col_names if 'lac' in c.lower() and c != '_search_lac'), col_names[0])
    cell_col = next((c for c in col_names if 'cell' in c.lower() and c != '_search_cell'), col_names[0])
    provider_col = next((c for c in col_names if any(x in c.lower() for x in ['provider', 'operator', 'company'])), col_names[0])
    dir_col = next((c for c in col_names if 'dir' in c.lower()), None)
    lat_col = next((c for c in col_names if 'lat' in c.lower()), None)
    lon_col = next((c for c in col_names if 'lon' in c.lower() or 'lng' in c.lower()), None)
    addr_col = next((c for c in col_names if any(x in c.lower() for x in ['address', 'site', 'location'])), None)

    tab1, tab2 = st.tabs(["🔍 Tower Search (Single)", "📑 Multiple Search (একাধিক সার্চ)"])

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
                lac_num = st.number_input("LAC", value=None, step=1, format="%d", placeholder="LAC লিখুন", key="s_lac")
                lac_val_in = str(int(lac_num)) if lac_num is not None else ""
            with i_col2:
                cell_num = st.number_input("Cell ID", value=None, step=1, format="%d", placeholder="CELL ID লিখুন", key="s_cell")
                cell_val_in = str(int(cell_num)) if cell_num is not None else ""
        elif selected_method == "LAC":
            lac_num = st.number_input("LAC", value=None, step=1, format="%d", placeholder="LAC লিখুন", key="s_lac_only")
            lac_val_in = str(int(lac_num)) if lac_num is not None else ""
        elif selected_method == "Cell ID":
            cell_num = st.number_input("CELL ID", value=None, step=1, format="%d", placeholder="CELL ID লিখুন", key="s_cell_only")
            cell_val_in = str(int(cell_num)) if cell_num is not None else ""
        elif selected_method == "BTS Address":
            address_val_in = st.text_input("BTS Address", placeholder="ঠিকানা বা এলাকার নাম লিখুন", key="s_addr_only").strip()

        search_button = st.button("🔍 সার্চ করুন", type="primary", use_container_width=True, key="single_btn")

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

            st.session_state['active_search_result'] = temp_df

    with tab2:
        col1, col2 = st.columns(2)
        with col1: 
            lac_list_input = st.text_area("LAC সমূহ (কমা দিয়ে লিখুন):", value="", placeholder="24051, 24051", key="m_lac")
        with col2: 
            cell_list_input = st.text_area("CELL ID সমূহ (কমা দিয়ে লিখুন):", value="", placeholder="55408, 55409", key="m_cell")

        multi_search_button = st.button("🔍 একাধিক সার্চ করুন", type="primary", use_container_width=True, key="multi_btn")

        if multi_search_button:
            lacs = [x.strip().replace('.0', '') for x in lac_list_input.split(",") if x.strip()]
            cells = [x.strip().replace('.0', '') for x in cell_list_input.split(",") if x.strip()]

            s_lac = '_search_lac' if '_search_lac' in df.columns else lac_col
            s_cell = '_search_cell' if '_search_cell' in df.columns else cell_col

            if lacs and cells:
                if len(lacs) == len(cells):
                    search_pairs = set(zip(lacs, cells))
                    conditions = pd.Series(False, index=df.index)
                    for l, c in search_pairs:
                        conditions |= ((df[s_lac] == l) & (df[s_cell] == c))
                    res_df = df[conditions]
                else:
                    res_df = df[(df[s_lac].isin(lacs)) & (df[s_cell].isin(cells))]
            elif lacs:
                res_df = df[df[s_lac].isin(lacs)]
            elif cells:
                res_df = df[df[s_cell].isin(cells)]
            else:
                res_df = pd.DataFrame()

            st.session_state['active_search_result'] = res_df

    # রেজাল্ট প্রদর্শন (যদি থাকে)
    filtered_df = st.session_state.get('active_search_result', None)

    if filtered_df is not None and not filtered_df.empty:
        st.success(f"🎉 মোট {len(filtered_df)} টি তথ্য পাওয়া গেছে![cite: 10]")

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

    st.markdown("---")

    # 🟢 কলাম ব্যবহার করে স্লাইডারটিকে ছোট এবং সুনির্দিষ্ট আকারে ম্যাপের ওপরে রাখা হলো
    col_s1, col_s2, col_s3 = st.columns([1, 2, 1])
    with col_s1:
        st.markdown('<div class="slider-card">', unsafe_allow_html=True)
        sector_radius = st.slider("সেক্টর কাভারেজ (মিটার):", min_value=100, max_value=1500, value=600, step=50, key="map_sec_rad")
        beam_angle = 90  # সেক্টর অ্যাঙ্গেল স্থায়ীভাবে ৯০ ডিগ্রি ফিক্সড
        st.markdown('</div>', unsafe_allow_html=True)

    # ম্যাপ রেন্ডারিং অংশ
    if filtered_df is not None and not filtered_df.empty:
        if len(filtered_df) == 1:
            row = filtered_df.iloc[0]
            lat, lon = row.get(lat_col), row.get(lon_col)
            if pd.notnull(lat) and pd.notnull(lon):
                try:
                    lat_val, lon_val = float(lat), float(lon)
                    m = render_folium_map(lat_val, lon_val, zoom=16)

                    pin_color = get_operator_color(row.get(provider_col, ''))
                    lac_val = clean_val(row.get(lac_col))
                    cell_val = clean_val(row.get(cell_col))
                    dir_val = clean_val(row.get(dir_col, '0'))
                    label_text = f"LAC: {lac_val}<br>Cell: {cell_val}<br>Az: {dir_val}°"

                    lbl_lat, lbl_lon = lat_val, lon_val
                    try:
                        azimuth_val = float(dir_val)
                        wedge_points, lbl_lat, lbl_lon, target_lat, target_lon = create_sector_wedge(
                            lat_val, lon_val, azimuth_val, distance_meters=sector_radius, beamwidth=beam_angle
                        )
                        folium.Polygon(locations=wedge_points, color=pin_color, weight=3, fill=True, fill_color=pin_color, fill_opacity=0.40).add_to(m)
                        
                        folium.PolyLine(
                            locations=[[lat_val, lon_val], [target_lat, target_lon]],
                            color="#FFD700",
                            weight=4,
                            opacity=0.9
                        ).add_to(m)
                        folium.RegularPolygonMarker(
                            location=[target_lat, target_lon],
                            fill_color="#FFD700",
                            color="#FFD700",
                            number_of_sides=3,
                            radius=12,
                            rotation=azimuth_val - 90
                        ).add_to(m)
                    except Exception:
                        pass

                    pin_html = f'''<div style="width:32px; height:42px; transform:translate(-50%, -100%);">
                        <svg viewBox="0 0 384 512" width="32" height="42">
                            <path fill="{pin_color}" stroke="#ffffff" stroke-width="15" d="M172.268 501.67 C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                            <circle cx="192" cy="192" r="70" fill="#ffffff"/>
                        </svg>
                    </div>'''
                    folium.Marker([lat_val, lon_val], icon=folium.DivIcon(html=pin_html)).add_to(m)
                    folium.Marker(
                        [lbl_lat, lbl_lon],
                        icon=folium.DivIcon(
                            html=f'''<div style="font-size: 10pt; font-weight: 800; color: #fff; 
                                    background-color: #0d1b2a; border: 2px solid #00a8e8; padding: 6px 10px; 
                                    border-radius: 6px; text-align: left; box-shadow: 0px 4px 8px rgba(0,0,0,0.5); 
                                    white-space: nowrap; transform: translate(-50%, -50%); display: inline-block;">{label_text}</div>'''
                        )
                    ).add_to(m)
                    
                    st_folium(m, use_container_width=True, height=550, key="map_single")
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
                        def haversine(lat1, lon1, lat2, lon2):
                            R = 6371.0
                            dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
                            a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
                            return R * 2 * asin(sqrt(a))

                        m = render_folium_map(records[0][lat_col], records[0][lon_col], zoom=14)
                        coords = []
                        all_bounds = []

                        for row in records:
                            p_lat, p_lon = row[lat_col], row[lon_col]
                            pin_color = get_operator_color(row.get(provider_col, ''))
                            coords.append({'lat': p_lat, 'lon': p_lon})
                            all_bounds.append([p_lat, p_lon])

                            m_lac = clean_val(row.get(lac_col))
                            m_cell = clean_val(row.get(cell_col))
                            m_dir = clean_val(row.get(dir_col, '0'))
                            label_text = f"LAC: {m_lac}<br>Cell: {m_cell}<br>Az: {m_dir}°"
                            lbl_lat, lbl_lon = p_lat, p_lon

                            try:
                                azimuth_val = float(m_dir)
                                wedge_points, lbl_lat, lbl_lon, target_lat, target_lon = create_sector_wedge(
                                    p_lat, p_lon, azimuth_val, distance_meters=sector_radius, beamwidth=beam_angle
                                )
                                folium.Polygon(locations=wedge_points, color=pin_color, weight=3, fill=True, fill_color=pin_color, fill_opacity=0.40).add_to(m)
                                
                                folium.PolyLine(
                                    locations=[[p_lat, p_lon], [target_lat, target_lon]],
                                    color="#FFD700",
                                    weight=4,
                                    opacity=0.9
                                ).add_to(m)
                                folium.RegularPolygonMarker(
                                    location=[target_lat, target_lon],
                                    fill_color="#FFD700",
                                    color="#FFD700",
                                    number_of_sides=3,
                                    radius=12,
                                    rotation=azimuth_val - 90
                                ).add_to(m)
                            except Exception:
                                pass

                            pin_html = f'''<div style="width:32px; height:42px; transform:translate(-50%, -100%);">
                                <svg viewBox="0 0 384 512" width="32" height="42">
                                    <path fill="{pin_color}" stroke="#ffffff" stroke-width="15" d="M172.268 501.67 C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                                    <circle cx="192" cy="192" r="70" fill="#ffffff"/>
                                </svg>
                            </div>'''
                            folium.Marker([p_lat, p_lon], icon=folium.DivIcon(html=pin_html)).add_to(m)
                            folium.Marker(
                                [lbl_lat, lbl_lon],
                                icon=folium.DivIcon(
                                    html=f'''<div style="font-size: 10pt; font-weight: 800; color: #fff; 
                                            background-color: #0d1b2a; border: 2px solid #00a8e8; padding: 6px 10px; 
                                            border-radius: 6px; text-align: left; box-shadow: 0px 4px 8px rgba(0,0,0,0.5); 
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

                        if len(all_bounds) > 1:
                            m.fit_bounds(all_bounds, padding=[80, 80])

                        st_folium(m, use_container_width=True, height=550, key="map_multi")
                except Exception as e:
                    st.error(f"ম্যাপ প্রদর্শনে সমস্যা হয়েছে: {e}")
    else:
        # সার্চ না করা থাকলে ডিফল্ট বাংলাদেশ কেন্দ্রিক ম্যাপ দেখাবে
        default_map = render_folium_map(center_lat=23.8103, center_lon=90.4125, zoom=11)
        st_folium(default_map, use_container_width=True, height=550, key="default_blank_map")

else:
    st.info("👈 ফোল্ডারে কোনো ডেটা ফাইল পাওয়া যায়নি।")
