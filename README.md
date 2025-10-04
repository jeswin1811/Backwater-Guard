# Backwater Guardian

An interactive Streamlit dashboard that reports water quality indicators (chlorophyll/eutrophication and turbidity hotspots) over Vembanad Lake using Sentinel-2 imagery from Google Earth Engine.

## Features
- Sentinel-2 SR (harmonized) imagery with QA60 cloud/cirrus masking
- Chlorophyll proxy via NDCI (B5, B4)
- Turbidity hotspot proxy using a simple red-to-blue ratio thresholding against the 80th percentile
- Adjustable hotspot AOI for a 2-year monthly trend chart
- Interactive map powered by geemap and Folium basemap

## Prerequisites
- A Google Earth Engine account and a Cloud Project with Earth Engine enabled
- Python 3.10+

## Quickstart

1. Install dependencies:

```powershell
python -m venv .venv; . .venv\Scripts\Activate.ps1; pip install -r requirements.txt
```

2. Authenticate Earth Engine (first time only):

```powershell
python test_ee.py
```

3. Run the app:

```powershell
streamlit run app.py
```

If you see an authentication error in the app, ensure the project id in `app.py` and `test_ee.py` matches your GEE project.

## Notes
- Reductions on Sentinel-2 bands use 10 m scale for consistency with B2–B5, B8 bands.
- We removed Streamlit caching on functions that return Earth Engine objects because these objects are not reliably cache-serializable across runs.
- The indexes used are proxies; for scientific work, consider atmospheric correction specifics and local calibration.
