import ee
import streamlit as st
import geemap.foliumap as geemap
import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import json
from google.oauth2 import service_account

# -----------------------------------------------------------------------------
# 1. App Setup and Configuration
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="Backwater Guardian",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for loading animation
if 'app_loaded' not in st.session_state:
    st.session_state.app_loaded = False

# Loading Animation
if not st.session_state.app_loaded:
    st.markdown("""
    <style>
        .stApp > header {display: none;}
        .block-container {padding: 0 !important; max-width: 100% !important;}
        
        .splash-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            animation: fadeOut 0.5s ease-out 3s forwards;
        }
        
        .water-drop-container {
            position: relative;
            width: 200px;
            height: 200px;
            margin-bottom: 40px;
        }
        
        .water-drop {
            position: absolute;
            width: 120px;
            height: 120px;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
            background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%);
            border-radius: 50% 50% 50% 0;
            transform-origin: center;
            animation: dropRotate 2s ease-in-out infinite;
            box-shadow: 0 10px 40px rgba(0, 212, 255, 0.4);
        }
        
        .water-drop::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 80px;
            height: 80px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 50%;
            animation: pulse 2s ease-in-out infinite;
        }
        
        .ripple {
            position: absolute;
            width: 200px;
            height: 200px;
            border: 2px solid rgba(0, 212, 255, 0.6);
            border-radius: 50%;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            animation: ripple 2s ease-out infinite;
        }
        
        .ripple:nth-child(2) {
            animation-delay: 0.5s;
        }
        
        .ripple:nth-child(3) {
            animation-delay: 1s;
        }
        
        .splash-title {
            font-size: 3rem;
            font-weight: 700;
            color: #00d4ff;
            margin-bottom: 15px;
            animation: fadeInUp 1s ease-out;
            text-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
            letter-spacing: 2px;
        }
        
        .splash-subtitle {
            font-size: 1.3rem;
            color: #8ec5d4;
            margin-bottom: 40px;
            animation: fadeInUp 1s ease-out 0.3s both;
            letter-spacing: 1px;
        }
        
        .loading-bar-container {
            width: 300px;
            height: 4px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            overflow: hidden;
            animation: fadeInUp 1s ease-out 0.6s both;
        }
        
        .loading-bar {
            height: 100%;
            background: linear-gradient(90deg, #00d4ff 0%, #0099cc 50%, #00d4ff 100%);
            background-size: 200% 100%;
            animation: loadingBar 2s ease-in-out infinite;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0, 212, 255, 0.8);
        }
        
        .loading-text {
            margin-top: 20px;
            color: #8ec5d4;
            font-size: 0.9rem;
            animation: fadeInUp 1s ease-out 0.9s both, blink 1.5s ease-in-out infinite;
            letter-spacing: 2px;
        }
        
        @keyframes dropRotate {
            0%, 100% { transform: translate(-50%, -50%) rotate(45deg); }
            50% { transform: translate(-50%, -50%) rotate(405deg); }
        }
        
        @keyframes pulse {
            0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.3; }
            50% { transform: translate(-50%, -50%) scale(1.2); opacity: 0.6; }
        }
        
        @keyframes ripple {
            0% {
                transform: translate(-50%, -50%) scale(0.5);
                opacity: 1;
            }
            100% {
                transform: translate(-50%, -50%) scale(1.5);
                opacity: 0;
            }
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes loadingBar {
            0% { background-position: 200% 0; width: 0%; }
            50% { width: 100%; }
            100% { background-position: -200% 0; width: 100%; }
        }
        
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        @keyframes fadeOut {
            to {
                opacity: 0;
                visibility: hidden;
            }
        }
    </style>
    
    <div class="splash-container">
        <div class="water-drop-container">
            <div class="ripple"></div>
            <div class="ripple"></div>
            <div class="ripple"></div>
            <div class="water-drop"></div>
        </div>
        <div class="splash-title">💧 BACKWATER GUARDIAN</div>
        <div class="splash-subtitle">Vembanad Lake Health Monitor</div>
        <div class="loading-bar-container">
            <div class="loading-bar"></div>
        </div>
        <div class="loading-text">INITIALIZING SATELLITE DATA...</div>
    </div>
    
    <script>
        setTimeout(function() {
            window.parent.postMessage({type: 'streamlit:setComponentValue', value: true}, '*');
        }, 3500);
    </script>
    """, unsafe_allow_html=True)
    
    import time
    time.sleep(3.5)
    st.session_state.app_loaded = True
    st.rerun()

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(120deg, #1e3c72 0%, #2a5298 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .info-box {
        background: #f0f8ff;
        padding: 1rem;
        border-left: 4px solid #2196F3;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .warning-box {
        background: #fff3cd;
        padding: 1rem;
        border-left: 4px solid #ff9800;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        padding: 0 2rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">💧 Backwater Guardian: Vembanad Lake Health Monitor</h1>', unsafe_allow_html=True)

# Important disclaimer at the top
st.warning("""
⚠️ **IMPORTANT NOTICE:** This tool displays **spectral indices** derived from satellite imagery, not direct water quality measurements. 
Values shown are relative indicators that require ground-truth validation for quantitative interpretation. Use this as a screening tool 
to identify areas that may need detailed field investigation.
""")

# -----------------------------------------------------------------------------
# 2. Earth Engine Initialization
# -----------------------------------------------------------------------------


@st.cache_resource
def initialize_ee():
    """Initializes Google Earth Engine using service account credentials."""
    try:
        st.write("🔄 Initializing Google Earth Engine...")

        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])

            # ✅ Define required Earth Engine OAuth scope
            SCOPES = ["https://www.googleapis.com/auth/earthengine.readonly"]

            # Build credentials with explicit scope
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=SCOPES
            )

            ee.Initialize(credentials)
            st.success("✅ Earth Engine initialized successfully (Service Account).")

        else:
            st.warning("⚠️ No service account found, using local auth fallback...")
            ee.Initialize(project="backwater-guard")

        return True

    except Exception as e:
        st.error(f"❌ Earth Engine initialization failed: {e}")
        st.info("""
        For local testing:
        Run `earthengine authenticate` in your terminal before launching Streamlit.

        For deployment (Streamlit Cloud):
        Make sure `[gcp_service_account]` is added under **Settings → Secrets**,
        and that the service account is registered for Google Earth Engine access.
        """)
        return False


