import ee
import streamlit as st
import geemap.foliumap as geemap
import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np

# -----------------------------------------------------------------------------
# 1. App Setup and Configuration
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="Backwater Guardian",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# -----------------------------------------------------------------------------
# 2. Earth Engine Initialization
# -----------------------------------------------------------------------------

@st.cache_resource
def initialize_ee():
    try:
        ee.Initialize(project='backwater-guard')
        return True
    except ee.EEException:
        return False

if not initialize_ee():
    st.error("Authentication failed. Please check your Project ID and setup.")
    st.stop()

AOI = ee.Geometry.Rectangle([76.25, 9.9, 76.45, 10.1])

# -----------------------------------------------------------------------------
# 3. Enhanced Analysis Functions
# -----------------------------------------------------------------------------

def mask_s2_clouds(image):
    qa = image.select('QA60')
    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11
    mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
    scaled_optical = image.select('B.*').divide(10000)
    return scaled_optical.updateMask(mask).copyProperties(image, ["system:time_start"])

@st.cache_data(ttl=3600)
def get_sentinel2_image(_aoi, months_back=3):
    """Builds a recent median composite with configurable time window."""
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
    ndwi = latest_image.normalizedDifference(['B3', 'B8']).rename('ndwi')
    nir = latest_image.select('B8')
    water_mask = ndwi.gt(0.1).And(nir.lt(0.15))
    
    return latest_image, water_mask, collection_size

@st.cache_data
def get_chlorophyll_map(_image, _water_mask):
    """Enhanced chlorophyll detection with better classification."""
    ndci = _image.normalizedDifference(['B5', 'B4']).rename('ndci')
    classified_image = (
        ndci.where(ndci.lte(0.05), 1)  # Low
        .where(ndci.gt(0.05).And(ndci.lte(0.15)), 2)  # Medium
        .where(ndci.gt(0.15).And(ndci.lte(0.25)), 3)  # High
        .where(ndci.gt(0.25), 4)  # Very High
    )
    return classified_image.updateMask(_water_mask), ndci.updateMask(_water_mask)

@st.cache_data
def get_turbidity_map(_image, _water_mask):
    """Enhanced turbidity calculation."""
    turbidity_index = _image.expression(
        'B4 / (B2 + B3 + 0.001)',
        {'B4': _image.select('B4'), 'B3': _image.select('B3'), 'B2': _image.select('B2')},
    ).rename('turbidity')
    turbidity_on_water = turbidity_index.updateMask(_water_mask)
    percentile = turbidity_on_water.reduceRegion(
        reducer=ee.Reducer.percentile([85]), geometry=AOI, scale=30, maxPixels=1e9
    ).get('turbidity')
    return ee.Image(ee.Algorithms.If(percentile, 
                                     turbidity_on_water.gte(ee.Number(percentile)).selfMask(), 
                                     ee.Image(0).selfMask())), turbidity_on_water

@st.cache_data
def get_floating_matter_map(_image, _water_mask):
    """Detect floating debris using NIR reflectance."""
    nir_band = _image.select('B8')
    nir_on_water = nir_band.updateMask(_water_mask)
    percentile = nir_on_water.reduceRegion(
        reducer=ee.Reducer.percentile([95]), geometry=AOI, scale=30, maxPixels=1e9
    ).get('B8')
    return ee.Image(ee.Algorithms.If(percentile, 
                                     nir_on_water.gte(ee.Number(percentile)).selfMask(), 
                                     ee.Image(0).selfMask())), nir_on_water

@st.cache_data
def calculate_water_quality_stats(_image, _water_mask, _aoi):
    """Calculate comprehensive water quality statistics."""
    ndci = _image.normalizedDifference(['B5', 'B4']).rename('ndci').updateMask(_water_mask)
    turbidity = _image.expression(
        'B4 / (B2 + B3 + 0.001)',
        {'B4': _image.select('B4'), 'B3': _image.select('B3'), 'B2': _image.select('B2')}
    ).rename('turbidity').updateMask(_water_mask)
    
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
    """Enhanced time series with better error handling."""
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
        turbidity = image.expression(
            'B4 / (B2 + B3 + 0.001)',
            {'B4': image.select('B4'), 'B3': image.select('B3'), 'B2': image.select('B2')}
        ).rename('turbidity').updateMask(water_mask)
        
        mean_ndci = ndci.reduceRegion(reducer=ee.Reducer.mean(), geometry=_aoi, scale=30, maxPixels=1e9).get('nd')
        mean_turb = turbidity.reduceRegion(reducer=ee.Reducer.mean(), geometry=_aoi, scale=30, maxPixels=1e9).get('turbidity')
        
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
chl_viz_params = {'min': 1, 'max': 4, 'palette': ['#00FF00', '#FFFF00', '#FF8C00', '#FF0000']}
turbidity_viz_params = {'palette': ['#FF0000']}
floating_viz_params = {'palette': ['#8A2BE2']}

