from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import polyline
import numpy as np
from pyproj import Proj, transform, Geod
import geopandas as gpd
import rasterio
from shapely.geometry import Point
import os
import pandas as pd
from utils import get_directions_polylines, decode_polyline, interpolate_geopath_equidistant, create_shapefiles_and_extract_raster_values, get_lat_lon_from_address
import traceback
import sys

app = Flask(__name__)
# Update CORS configuration to explicitly allow the React frontend
# Get allowed origins from environment variable or use defaults
ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:3001').split(',')
CORS(app, resources={
    r"/api/*": {
        "origins": ALLOWED_ORIGINS,
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

API_KEY = "AIzaSyDA1XsDPGVPIJGSHi7-NTRVZODYIlbI7OE"
# Get the absolute path to the UTCI file
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GEOTIFF_PATH = os.path.join(SCRIPT_DIR, "UTCI_1600.tif")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.route('/api/process-route', methods=['POST'])
def process_route():
    try:
        data = request.json
        origin = data.get('origin')
        destination = data.get('destination')

        if not origin or not destination:
            return jsonify({'error': 'Origin and destination are required'}), 400

        print(f"Processing route from {origin} to {destination}")

        # Get coordinates
        origin_lat, origin_lon = get_lat_lon_from_address(origin, API_KEY)
        destination_lat, destination_lon = get_lat_lon_from_address(destination, API_KEY)

        if origin_lat is None or destination_lat is None:
            return jsonify({'error': 'Failed to find coordinates for locations'}), 400

        print(f"Coordinates found: Origin ({origin_lat}, {origin_lon}), Destination ({destination_lat}, {destination_lon})")

        origin_coords = f"{origin_lat}, {origin_lon}"
        destination_coords = f"{destination_lat}, {destination_lon}"

        # Get routes
        print("Fetching routes from Google Maps API...")
        google_routes_data = get_directions_polylines(origin_coords, destination_coords, api_key=API_KEY)
        if not google_routes_data:
            return jsonify({'error': 'No routes found between the specified locations'}), 400

        print(f"Found {len(google_routes_data)} routes")
        print("Google routes data:", google_routes_data)  # Debug print
        
        decoded_coords = [decode_polyline(route['polyline']) for route in google_routes_data]
        interpolated_routes = [interpolate_geopath_equidistant(coords, 4) for coords in decoded_coords]

        # Process routes
        print("Processing routes with UTCI data...")
        gdfs, _ = create_shapefiles_and_extract_raster_values(interpolated_routes, GEOTIFF_PATH, OUTPUT_DIR)
        all_routes_gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))

        if all_routes_gdf.crs != 'epsg:4326':
            all_routes_gdf = all_routes_gdf.to_crs('epsg:4326')

        # Calculate route statistics
        all_routes_gdf['route_id'] = np.repeat(np.arange(len(gdfs)), [len(gdf) for gdf in gdfs])
        mean_raster_values = all_routes_gdf.groupby('route_id')['raster_value'].mean()
        min_raster_values = all_routes_gdf.groupby('route_id')['raster_value'].min()
        max_raster_values = all_routes_gdf.groupby('route_id')['raster_value'].max()

        # Calculate percentage of route in shade using a relative threshold
        # Find the overall min and max UTCI values across all routes
        overall_min = all_routes_gdf['raster_value'].min()
        overall_max = all_routes_gdf['raster_value'].max()
        utci_range = overall_max - overall_min

        # Define the shade threshold as a percentage of the range from the minimum
        # For example, if we want the bottom 30% of the range to be considered "shade"
        SHADE_PERCENTILE = 90  # Bottom 30% of the range
        shade_threshold = overall_min + (utci_range * SHADE_PERCENTILE / 100)

       # print(f"UTCI range: {overall_min:.2f} to {overall_max:.2f}")
        print(f"Shade threshold (bottom {SHADE_PERCENTILE}%): {shade_threshold:.2f}")

        # Calculate the percentage of points below the threshold for each route
        shade_percentages = []
        for i in range(len(gdfs)):
            route_data = all_routes_gdf[all_routes_gdf['route_id'] == i]
            total_points = len(route_data)
            shade_points = len(route_data[route_data['raster_value'] < shade_threshold])
            shade_percentage = (shade_points / total_points) * 100 if total_points > 0 else 0
            shade_percentages.append(shade_percentage)
            print(f"Route {i}: {shade_percentage:.2f}% in shade (UTCI < {shade_threshold:.2f})")

        # Print only the raster values for each route
        

        # Also print to stderr to ensure it's visible


        # Write to a file to ensure we can see the values
        with open(os.path.join(OUTPUT_DIR, "raster_values.txt"), "w") as f:
            f.write("--- Raster Values by Route ---\n")
            for i in range(len(gdfs)):
                route_utci_values = all_routes_gdf[all_routes_gdf['route_id'] == i]['raster_value'].tolist()
                f.write(f"Route {i}: {route_utci_values}\n")
            f.write("--- End of Raster Values ---\n")

        # Normalize values
        min_val = mean_raster_values.min()
        max_val = mean_raster_values.max()
        mean_raster_values_normalized = ((mean_raster_values - min_val) / (max_val - min_val)) * 100

        # Prepare response data
        routes_data = []
        for i, route in enumerate(interpolated_routes):
            # Get all UTCI values for this route
            route_utci_values = all_routes_gdf[all_routes_gdf['route_id'] == i]['raster_value'].tolist()
            
            route_data = {
                'coordinates': route,
                'mean_utci': float(mean_raster_values[i]),
                'min_utci': float(min_raster_values[i]),
                'max_utci': float(max_raster_values[i]),
                'normalized_utci': float(mean_raster_values_normalized[i]),
                'utci_values': [float(val) for val in route_utci_values],  # Add all UTCI values
                'shade_percentage': float(shade_percentages[i]),  # Add shade percentage
                'duration': google_routes_data[i]['duration'],
                'distance': google_routes_data[i]['distance']
            }
            routes_data.append(route_data)
            #print(f"Route {i} data:", route_data)  # Debug print

        response_data = {
            'routes': routes_data,
            'origin': {'lat': origin_lat, 'lng': origin_lon},
            'destination': {'lat': destination_lat, 'lng': destination_lon},
            'utci_range': {
                'min': float(min_val),
                'max': float(max_val)
            }
        }

        print("Successfully processed routes")
        return jsonify(response_data)

    except Exception as e:
        print(f"Error processing route: {str(e)}")
        print("Traceback:")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug) 