# --- Main execution block ---

ee_initialized = initialize_ee()

if not ee_initialized:
    st.stop()

# Safe to define AOI after initialization
AOI = ee.Geometry.Rectangle([76.25, 9.9, 76.45, 10.1])

# -----------------------------------------------------------------------------
# 3. Enhanced Analysis Functions
# -----------------------------------------------------------------------------

def mask_s2_clouds(image):
    """Cloud masking using Sentinel-2 QA60 band."""
    qa = image.select('QA60')
    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11
    mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
    scaled_optical = image.select('B.*').divide(10000)
    return scaled_optical.updateMask(mask).copyProperties(image, ["system:time_start"])

@st.cache_data(ttl=3600)
def get_sentinel2_image(_aoi, months_back=3):
    """
    Builds a median composite from recent Sentinel-2 imagery.
    Uses NDWI for water detection with thresholds tuned for Vembanad Lake.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
        .filterDate(ee.Date(now).advance(-months_back, 'month'), ee.Date(now)) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
        .filterBounds(_aoi) \
        .map(mask_s2_clouds)
    
    collection_size = collection.size().getInfo()
    if collection_size == 0:
        return None, None, collection_size
    
    latest_image = collection.median().clip(_aoi)
    
    # NDWI water mask (McFeeters 1996)
    ndwi = latest_image.normalizedDifference(['B3', 'B8']).rename('ndwi')
    nir = latest_image.select('B8')
    water_mask = ndwi.gt(0.1).And(nir.lt(0.15))
    
    return latest_image, water_mask, collection_size

@st.cache_data
def get_chlorophyll_map(_image, _water_mask):
    """
    Chlorophyll proxy using NDCI (Normalized Difference Chlorophyll Index).
    
    Method: NDCI = (B5 - B4) / (B5 + B4)
    Reference: Mishra & Mishra (2012)
    
    Note: This is a relative index, NOT chlorophyll-a concentration (mg/L).
    Higher values indicate greater algal biomass.
    """
    ndci = _image.normalizedDifference(['B5', 'B4']).rename('ndci')
    
    # Classification into relative categories
    classified_image = (
        ndci.where(ndci.lte(0.0), 1)    # Very Low
        .where(ndci.gt(0.0).And(ndci.lte(0.1)), 2)   # Low
        .where(ndci.gt(0.1).And(ndci.lte(0.2)), 3)   # Moderate
        .where(ndci.gt(0.2), 4)         # High
    )
    return classified_image.updateMask(_water_mask), ndci.updateMask(_water_mask)

@st.cache_data
def get_turbidity_map(_image, _water_mask):
    """
    Turbidity proxy using red band reflectance.
    
    Method: Higher red band reflectance correlates with suspended particles.
    This identifies the top 15% most turbid areas as hotspots.
    
    Note: Values are unitless reflectance, NOT NTU (Nephelometric Turbidity Units).
    Requires local calibration for quantitative interpretation.
    """
    # Using red band as turbidity indicator (simplified Nechad approach)
    red_band = _image.select('B4').rename('turbidity')
    turbidity_on_water = red_band.updateMask(_water_mask)
    
    # Identify top 15% as hotspots
    percentile = turbidity_on_water.reduceRegion(
        reducer=ee.Reducer.percentile([85]), 
        geometry=AOI, 
        scale=30, 
        maxPixels=1e9
    ).get('turbidity')
    
    hotspots = ee.Image(ee.Algorithms.If(
        percentile, 
        turbidity_on_water.gte(ee.Number(percentile)).selfMask(), 
        ee.Image(0).selfMask()
    ))
    
    return hotspots, turbidity_on_water

@st.cache_data
def get_floating_matter_map(_image, _water_mask):
    """
    NIR anomaly detection over water surfaces.
    
    Method: Clean water absorbs NIR; high NIR indicates surface anomalies.
    This identifies the top 5% highest NIR areas.
    
    CAUTION: High NIR can indicate multiple phenomena:
    - Algal scum or surface mats
    - Very shallow water (bottom reflectance)
    - Suspended organic matter
    - Sun glint artifacts
    
    Cannot distinguish between these without additional analysis.
    Use as flagging tool for field investigation, not direct classification.
    """
    nir_band = _image.select('B8')
    nir_on_water = nir_band.updateMask(_water_mask)
    
    # Identify top 5% as anomalies
    percentile = nir_on_water.reduceRegion(
        reducer=ee.Reducer.percentile([95]), 
        geometry=AOI, 
        scale=30, 
        maxPixels=1e9
    ).get('B8')
    
    anomalies = ee.Image(ee.Algorithms.If(
        percentile, 
        nir_on_water.gte(ee.Number(percentile)).selfMask(), 
        ee.Image(0).selfMask()
    ))
    
    return anomalies, nir_on_water

@st.cache_data
def calculate_water_quality_stats(_image, _water_mask, _aoi):
    """Calculate comprehensive statistics for spectral indices."""
    ndci = _image.normalizedDifference(['B5', 'B4']).rename('ndci').updateMask(_water_mask)
    turbidity = _image.select('B4').rename('turbidity').updateMask(_water_mask)
    
    stats = ndci.addBands(turbidity).reduceRegion(
        reducer=ee.Reducer.mean().combine(
            ee.Reducer.stdDev(), '', True
        ).combine(
            ee.Reducer.minMax(), '', True
        ),
        geometry=_aoi,
        scale=30,
        maxPixels=1e9
    ).getInfo()
    
    return stats

@st.cache_data
def create_time_series(_bounds_key, _aoi, years=2):
    """Generate monthly time series of water quality indices."""
    start_date = ee.Date(datetime.datetime.now(datetime.timezone.utc)).advance(-years, 'year')
    end_date = ee.Date(datetime.datetime.now(datetime.timezone.utc))
    s2_collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(_aoi)
    
    def calculate_monthly_mean(date):
        date = ee.Date(date)
        image = s2_collection.filterDate(date, date.advance(1, 'month')).map(mask_s2_clouds).median().clip(_aoi)
        
        ndwi = image.normalizedDifference(['B3', 'B8'])
        nir = image.select('B8')
        water_mask = ndwi.gt(0.1).And(nir.lt(0.15))
        
        ndci = image.normalizedDifference(['B5', 'B4']).updateMask(water_mask)
        turbidity = image.select('B4').rename('turbidity').updateMask(water_mask)
        
        mean_ndci = ndci.reduceRegion(
            reducer=ee.Reducer.mean(), 
            geometry=_aoi, 
            scale=30, 
            maxPixels=1e9
        ).get('nd')
        
        mean_turb = turbidity.reduceRegion(
            reducer=ee.Reducer.mean(), 
            geometry=_aoi, 
            scale=30, 
            maxPixels=1e9
        ).get('turbidity')
        
        return ee.Feature(None, {
            'date': date.format('YYYY-MM'),
            'mean_ndci': mean_ndci,
            'mean_turbidity': mean_turb
        })
    
    months = ee.List.sequence(0, end_date.difference(start_date, 'month').subtract(1)).map(
        lambda m: start_date.advance(m, 'month')
    )
    monthly_data = months.map(calculate_monthly_mean)
    data = monthly_data.getInfo()
    
    df = pd.DataFrame([{
        'Month': f['properties']['date'],
        'Chlorophyll Index': f['properties'].get('mean_ndci'),
        'Turbidity': f['properties'].get('mean_turbidity')
    } for f in data]).set_index('Month')
    
    return df

# Visualization parameters
chl_viz_params = {'min': 1, 'max': 4, 'palette': ['#3498db', '#2ecc71', '#f39c12', '#e74c3c']}
turbidity_viz_params = {'palette': ['#c0392b']}
floating_viz_params = {'palette': ['#8e44ad']}

# Reference thresholds (for relative comparison, not regulatory limits)
NDCI_ELEVATED = 0.15  # Elevated algal activity
NDCI_HIGH = 0.25      # High algal activity
TURBIDITY_ELEVATED = 0.05  # Elevated turbidity (reflectance units)
TURBIDITY_HIGH = 0.08      # High turbidity (reflectance units)

# -----------------------------------------------------------------------------
# 4. Enhanced Dashboard Layout
# -----------------------------------------------------------------------------

# Sidebar Configuration
with st.sidebar:
    st.markdown("### Control Panel")
    
    with st.expander("⚙️ Data Settings", expanded=True):
        composite_months = st.slider(
            "Composite Time Window (months)", 
            1, 6, 3,
            help="Longer windows provide more cloud-free data but less temporal specificity"
        )
        analysis_years = st.slider("Trend Analysis Period (years)", 1, 5, 2)
    
    st.markdown("---")
    
    st.markdown("### 🗺️ Layer Selection")
    map_selection = st.radio(
        "Choose visualization:",
        ('Chlorophyll Proxy', 'Turbidity Hotspots', 'NIR Anomalies', 'Multi-layer'),
        label_visibility="collapsed"
    )
    
    layer_opacity = st.slider("Layer Opacity", 0.0, 1.0, 0.7, 0.1)
    
    st.markdown("---")
    
    st.markdown("### 📍 Analysis Area")
    st.caption("Define custom area for detailed analysis")
    col1, col2 = st.columns(2)
    with col1:
        min_lon = st.number_input("Min Lon", 76.0, 77.0, 76.255, 0.01, format="%.4f")
        min_lat = st.number_input("Min Lat", 9.0, 11.0, 9.905, 0.01, format="%.4f")
    with col2:
        max_lon = st.number_input("Max Lon", 76.0, 77.0, 76.270, 0.01, format="%.4f")
        max_lat = st.number_input("Max Lat", 9.0, 11.0, 9.915, 0.01, format="%.4f")
    
    HOTSPOT_AOI = ee.Geometry.Rectangle([min_lon, min_lat, max_lon, max_lat])
    
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    st.caption("Data: ESA Sentinel-2 via Google Earth Engine")

# Main Content Area
tab1, tab2, tab3 = st.tabs(["🗺️ Interactive Map", "📊 Analytics Dashboard", "ℹ️ About & Methodology"])

with tab1:
    # Load data
    with st.spinner("Fetching satellite imagery..."):
        image, water_mask, img_count = get_sentinel2_image(AOI, composite_months)
    
    if image is None:
        st.error("No clear imagery available for the selected period. Try increasing the time window.")
        st.stop()
    
    # Calculate statistics
    stats = calculate_water_quality_stats(image, water_mask, AOI)
    chl_mean = stats.get('ndci_mean')
    turb_mean = stats.get('turbidity_mean')
    
    # Statistics Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Images Used", 
            img_count, 
            help="Number of cloud-free Sentinel-2 scenes in composite"
        )
    
    with col2:
        st.metric(
            "Time Window", 
            f"{composite_months} months", 
            help="Temporal range of composite imagery"
        )
    
    with col3:
        if chl_mean is not None:
            status = "High" if chl_mean > NDCI_HIGH else "Elevated" if chl_mean > NDCI_ELEVATED else "Low" if chl_mean > 0 else "Very Low"
            delta_color = "inverse" if chl_mean > NDCI_ELEVATED else "normal"
            st.metric(
                "Avg NDCI", 
                f"{chl_mean:.3f}", 
                delta=status,
                delta_color=delta_color,
                help="Chlorophyll proxy (unitless). Higher values suggest more algal biomass."
            )
        else:
            st.metric("Avg NDCI", "N/A")
    
    with col4:
        if turb_mean is not None:
            status = "High" if turb_mean > TURBIDITY_HIGH else "Elevated" if turb_mean > TURBIDITY_ELEVATED else "Normal"
            delta_color = "inverse" if turb_mean > TURBIDITY_ELEVATED else "normal"
            st.metric(
                "Avg Turbidity", 
                f"{turb_mean:.4f}",
                delta=status,
                delta_color=delta_color,
                help="Red band reflectance (unitless). Higher = more suspended particles."
            )
        else:
            st.metric("Avg Turbidity", "N/A")
    
    st.markdown("---")
    
    # Layer-specific info boxes with proper interpretation
    if map_selection == 'Chlorophyll Proxy':
        st.info("""
        **Chlorophyll Proxy Layer (NDCI):** Relative indicator of algal biomass using spectral characteristics.
        
        - 🔵 Blue = Very Low | 🟢 Green = Low | 🟡 Orange = Moderate | 🔴 Red = High
        
        **Interpretation:** Higher values indicate increased phytoplankton/algal presence. Persistent high values may suggest 
        nutrient enrichment (eutrophication). Seasonal variation is normal; look for unusual patterns or trends.
        
        **Limitation:** These are relative categories, not actual chlorophyll-a concentrations (mg/L). Field sampling required for quantification.
        """)
    elif map_selection == 'Turbidity Hotspots':
        st.warning("""
        **Turbidity Hotspots:** Top 15% highest red reflectance areas, indicating elevated suspended particles.
        
        - 🔴 Red areas show zones with highest turbidity relative to the lake
        
        **Interpretation:** May indicate sediment loading from rivers, agricultural runoff, resuspension from wind/boat activity, 
        or algal blooms. Cross-reference with rainfall events and land use patterns.
        
        **Limitation:** Values are unitless reflectance, not NTU measurements. Ground truth needed for quantitative assessment.
        """)
    elif map_selection == 'NIR Anomalies':
        st.info("""
        **NIR Anomalies:** Top 5% highest near-infrared reflectance over water - multi-factor indicator.
        
        - 🟣 Purple areas show unusual NIR signatures that warrant investigation
        
        **Interpretation:** Clean water absorbs almost all NIR. High values MAY indicate:
        - Dense algal scum or surface mats (cyanobacteria blooms)
        - Very shallow water (bottom reflectance from sand/vegetation)
        - Suspended organic matter
        - Sun glint artifacts (especially in afternoon imagery)
        
        **Critical Limitation:** Cannot distinguish between these causes. Use as screening tool to prioritize field visits.
        """)
    else:
        st.info("""
        **Multi-layer View:** Comprehensive assessment showing all three indicators simultaneously.
        
        - Blue/Green/Orange/Red = Chlorophyll levels
        - Dark Red = Turbidity hotspots  
        - Purple = NIR anomalies
        
        **Interpretation:** Look for spatial relationships - do high chlorophyll areas coincide with anomalies? 
        Are turbidity hotspots near river inlets? Use this view to understand complex water quality patterns.
        """)
    
    # Map Display
    m = geemap.Map(center=[10.0, 76.35], zoom=11, height=650)
    m.add_basemap("HYBRID")
    
    # Add layers based on selection
    if map_selection == 'Chlorophyll Proxy':
        chl_map, ndci_raw = get_chlorophyll_map(image, water_mask)
        m.addLayer(chl_map, chl_viz_params, 'Chlorophyll Index (NDCI)', True, layer_opacity)
        
    elif map_selection == 'Turbidity Hotspots':
        turbidity_map, turb_raw = get_turbidity_map(image, water_mask)
        m.addLayer(turbidity_map, turbidity_viz_params, 'Turbidity Hotspots', True, layer_opacity)
        
    elif map_selection == 'NIR Anomalies':
        floating_map, float_raw = get_floating_matter_map(image, water_mask)
        m.addLayer(floating_map, floating_viz_params, 'NIR Anomalies', True, layer_opacity)
        
    else:  # Multi-layer
        chl_map, _ = get_chlorophyll_map(image, water_mask)
        turbidity_map, _ = get_turbidity_map(image, water_mask)
        floating_map, _ = get_floating_matter_map(image, water_mask)
        
        m.addLayer(chl_map, chl_viz_params, 'Chlorophyll', True, layer_opacity * 0.8)
        m.addLayer(turbidity_map, turbidity_viz_params, 'Turbidity', True, layer_opacity * 0.7)
        m.addLayer(floating_map, floating_viz_params, 'NIR Anomalies', True, layer_opacity * 0.7)
    
    m.addLayer(HOTSPOT_AOI, {'color': 'FF0000', 'fillColor': 'FF000020'}, 'Analysis Area', True, 0.8)
    
    m.to_streamlit()

with tab2:
    st.markdown("### Water Quality Trends")
    
    st.info("""
    **How to Read These Charts:**
    - Look for **seasonal patterns** (monsoon vs dry season effects)
    - Identify **sudden spikes** that may correlate with pollution events or algal blooms
    - Assess **long-term trends** (increasing/decreasing over years)
    - **Light blue shading** marks monsoon months (June-September) when turbidity typically increases
    - **Dashed lines** are reference levels for comparison, NOT regulatory limits
    
    Remember: These are satellite-derived proxies, not laboratory measurements.
    """)
    
    try:
        with st.spinner("Calculating historical trends..."):
            bounds_key = (min_lon, min_lat, max_lon, max_lat)
            timeseries_df = create_time_series(bounds_key, HOTSPOT_AOI, analysis_years)
        
        if not timeseries_df.empty and timeseries_df['Chlorophyll Index'].notna().any():
            # Identify monsoon months and prepare datetime x-axis
            def is_monsoon(month_str):
                try:
                    month = int(month_str.split('-')[1])
                    return month in [6, 7, 8, 9]
                except Exception:
                    return False

            timeseries_df['Is_Monsoon'] = timeseries_df.index.map(is_monsoon)
            # Convert index to datetime for better axis scaling and shading ranges
            dt_index = pd.to_datetime(timeseries_df.index, format='%Y-%m', errors='coerce')
            
            # Create interactive chart
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=(
                    'Chlorophyll Index (NDCI) - Monsoon months in light blue', 
                    'Turbidity Index (Red Band Reflectance)'
                ),
                vertical_spacing=0.15,
                shared_xaxes=True
            )
            
            # Compute contiguous monsoon periods (grouped shading)
            monsoon_positions = [i for i, v in enumerate(timeseries_df['Is_Monsoon']) if v]
            monsoon_periods = []
            if monsoon_positions:
                start_pos = monsoon_positions[0]
                for i in range(1, len(monsoon_positions)):
                    if monsoon_positions[i] != monsoon_positions[i-1] + 1:
                        monsoon_periods.append((start_pos, monsoon_positions[i-1]))
                        start_pos = monsoon_positions[i]
                monsoon_periods.append((start_pos, monsoon_positions[-1]))

            # Chlorophyll plot
            chl_data = timeseries_df['Chlorophyll Index'].dropna()
            if len(chl_data) > 0:
                # Monsoon shading across contiguous ranges for both subplots
                for s_pos, e_pos in monsoon_periods:
                    if pd.notna(dt_index[s_pos]) and pd.notna(dt_index[e_pos]):
                        x0 = dt_index[s_pos]
                        # Shade through end of the last month in the period
                        x1 = (dt_index[e_pos] + pd.offsets.MonthEnd(0))
                        fig.add_vrect(x0=x0, x1=x1, fillcolor="lightblue", opacity=0.18,
                                      layer="below", line_width=0, row=1, col=1)
                        fig.add_vrect(x0=x0, x1=x1, fillcolor="lightblue", opacity=0.18,
                                      layer="below", line_width=0, row=2, col=1)
                
                # Primary series
                x_chl = pd.to_datetime(chl_data.index, format='%Y-%m', errors='coerce')
                fig.add_trace(
                    go.Scatter(
                        x=x_chl, y=chl_data.values,
                        mode='lines+markers', name='NDCI',
                        line=dict(color='#2ecc71', width=3),
                        marker=dict(size=8),
                        hovertemplate='<b>%{x}</b><br>NDCI: %{y:.4f}<extra></extra>'
                    ),
                    row=1, col=1
                )
                # Rolling 3-month average (smoothing)
                chl_roll = chl_data.rolling(window=3, min_periods=2).mean()
                fig.add_trace(
                    go.Scatter(
                        x=x_chl, y=chl_roll.values,
                        mode='lines', name='NDCI (3-mo avg)',
                        line=dict(color='rgba(46,204,113,0.5)', width=2, dash='dot')
                    ),
                    row=1, col=1
                )
                # Highlight high values
                chl_high_mask = chl_data > NDCI_HIGH
                if chl_high_mask.any():
                    fig.add_trace(
                        go.Scatter(
                            x=x_chl[chl_high_mask], y=chl_data[chl_high_mask],
                            mode='markers', name='NDCI > High',
                            marker=dict(size=10, color='#e74c3c', symbol='diamond')
                        ),
                        row=1, col=1
                    )
                
                # Reference lines
                fig.add_hline(
                    y=NDCI_ELEVATED, line_dash="dash", line_color="orange", 
                    row=1, col=1
                )
                fig.add_hline(
                    y=NDCI_HIGH, line_dash="dash", line_color="red", 
                    row=1, col=1
                )
                
                # Trend line
                if len(chl_data) > 1:
                    z = np.polyfit(range(len(chl_data)), chl_data.values, 1)
                    p = np.poly1d(z)
                    trend_direction = "↑ Increasing" if z[0] > 0 else "↓ Decreasing"
                    fig.add_trace(
                        go.Scatter(
                            x=x_chl, y=p(range(len(chl_data))),
                            mode='lines', name=f'Trend {trend_direction}',
                            line=dict(color='rgba(46,204,113,0.3)', width=2, dash='dash')
                        ),
                        row=1, col=1
                    )
            
            # Turbidity plot
            turb_data = timeseries_df['Turbidity'].dropna()
            if len(turb_data) > 0:
                # Primary series
                x_turb = pd.to_datetime(turb_data.index, format='%Y-%m', errors='coerce')
                fig.add_trace(
                    go.Scatter(
                        x=x_turb, y=turb_data.values,
                        mode='lines+markers', name='Turbidity',
                        line=dict(color='#e74c3c', width=3),
                        marker=dict(size=8),
                        hovertemplate='<b>%{x}</b><br>Turbidity: %{y:.4f}<extra></extra>'
                    ),
                    row=2, col=1
                )
                # Rolling 3-month average
                turb_roll = turb_data.rolling(window=3, min_periods=2).mean()
                fig.add_trace(
                    go.Scatter(
                        x=x_turb, y=turb_roll.values,
                        mode='lines', name='Turbidity (3-mo avg)',
                        line=dict(color='rgba(231,76,60,0.5)', width=2, dash='dot')
                    ),
                    row=2, col=1
                )
                # Highlight high turbidity points
                turb_high_mask = turb_data > TURBIDITY_HIGH
                if turb_high_mask.any():
                    fig.add_trace(
                        go.Scatter(
                            x=x_turb[turb_high_mask], y=turb_data[turb_high_mask],
                            mode='markers', name='Turbidity > High',
                            marker=dict(size=10, color='#c0392b', symbol='diamond')
                        ),
                        row=2, col=1
                    )
                
                fig.add_hline(
                    y=TURBIDITY_ELEVATED, line_dash="dash", line_color="orange", 
                    row=2, col=1
                )
                fig.add_hline(
                    y=TURBIDITY_HIGH, line_dash="dash", line_color="red", 
                    row=2, col=1
                )
            
            fig.update_layout(
                height=700, 
                showlegend=True, 
                hovermode='x unified',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                legend=dict(
                    orientation='h',
                    yanchor='top',
                    y=-0.12,
                    xanchor='center',
                    x=0.5
                ),
                margin=dict(t=80, r=30, b=120, l=60)
            )
            fig.update_xaxes(title_text="Month", row=2, col=1, tickformat='%Y-%m')
            fig.update_yaxes(title_text="NDCI (unitless)", row=1, col=1, tickformat=".3f", title_standoff=10, ticks="outside", ticklen=6)
            fig.update_yaxes(title_text="Red Reflectance (unitless)", row=2, col=1, tickformat=".3f", title_standoff=10, ticks="outside", ticklen=6)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Alert summary
            chl_alerts = len(chl_data[chl_data > NDCI_HIGH])
            turb_alerts = len(turb_data[turb_data > TURBIDITY_HIGH])
            
            if chl_alerts > 0 or turb_alerts > 0:
                st.warning(
                    f"**Elevated Readings Detected:** {chl_alerts} months with high NDCI values, "
                    f"{turb_alerts} months with high turbidity values. These periods may warrant "
                    f"ground-truth sampling to assess actual conditions."
                )
            else:
                st.success("No readings exceeded reference thresholds during the analysis period")
            
            # Summary Statistics
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Chlorophyll Index (NDCI) Statistics")
                chl_stats = timeseries_df['Chlorophyll Index'].describe()
                st.dataframe(chl_stats, use_container_width=True)
            
            with col2:
                st.markdown("#### Turbidity Statistics")
                turb_stats = timeseries_df['Turbidity'].describe()
                st.dataframe(turb_stats, use_container_width=True)
            
            # Download data
            csv_data = timeseries_df.to_csv()
            st.download_button(
                label="📥 Download Time Series Data (CSV)",
                data=csv_data,
                file_name=f"vembanad_spectral_indices_{datetime.date.today()}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.warning("Insufficient data for trend analysis. Try adjusting the analysis area or time period.")
    
    except Exception as e:
        st.error(f"Error calculating trends: {str(e)}")
        st.info("Try selecting a smaller analysis area or shorter time period.")

with tab3:
    st.markdown("""
    ## About Backwater Guardian
    
    ### Mission & Purpose
    
    This tool demonstrates satellite-based water quality screening for Vembanad Lake using open Earth observation data from the 
    European Space Agency's Sentinel-2 mission. It is designed as a **first-level screening tool** to identify areas and time 
    periods that may require detailed ground-truth investigation.
    
    ---
    
    ### Critical Limitations & Disclaimers
    
    **What This Tool IS:**
    - A screening tool for identifying potential water quality issues
    - A temporal trend analyzer for detecting changes over time
    - A spatial prioritization tool for field sampling
    - A demonstration of satellite remote sensing capabilities
    
    **What This Tool IS NOT:**
    - A replacement for in-situ water quality measurements
    - A source of regulatory-grade water quality data
    - Capable of providing actual concentrations (mg/L, NTU, etc.)
    - A direct pollution detection system
    
    **Key Limitations:**
    1. **No Direct Measurements:** All values are spectral indices derived from light reflectance, not chemical/physical measurements
    2. **Requires Validation:** Satellite observations must be calibrated with field samples for accurate interpretation
    3. **Cloud Dependence:** Tropical regions have frequent cloud cover; some events may be missed
    4. **Atmospheric Effects:** Even corrected imagery can have residual atmospheric interference
    5. **Spatial Resolution:** 10-20m pixels may mix water types or include land at boundaries
    6. **Temporal Gaps:** 5-day revisit combined with clouds means some short-term events are not captured
    
    ---
    
    ### Data Source & Technical Details
    
    **Satellite Mission:**
    - **Source:** ESA Sentinel-2 MultiSpectral Instrument (MSI)
    - **Constellation:** Two satellites (Sentinel-2A & 2B)
    - **Revisit Time:** 5 days (combined)
    - **Data Type:** Surface Reflectance (atmospherically corrected)
    - **Processing Platform:** Google Earth Engine
    
    **Spectral Bands Used:**
    
    | Band | Wavelength | Resolution | Application |
    |------|------------|------------|-------------|
    | B2 (Blue) | 490 nm | 10m | Atmospheric correction, water detection |
    | B3 (Green) | 560 nm | 10m | Water masking, turbidity |
    | B4 (Red) | 665 nm | 10m | Turbidity proxy, chlorophyll |
    | B5 (Red Edge) | 705 nm | 20m | Chlorophyll detection (NDCI) |
    | B8 (NIR) | 842 nm | 10m | Water detection, anomaly identification |
    | B11 (SWIR) | 1610 nm | 20m | Water/land separation |
    
    ---
    
    ### Methodology & Scientific Basis
    
    #### 1. Water Detection
    **Method:** NDWI (Normalized Difference Water Index)
    
    **Formula:** (Green - NIR) / (Green + NIR)
    
    **Thresholds:** NDWI > 0.1 AND NIR < 0.15
    
    **Reference:** McFeeters, S.K. (1996). "The use of the Normalized Difference Water Index (NDWI) in the delineation of open water features." 
    International Journal of Remote Sensing, 17(7), 1425-1432.
    
    **Purpose:** Separates water bodies from land, vegetation, and built-up areas. Thresholds tuned specifically for Vembanad Lake's 
    characteristics (turbid tropical backwater).
    
    ---
    
    #### 2. Chlorophyll Proxy (NDCI)
    **Method:** Normalized Difference Chlorophyll Index
    
    **Formula:** (Red Edge - Red) / (Red Edge + Red) = (B5 - B4) / (B5 + B4)
    
    **Scientific Basis:**
    - Red edge (705nm) is sensitive to chlorophyll absorption features
    - Chlorophyll-a has strong absorption in red (665nm) and reflection in red edge
    - Higher NDCI values correlate with increased phytoplankton biomass
    
    **Classification (Relative Categories):**
    - Very Low: NDCI ≤ 0.0
    - Low: 0.0 < NDCI ≤ 0.1
    - Moderate: 0.1 < NDCI ≤ 0.2
    - High: NDCI > 0.2
    
    **Key References:**
    - Mishra, S., & Mishra, D.R. (2012). "Normalized difference chlorophyll index: A novel model for remote estimation of 
    chlorophyll-a concentration in turbid productive waters." Remote Sensing of Environment, 117, 394-406.
    - Gitelson, A.A., et al. (2009). "A simple semi-analytical model for remote estimation of chlorophyll-a in turbid waters."
    
    **Important Limitations:**
    - NDCI is unitless and does NOT provide chlorophyll-a concentration (mg/L)
    - Affected by suspended sediments, CDOM (colored dissolved organic matter), and bottom reflectance in shallow areas
    - Requires local calibration with field measurements for quantitative interpretation
    - Different algal species have varying spectral characteristics
    
    ---
    
    #### 3. Turbidity Proxy
    **Method:** Red band reflectance as turbidity indicator
    
    **Scientific Basis:**
    - Suspended particles scatter light, increasing water reflectance
    - Red wavelengths (665nm) are particularly sensitive to particle scattering
    - Higher red reflectance correlates with higher suspended solid concentration
    
    **Implementation:** Displays top 15% highest red reflectance areas as "hotspots"
    
    **Key References:**
    - Nechad, B., et al. (2010). "Calibration and validation of a generic multisensor algorithm for mapping of total suspended matter."
    - Dogliotti, A.I., et al. (2015). "A single algorithm to retrieve turbidity from remotely-sensed data in all coastal waters."
    
    **Important Limitations:**
    - Values are unitless reflectance, NOT NTU (Nephelometric Turbidity Units)
    - Red band is affected by both chlorophyll absorption and particle scattering (confounding factors)
    - Bottom reflectance interferes in shallow water (<2m depth)
    - Requires empirical calibration curve specific to Vembanad Lake for quantitative values
    
    ---
    
    #### 4. NIR Anomaly Detection
    **Method:** Near-infrared reflectance over water surfaces
    
    **Scientific Basis:**
    - Clean water strongly absorbs NIR radiation (>99% absorption)
    - Any significant NIR reflectance over water indicates surface or shallow anomalies
    - Common causes: floating algae, shallow bottom, suspended organics, or sun glint
    
    **Implementation:** Displays top 5% highest NIR areas as anomalies
    
    **CRITICAL LIMITATION:**
    This is NOT a debris detector. Multiple phenomena cause elevated NIR over water:
    
    1. **Algal Surface Scums:** Dense cyanobacteria blooms floating on surface
    2. **Shallow Water:** Bottom reflectance from sand, rocks, or aquatic vegetation
    3. **Suspended Organic Matter:** High organic particle concentrations
    4. **Sun Glint:** Specular reflection from water surface (especially late morning/afternoon)
    5. **Emergent Vegetation:** Water hyacinth, lotus, or other floating plants
    
    **Proper Interpretation:** Use as a flagging tool to identify areas requiring field investigation. Cannot distinguish between causes 
    without additional data (spectral unmixing, temporal analysis, or field verification).
    
    ---
    
    ### Reference Thresholds Explained
    
    The "Elevated" and "High" reference lines shown in charts are **NOT:**
    - Regulatory water quality standards
    - Health-based limits
    - Official pollution thresholds
    
    They ARE:
    - Empirically derived percentiles for relative comparison within Vembanad Lake
    - Based on typical ranges observed in similar tropical backwaters
    - Intended to highlight periods that deviate from baseline conditions
    - Starting points for prioritizing field investigation
    
    **For Actual Water Quality Standards, Consult:**
    - Central Pollution Control Board (CPCB) - India
    - Kerala State Pollution Control Board
    - Bureau of Indian Standards (BIS) - Drinking Water Specifications (IS 10500:2012)
    - WHO Guidelines for Drinking Water Quality
    
    ---
    
    ### Seasonal Patterns in Vembanad Lake
    
    **Southwest Monsoon (June-September):**
    - Heavy rainfall increases river discharge
    - Elevated turbidity from sediment loading
    - Variable chlorophyll (nutrients vs. light limitation)
    - Freshwater intrusion affects salinity
    
    **Post-Monsoon (October-December):**
    - Turbidity gradually decreases
    - Water clarity improves
    - Potential for algal blooms (nutrients + light + warmer temps)
    
    **Winter/Dry Season (January-May):**
    - Lower water levels
    - Increased salinity in lower reaches
    - Baseline chlorophyll conditions
    - Lower turbidity overall
    
    **Pre-Monsoon (April-May):**
    - Warmest temperatures
    - Potential cyanobacteria bloom period
    - Lowest water levels
    
    ---
    
    ### Best Practices for Using This Tool
    
    **1. Temporal Analysis:**
    - Compare current conditions to historical baseline
    - Look for anomalous spikes or sustained elevated periods
    - Consider seasonal context when interpreting values
    
    **2. Spatial Patterns:**
    - Identify consistent hotspot locations
    - Map potential pollution sources (river inlets, discharge points)
    - Use multi-layer view to understand relationships
    
    **3. Field Validation:**
    - Prioritize sampling in areas with persistent anomalies
    - Collect samples within ±3 hours of satellite overpass (typically 10:30 AM local)
    - Record GPS coordinates, time, weather, and visual observations
    
    **4. Data Integration:**
    - Cross-reference with rainfall data
    - Consider agricultural calendar (fertilizer application periods)
    - Note local events (festivals, industrial activities)
    
    **5. Reporting:**
    - Always include image dates and number of scenes used
    - Report values with units (or specify "unitless")
    - Acknowledge limitations and need for validation
    - Don't overstate certainty
    
    ---
    
    ### Recommended Ground-Truth Measurements
    
    To validate and calibrate satellite observations:
    
    **Essential Parameters:**
    - **Chlorophyll-a:** Laboratory extraction method or in-situ fluorometry
    - **Turbidity:** Nephelometer (report in NTU or FNU)
    - **Secchi Depth:** Simple transparency disk (cm)
    - **Total Suspended Solids (TSS):** Gravimetric analysis (mg/L)
    
    **Supporting Parameters:**
    - Dissolved Oxygen, pH, Temperature, Conductivity (multi-parameter probe)
    - Nutrients: Total Nitrogen, Total Phosphorus (laboratory analysis)
    - Phytoplankton identification and enumeration
    - Water color (visual assessment or spectrophotometry)
    
    **Sampling Protocol:**
    - Surface samples (0-0.5m depth) for satellite matchup
    - Multiple locations across lake segments
    - Same-day as satellite overpass when possible
    - Triplicate samples for quality control
    - Proper preservation and chain of custody
    
    ---
    
    ### Future Enhancements
    
    To develop this into an operational monitoring system:
    
    1. **Local Calibration:** Develop regression models using field samples vs. satellite indices
    2. **Algorithm Refinement:** Test multiple chlorophyll algorithms (OC3, 2-band, 3-band approaches)
    3. **Validation Database:** Build archive of satellite-field matchups over time
    4. **Advanced Corrections:** Implement adjacency effect correction, sun glint removal
    5. **Machine Learning:** Train classifiers using labeled training data
    6. **Automated Alerts:** Real-time anomaly detection with stakeholder notifications
    7. **Data Integration:** Combine with weather, river discharge, land-use, and point-source data
    8. **Multi-Mission:** Incorporate Landsat, MODIS for extended temporal record
    
    ---
    
    ### Scientific References
    
    **Water Quality Remote Sensing:**
    - IOCCG Report Series - International Ocean-Colour Coordinating Group
    - Gholizadeh et al. (2016). "A comprehensive review on water quality parameters estimation using remote sensing techniques"
    - Matthews (2011). "A current review of empirical procedures of remote sensing in inland waters"
    
    **Specific Algorithms:**
    - McFeeters (1996) - NDWI
    - Mishra & Mishra (2012) - NDCI
    - Nechad et al. (2010) - Turbidity
    - Xu (2006) - Modified NDWI
    
    **Vembanad Lake Studies:**
    - Check Kerala State Pollution Control Board reports
    - Centre for Water Resources Development and Management (CWRDM) publications
    - National Centre for Earth Science Studies (NCESS) research
    
    ---
    
    ### Acknowledgments
    
    **Data Providers:**
    - European Space Agency (ESA) - Sentinel-2 imagery
    - Copernicus Programme - Open data access
    - Google Earth Engine - Cloud processing platform
    
    **Open Source Tools:**
    - Streamlit - Web application framework
    - geemap - Interactive mapping library
    - Plotly - Data visualization
    
    ---
    
    ### Contact & Collaboration
    
    For operational use, academic collaboration, or validation data sharing:
    
    - **Kerala State Pollution Control Board** - Regulatory authority
    - **Centre for Water Resources Development and Management (CWRDM)** - Research institution
    - **National Remote Sensing Centre (NRSC)** - Technical expertise
    - **Local universities** - Academic partnerships for field validation
    
    ---
    
    ### Final Disclaimer
    
    This tool is provided "as is" for **informational, educational, and research purposes only**. 
    
    The developers make NO warranties regarding:
    - Accuracy of satellite-derived indices
    - Suitability for regulatory or legal decision-making
    - Completeness or timeliness of data
    - Fitness for any particular purpose
    
    **Users assume all responsibility** for interpretation and application of results. Always consult qualified environmental 
    professionals and conduct proper field sampling before making water management decisions.
    
    Satellite remote sensing is a powerful screening tool but is NOT a substitute for direct water quality monitoring programs.
    
    ---
    
    **Last Updated:** October 2025  
    **Version:** 1.0 (Demonstration/Research Tool)
    
    *Powered by Google Earth Engine • ESA Sentinel-2 • Built with Streamlit*
    """)

st.markdown("---")
st.caption("🌍 Environmental screening tool for water resource monitoring • Not a substitute for field measurements • Requires ground-truth validation")