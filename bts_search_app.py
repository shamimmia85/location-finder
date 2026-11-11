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

        textarea[data-baseweb="textarea"] {
            overflow-y: hidden !important;
            overflow-x: hidden !important;
            height: auto !important;
            min-height: 180px !important;
            max-height: none !important;
            resize: none !important;
            padding-top: 12px !important;
            padding-bottom: 12px !important;
            line-height: 1.6 !important;
        }

        .slider-box {
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 8px 14px;
            margin-top: 5px;
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
st.write("সহজ ও দ্রুত উপায়ে লাখ লাখ বিটিএস ডেটা থেকে অনুসন্ধান করুন।")

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
    
    label_dist = distance_meters * 0.65
    label_lat = lat + ((label_dist * math.cos(target_rad)) / 111320.0)
    label_lon = lon + ((label_dist * math.sin(target_rad)) / (111320.0 * math.cos(math.radians(lat))))
    
    return points, label_lat, label_lon, target_lat, target_lon

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return R * 2 * asin(sqrt(a))

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

# ------------------ মূল সার্চ ড্যাশবোর্ড ইন্টারফেস ------------------
if df is not None:
    col_names = df.columns.tolist()

    lac_col = next((c for c in col_names if 'lac' in c.lower() and c != '_search_lac'), col_names[0])
    cell_col = next((c for c in col_names if 'cell' in c.lower() and c != '_search_cell'), col_names[0])
    provider_col = next((c for c in col_names if any(x in c.lower() for x in ['provider', 'operator', 'company'])), col_names[0])
    dir_col = next((c for c in col_names if 'dir' in c.lower()), None)
    lat_col = next((c for c in col_names if 'lat' in c.lower()), None)
    lon_col = next((c for c in col_names if 'lon' in c.lower() or 'lng' in c.lower()), None)
    addr_col = next((c for c in col_names if any(x in c.lower() for x in ['address', 'site', 'location'])), None)

    st.subheader("Tower search")
    
    search_col, _ = st.columns([1, 1])
    
    with search_col:
        scol1, scol2 = st.columns(2)
        with scol1:
            selected_provider = st.selectbox(
                "Provider", 
                ["All Providers", "Grameenphone", "Robi And Airtel", "Banglalink", "Teletalk"],
                key="single_prov"
            )
        with scol2:
            method_options = ["Lac & Cell", "LAC", "Cell ID", "BTS Address"]
            selected_method = st.selectbox("Search method", method_options, key="single_method")

        user_input_text = st.session_state.get('search_text_input', '')
        line_count = max(6, user_input_text.count('\n') + 1)
        dynamic_height = min(max(180, line_count * 30), 1000)

        search_query = st.text_area("Search text", placeholder="LAC or CELLID (যেমন: 30425 14370)", key="search_text_input", height=dynamic_height)
        search_button = st.button("🔍 Search", type="primary", use_container_width=True, key="single_btn")

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

        cleaned_query = search_query.strip()
        if cleaned_query:
            if selected_method == "Lac & Cell":
                lines = [line.strip() for line in cleaned_query.split('\n') if line.strip()]
                pairs = []
                for line in lines:
                    parts = line.replace(',', ' ').split()
                    if len(parts) >= 2:
                        pairs.append((parts[0].replace('.0', ''), parts[1].replace('.0', '')))
                
                if pairs:
                    conditions = pd.Series(False, index=temp_df.index)
                    for l, c in pairs:
                        conditions |= ((temp_df[s_lac] == l) & (temp_df[s_cell] == c))
                    temp_df = temp_df[conditions]
                else:
                    parts = cleaned_query.replace(',', ' ').split()
                    if len(parts) >= 2:
                        l_clean = parts[0].replace('.0', '')
                        c_clean = parts[1].replace('.0', '')
                        temp_df = temp_df[(temp_df[s_lac] == l_clean) & (temp_df[s_cell] == c_clean)]
                    else:
                        st.warning("⚠️ সঠিক ফরম্যাটে LAC এবং Cell ID দিন (যেমন: 30425 14370)")
                        temp_df = pd.DataFrame()

            elif selected_method == "LAC":
                lacs = [x.strip().replace('.0', '') for x in cleaned_query.replace(',', '\n').split('\n') if x.strip()]
                temp_df = temp_df[temp_df[s_lac].isin(lacs)]

            elif selected_method == "Cell ID":
                cells = [x.strip().replace('.0', '') for x in cleaned_query.replace(',', '\n').split('\n') if x.strip()]
                temp_df = temp_df[temp_df[s_cell].isin(cells)]

            elif selected_method == "BTS Address":
                if addr_col:
                    temp_df = temp_df[temp_df[addr_col].astype(str).str.lower().str.contains(cleaned_query.lower(), na=False)]
                else:
                    st.error("⚠️ ডেটাসেটে কোনো Address কলাম খুঁজে পাওয়া যায়নি।")
                    temp_df = pd.DataFrame()
        else:
            st.warning("⚠️ অনুগ্রহ করে সার্চ টেক্সট লিখুন।")
            temp_df = pd.DataFrame()

        st.session_state['active_search_result'] = temp_df

    # রেজাল্ট প্রদর্শন (যদি থাকে)
    filtered_df = st.session_state.get('active_search_result', None)

    if filtered_df is not None and not filtered_df.empty:
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

    st.markdown("---")

    # স্লাইডার কলাম বক্স
    col_s1, col_s2 = st.columns([1, 2])
    with col_s1:
        st.markdown('<div class="slider-box">', unsafe_allow_html=True)
        sector_radius = st.slider("সেক্টর কাভারেজ (মিটার):", min_value=100, max_value=1500, value=600, step=50, key="map_sec_rad")
        beam_angle = 90  
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
                    
                    label_text = f"{lac_val}|{cell_val}|{dir_val}°"

                    lbl_lat, lbl_lon = lat_val, lon_val
                    try:
                        azimuth_val = float(dir_val)
                        wedge_points, lbl_lat, lbl_lon, target_lat, target_lon = create_sector_wedge(
                            lat_val, lon_val, azimuth_val, distance_meters=sector_radius, beamwidth=beam_angle
                        )
                        folium.Polygon(locations=wedge_points, color=pin_color, weight=3, fill=True, fill_color=pin_color, fill_opacity=0.40).add_to(m)
                        
                        # 🔴 পিন পয়েন্ট থেকে নির্দিষ্ট দূরত্বে (যেমন ২০০ মিটার দূরে বা হলুদ লাইনের ওপর) ছোট লাল বৃত্ত যোগ করা হলো
                        circle_dist = 200 # মিটার দূরত্ব
                        c_rad = math.radians(azimuth_val)
                        c_lat = lat_val + ((circle_dist * math.cos(c_rad)) / 111320.0)
                        c_lon = lon_val + ((circle_dist * math.sin(c_rad)) / (111320.0 * math.cos(math.radians(lat_val))))

                        folium.CircleMarker(
                            location=[c_lat, c_lon],
                            radius=8,
                            color='#ff0000',
                            weight=2,
                            fill=True,
                            fill_color='#ff0000',
                            fill_opacity=0.8
                        ).add_to(m)

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

                    pin_html = f'''<div style="width:28px; height:38px; transform:translate(-10px, -30px);">
                        <svg viewBox="0 0 384 512" width="28" height="38">
                            <path fill="{pin_color}" stroke="#ffffff" stroke-width="12" d="M172.268 501.67 C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                            <circle cx="192" cy="192" r="70" fill="#ffffff"/>
                        </svg>
                    </div>'''
                    folium.Marker([lat_val, lon_val], icon=folium.DivIcon(html=pin_html)).add_to(m)
                    
                    folium.Marker(
                        [lbl_lat, lbl_lon],
                        icon=folium.DivIcon(
                            html=f'''<div style="font-size: 11pt; font-weight: 600; color: #000000; 
                                    background-color: #ffffff; border: 1px solid #94a3b8; padding: 4px 12px; 
                                    border-radius: 6px; text-align: center; box-shadow: 0px 2px 4px rgba(0,0,0,0.2); 
                                    white-space: nowrap; writing-mode: horizontal-tb; transform: translate(-50%, -50%); display: inline-block;">{label_text}</div>'''
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
                            
                            label_text = f"{m_lac}|{m_cell}|{m_dir}°"
                            lbl_lat, lbl_lon = p_lat, p_lon

                            try:
                                azimuth_val = float(m_dir)
                                wedge_points, lbl_lat, lbl_lon, target_lat, target_lon = create_sector_wedge(
                                    p_lat, p_lon, azimuth_val, distance_meters=sector_radius, beamwidth=beam_angle
                                )
                                folium.Polygon(locations=wedge_points, color=pin_color, weight=3, fill=True, fill_color=pin_color, fill_opacity=0.40).add_to(m)
                                
                                # 🔴 মাল্টিপল রেজাল্টের ক্ষেত্রেও নির্দিষ্ট দূরত্বে ছোট লাল বৃত্ত যোগ করা হলো
                                circle_dist = 200
                                c_rad = math.radians(azimuth_val)
                                c_lat = p_lat + ((circle_dist * math.cos(c_rad)) / 111320.0)
                                c_lon = p_lon + ((circle_dist * math.sin(c_rad)) / (111320.0 * math.cos(math.radians(p_lat))))

                                folium.CircleMarker(
                                    location=[c_lat, c_lon],
                                    radius=8,
                                    color='#ff0000',
                                    weight=2,
                                    fill=True,
                                    fill_color='#ff0000',
                                    fill_opacity=0.8
                                ).add_to(m)

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

                            pin_html = f'''<div style="width:28px; height:38px; transform:translate(-10px, -30px);">
                                <svg viewBox="0 0 384 512" width="28" height="38">
                                    <path fill="{pin_color}" stroke="#ffffff" stroke-width="12" d="M172.268 501.67 C26.97 291.031 0 269.413 0 192 0 85.961 85.961 0 192 0s192 85.961 192 192c0 77.413-26.97 99.031-172.268 309.67-9.535 13.774-29.93 13.773-39.464 0z"/>
                                    <circle cx="192" cy="192" r="70" fill="#ffffff"/>
                                </svg>
                            </div>'''
                            folium.Marker([p_lat, p_lon], icon=folium.DivIcon(html=pin_html)).add_to(m)
                            folium.Marker(
                                [lbl_lat, lbl_lon],
                                icon=folium.DivIcon(
                                    html=f'''<div style="font-size: 11pt; font-weight: 600; color: #000000; 
                                            background-color: #ffffff; border: 1px solid #94a3b8; padding: 4px 12px; 
                                            border-radius: 6px; text-align: center; box-shadow: 0px 2px 4px rgba(0,0,0,0.2); 
                                            white-space: nowrap; writing-mode: horizontal-tb; transform: translate(-50%, -50%); display: inline-block;">{label_text}</div>'''
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
        default_map = render_folium_map(center_lat=23.8103, center_lon=90.4125, zoom=11)
        st_folium(default_map, use_container_width=True, height=550, key="default_blank_map")

else:
    st.info("👈 ফোল্ডারে কোনো ডেটা ফাইল পাওয়া যায়নি।")
