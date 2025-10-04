import ee

try:
    # Add your Project ID inside the parentheses
    ee.Initialize(project='backwater-guard')
    print("SUCCESS: Earth Engine authentication is working correctly.")
except Exception as e:
    print(f"FAILURE: Could not initialize Earth Engine.\nError: {e}")