# Thresholds for alerts
CHLOROPHYLL_WARNING = 0.15
CHLOROPHYLL_CRITICAL = 0.25
TURBIDITY_WARNING = 0.40
TURBIDITY_CRITICAL = 0.45

# -----------------------------------------------------------------------------
# 4. Enhanced Dashboard Layout
# -----------------------------------------------------------------------------

# Sidebar Configuration
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/000000/lake.png", width=80)
    st.markdown("### Control Panel")
    
    with st.expander("Data Settings", expanded=True):
        composite_months = st.slider("Composite Time Window (months)", 1, 6, 3)
        analysis_years = st.slider("Trend Analysis Period (years)", 1, 5, 2)
    
    st.markdown("---")
    
    st.markdown("### Layer Selection")
    map_selection = st.radio(
        "Choose visualization:",
        ('Eutrophication', 'Turbidity Hotspots', 'Floating Debris', 'Multi-layer'),
        label_visibility="collapsed"
    )
    
    # Layer opacity control
    layer_opacity = st.slider("Layer Opacity", 0.0, 1.0, 0.7, 0.1, help="Adjust transparency of data layers")
    
    st.markdown("---")
    
    st.markdown("### Analysis Area")
    col1, col2 = st.columns(2)
    with col1:
        min_lon = st.number_input("Min Lon", 76.0, 77.0, 76.255, 0.01, format="%.4f")
        min_lat = st.number_input("Min Lat", 9.0, 11.0, 9.905, 0.01, format="%.4f")
    with col2:
        max_lon = st.number_input("Max Lon", 76.0, 77.0, 76.270, 0.01, format="%.4f")
        max_lat = st.number_input("Max Lat", 9.0, 11.0, 9.915, 0.01, format="%.4f")
    
    HOTSPOT_AOI = ee.Geometry.Rectangle([min_lon, min_lat, max_lon, max_lat])
    
    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Main Content Area
tab1, tab2, tab3 = st.tabs(["Interactive Map", "Analytics Dashboard", "About"])

with tab1:
    # Load data
    with st.spinner("Fetching satellite imagery..."):
        image, water_mask, img_count = get_sentinel2_image(AOI, composite_months)
    
    if image is None:
        st.error("No clear imagery available for the selected period.")
        st.stop()
    
    # Calculate statistics
    stats = calculate_water_quality_stats(image, water_mask, AOI)
    chl_mean = stats.get('ndci_mean')
    turb_mean = stats.get('turbidity_mean')
    
    # Statistics Cards at the top
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Images Used", 
            img_count, 
            help="Number of cloud-free Sentinel-2 images in composite"
        )
    
    with col2:
        st.metric(
            "Time Window", 
            f"{composite_months} months", 
            help="Temporal range of composite imagery"
        )
    
    with col3:
        if chl_mean:
            delta_color = "inverse" if chl_mean > CHLOROPHYLL_WARNING else "normal"
            status = "Critical" if chl_mean > CHLOROPHYLL_CRITICAL else "High" if chl_mean > CHLOROPHYLL_WARNING else "Moderate" if chl_mean > 0.05 else "Low"
            st.metric(
                "Avg Chlorophyll", 
                f"{chl_mean:.3f}", 
                delta=status,
                delta_color=delta_color,
                help=f"NDCI mean value. Warning: >{CHLOROPHYLL_WARNING}, Critical: >{CHLOROPHYLL_CRITICAL}"
            )
        else:
            st.metric("Avg Chlorophyll", "N/A")
    
    with col4:
        if turb_mean:
            delta_color = "inverse" if turb_mean > TURBIDITY_WARNING else "normal"
            status = "Critical" if turb_mean > TURBIDITY_CRITICAL else "High" if turb_mean > TURBIDITY_WARNING else "Normal"
            st.metric(
                "Avg Turbidity", 
                f"{turb_mean:.3f}",
                delta=status,
                delta_color=delta_color,
                help=f"Turbidity index. Warning: >{TURBIDITY_WARNING}, Critical: >{TURBIDITY_CRITICAL}"
            )
        else:
            st.metric("Avg Turbidity", "N/A")
    
    st.markdown("---")
    
    # Layer-specific info boxes
    if map_selection == 'Eutrophication':
        st.info("**Eutrophication Layer:** 🟢 Green = Low (Healthy) | 🟡 Yellow = Medium | 🟠 Orange = High | 🔴 Red = Very High (Critical algal blooms)")
    elif map_selection == 'Turbidity Hotspots':
        st.warning("**Turbidity Hotspots:** 🔴 Red areas indicate the top 15% highest turbidity zones - potential sediment loading or runoff")
    elif map_selection == 'Floating Debris':
        st.info("**Floating Debris:** 🟣 Purple areas show potential floating matter, algal scum, or surface pollutants detected via NIR reflectance")
    else:
        st.info("**Multi-layer View:** All three indicators displayed simultaneously. Green=Eutrophication, Red=Turbidity, Purple=Floating Matter")
    
    # Map Display
    m = geemap.Map(center=[10.0, 76.35], zoom=11, height=650)
    m.add_basemap("HYBRID")
    
    # Add layers based on selection
    if map_selection == 'Eutrophication':
        chl_map, ndci_raw = get_chlorophyll_map(image, water_mask)
        m.addLayer(chl_map, chl_viz_params, 'Chlorophyll Index', True, layer_opacity)
        
    elif map_selection == 'Turbidity Hotspots':
        turbidity_map, turb_raw = get_turbidity_map(image, water_mask)
        m.addLayer(turbidity_map, turbidity_viz_params, 'Turbidity Hotspots', True, layer_opacity)
        
    elif map_selection == 'Floating Debris':
        floating_map, float_raw = get_floating_matter_map(image, water_mask)
        m.addLayer(floating_map, floating_viz_params, 'Floating Matter', True, layer_opacity)
        
    else:  # Multi-layer
        chl_map, _ = get_chlorophyll_map(image, water_mask)
        turbidity_map, _ = get_turbidity_map(image, water_mask)
        floating_map, _ = get_floating_matter_map(image, water_mask)
        
        m.addLayer(chl_map, chl_viz_params, 'Chlorophyll', True, layer_opacity * 0.8)
        m.addLayer(turbidity_map, turbidity_viz_params, 'Turbidity', True, layer_opacity * 0.7)
        m.addLayer(floating_map, floating_viz_params, 'Floating Matter', True, layer_opacity * 0.7)
    
    m.addLayer(HOTSPOT_AOI, {'color': 'FF0000', 'fillColor': 'FF000020'}, 'Analysis Area', True, 0.8)
    
    m.to_streamlit()

with tab2:
    st.markdown("### Water Quality Trends")
    
    try:
        with st.spinner("Calculating historical trends..."):
            bounds_key = (min_lon, min_lat, max_lon, max_lat)
            timeseries_df = create_time_series(bounds_key, HOTSPOT_AOI, analysis_years)
        
        if not timeseries_df.empty and timeseries_df['Chlorophyll Index'].notna().any():
            # Identify monsoon months (June-September)
            def is_monsoon(month_str):
                month = int(month_str.split('-')[1])
                return month in [6, 7, 8, 9]
            
            timeseries_df['Is_Monsoon'] = timeseries_df.index.map(is_monsoon)
            
            # Create interactive plotly chart with seasonal highlighting
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Chlorophyll Index Trend (Monsoon months highlighted)', 'Turbidity Trend'),
                vertical_spacing=0.15,
                shared_xaxes=True
            )
            
            # Chlorophyll plot
            chl_data = timeseries_df['Chlorophyll Index'].dropna()
            if len(chl_data) > 0:
                # Add monsoon background shading
                for idx in timeseries_df[timeseries_df['Is_Monsoon']].index:
                    if idx in chl_data.index:
                        fig.add_vrect(
                            x0=idx, x1=idx,
                            fillcolor="lightblue", opacity=0.2,
                            layer="below", line_width=0,
                            row=1, col=1
                        )
                
                # Main chlorophyll line
                fig.add_trace(
                    go.Scatter(x=chl_data.index, y=chl_data.values,
                              mode='lines+markers', name='Chlorophyll',
                              line=dict(color='#2ecc71', width=3),
                              marker=dict(size=8),
                              hovertemplate='<b>%{x}</b><br>Chlorophyll: %{y:.4f}<extra></extra>'),
                    row=1, col=1
                )
                
                # Add threshold lines for chlorophyll
                fig.add_hline(y=CHLOROPHYLL_WARNING, line_dash="dash", line_color="orange", 
                             annotation_text="Warning Level", row=1, col=1,
                             annotation_position="right")
                fig.add_hline(y=CHLOROPHYLL_CRITICAL, line_dash="dash", line_color="red", 
                             annotation_text="Critical Level", row=1, col=1,
                             annotation_position="right")
                
                # Add trend line for chlorophyll
                if len(chl_data) > 1:
                    z = np.polyfit(range(len(chl_data)), chl_data.values, 1)
                    p = np.poly1d(z)
                    trend_direction = "↑ Increasing" if z[0] > 0 else "↓ Decreasing"
                    fig.add_trace(
                        go.Scatter(x=chl_data.index, y=p(range(len(chl_data))),
                                  mode='lines', name=f'Trend {trend_direction}',
                                  line=dict(color='rgba(46,204,113,0.3)', width=2, dash='dash')),
                        row=1, col=1
                    )
            
            # Turbidity plot
            turb_data = timeseries_df['Turbidity'].dropna()
            if len(turb_data) > 0:
                # Add monsoon background shading
                for idx in timeseries_df[timeseries_df['Is_Monsoon']].index:
                    if idx in turb_data.index:
                        fig.add_vrect(
                            x0=idx, x1=idx,
                            fillcolor="lightblue", opacity=0.2,
                            layer="below", line_width=0,
                            row=2, col=1
                        )
                
                fig.add_trace(
                    go.Scatter(x=turb_data.index, y=turb_data.values,
                              mode='lines+markers', name='Turbidity',
                              line=dict(color='#e74c3c', width=3),
                              marker=dict(size=8),
                              hovertemplate='<b>%{x}</b><br>Turbidity: %{y:.4f}<extra></extra>'),
                    row=2, col=1
                )
                
                # Add threshold lines for turbidity
                fig.add_hline(y=TURBIDITY_WARNING, line_dash="dash", line_color="orange", 
                             annotation_text="Warning Level", row=2, col=1,
                             annotation_position="right")
                fig.add_hline(y=TURBIDITY_CRITICAL, line_dash="dash", line_color="red", 
                             annotation_text="Critical Level", row=2, col=1,
                             annotation_position="right")
            
            fig.update_layout(
                height=700, 
                showlegend=True, 
                hovermode='x unified',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            fig.update_xaxes(title_text="Month", row=2, col=1)
            fig.update_yaxes(title_text="Chlorophyll Index (NDCI)", row=1, col=1)
            fig.update_yaxes(title_text="Turbidity Index", row=2, col=1)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Alert summary
            chl_alerts = len(chl_data[chl_data > CHLOROPHYLL_CRITICAL])
            turb_alerts = len(turb_data[turb_data > TURBIDITY_CRITICAL])
            
            if chl_alerts > 0 or turb_alerts > 0:
                st.warning(f"**Alerts:** {chl_alerts} months with critical chlorophyll levels, {turb_alerts} months with critical turbidity levels")
            else:
                st.success("No critical threshold violations detected in the analysis period")
            
            # Summary Statistics
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Chlorophyll Statistics")
                chl_stats = timeseries_df['Chlorophyll Index'].describe()
                st.dataframe(chl_stats, use_container_width=True)
            
            with col2:
                st.markdown("#### Turbidity Statistics")
                turb_stats = timeseries_df['Turbidity'].describe()
                st.dataframe(turb_stats, use_container_width=True)
            
            # Download data
            csv_data = timeseries_df.to_csv()
            st.download_button(
                label="Download Data (CSV)",
                data=csv_data,
                file_name=f"vembanad_water_quality_{datetime.date.today()}.csv",
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
    ### About Backwater Guardian
    
    This advanced monitoring system uses **Sentinel-2 satellite imagery** to track water quality in Vembanad Lake.
    
    #### Indicators Explained
    
    **Eutrophication (Chlorophyll Index)**
    - Measures algal blooms and nutrient pollution
    - Uses NDCI (Normalized Difference Chlorophyll Index)
    - Formula: (B5 - B4) / (B5 + B4)
    - Warning Level: >0.15 | Critical Level: >0.25
    
    **Turbidity**
    - Detects suspended particles and water clarity
    - Highlights areas with highest sediment load
    - Critical for aquatic ecosystem health
    - Warning Level: >0.40 | Critical Level: >0.45
    
    **Floating Debris**
    - Identifies surface pollutants and algal scum
    - Uses NIR reflectance patterns
    - Helps track pollution sources
    
    #### Data Source
    - **Sentinel-2 MSI**: 10-20m resolution
    - **Update Frequency**: Every 5 days
    - **Bands Used**: B2 (Blue), B3 (Green), B4 (Red), B5 (Red Edge), B8 (NIR)
    
    #### Seasonal Patterns
    - **Monsoon Season** (June-September): Highlighted in light blue on charts
    - Typically shows increased turbidity and variable chlorophyll levels
    - Post-monsoon recovery period shows water quality improvement
    
    #### Best Practices
    1. Use 3-month composites for seasonal analysis
    2. Compare trends over multiple years
    3. Monitor threshold violations for early warnings
    4. Cross-reference with local weather patterns
    5. Export data for detailed reporting
    
    ---
    *Powered by Google Earth Engine • Built with Streamlit*
    """)

st.markdown("---")
st.caption("Environmental monitoring for sustainable water resource management")