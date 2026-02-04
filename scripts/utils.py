# utils.py

import time
import requests
import polyline
import numpy as np
from pyproj import Proj, transform, Geod
import geopandas as gpd
import rasterio
from shapely.geometry import Point
import os
try:
    import streamlit as st
except ImportError:
    st = None  # streamlit not available (e.g., in Flask backend)



def _log_profile(step_name, elapsed_sec):
    """Log profile timing with [PROFILE] prefix for greppable logs."""
    print(f"[PROFILE] utils.{step_name}: {elapsed_sec:.3f}s", flush=True)


def get_directions_polylines(origin, destination, mode='walking', api_key=''):
    t0 = time.perf_counter()
    url = f"https://maps.googleapis.com/maps/api/directions/json?origin={origin}&destination={destination}&mode={mode}&alternatives=true&key={api_key}"

    try:
        t = time.perf_counter()
        response = requests.get(url)
        _log_profile("directions_http_request", time.perf_counter() - t)
        t = time.perf_counter()
        data = response.json()
        _log_profile("directions_json_parse", time.perf_counter() - t)
        routes_data = []

        if data['status'] == 'OK':
            # Loop through each route and extract the polyline and route details
            for route in data['routes']:
                polyline = route['overview_polyline']['points']
                
                # Extract walking time and distance from the first leg
                leg = route['legs'][0]
                duration = leg['duration']['text']  # e.g., "1 hour 30 mins"
                distance = leg['distance']['text']  # e.g., "5.2 km"
                
                routes_data.append({
                    'polyline': polyline,
                    'duration': duration,
                    'distance': distance
                })
            _log_profile("get_directions_polylines(TOTAL)", time.perf_counter() - t0)
            return routes_data
        else:
            print("Failed to retrieve directions")
            return []
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return []
    

def decode_polyline(polyline_str):
    """
    Decodes a polyline that has been encoded using Google's algorithm
    https://developers.google.com/maps/documentation/utilities/polylinealgorithm
    
    Args:
    polyline_str (str): Encoded polyline string.
    
    Returns:
    list of tuples: List of latitude and longitude pairs.
    """
    index, lat, lng = 0, 0, 0
    coordinates = []
    changes = {'latitude': 0, 'longitude': 0}

    # Coordinates have variable length when encoded, so keep decoding until we reach the end.
    while index < len(polyline_str):
        # Calculate next latitude
        for unit in ['latitude', 'longitude']:
            shift, result = 0, 0

            while True:
                byte = ord(polyline_str[index]) - 63
                index += 1
                result |= (byte & 0x1f) << shift
                shift += 5
                if not byte >= 0x20:
                    break

            if (result & 1):
                changes[unit] = ~(result >> 1)
            else:
                changes[unit] = (result >> 1)

        lat += changes['latitude']
        lng += changes['longitude']

        coordinates.append((lat / 1e5, lng / 1e5))

    return coordinates

def interpolate_geopath_equidistant(path, distance_between_points):
    """
    Interpolates equidistant points along a path defined by latitude and longitude coordinates.
    
    :param path: List of tuples, where each tuple is (latitude, longitude)
    :param distance_between_points: Desired approximate distance between interpolated points (in meters)
    :return: List of interpolated (latitude, longitude) tuples, including original points
    """
    geod = Geod(ellps='WGS84')
    utm_zone = int((path[0][1] + 180) / 6) + 1
    proj_utm = Proj(f'+proj=utm +zone={utm_zone} +ellps=WGS84')
    proj_latlon = Proj(proj='latlong', ellps='WGS84')
    
    # Calculate total path distance and determine the number of points to interpolate
    total_distance = 0
    for i in range(len(path) - 1):
        _, _, distance = geod.inv(path[i][1], path[i][0], path[i+1][1], path[i+1][0])
        total_distance += distance
    
    num_points_total = max(int(total_distance / distance_between_points), 1)
    interpolated_path = [path[0]]
    
    for i in range(len(path) - 1):
        # Convert current pair of points to UTM
        x1, y1 = transform(proj_latlon, proj_utm, path[i][1], path[i][0])
        x2, y2 = transform(proj_latlon, proj_utm, path[i+1][1], path[i+1][0])
        
        # Calculate distance for the current segment to determine segment-specific interpolation
        _, _, segment_distance = geod.inv(path[i][1], path[i][0], path[i+1][1], path[i+1][0])
        num_points_segment = max(int(segment_distance / distance_between_points), 1)
        
        # Linearly interpolate in UTM coordinates
        xs = np.linspace(x1, x2, num_points_segment + 2)  # +2 because endpoints are included
        ys = np.linspace(y1, y2, num_points_segment + 2)
        
        # Convert interpolated points back to lat-lon and add to the output, excluding the first point to avoid duplication
        for j in range(1, len(xs) - 1):
            lon, lat = transform(proj_utm, proj_latlon, xs[j], ys[j])
            interpolated_path.append((lat, lon))
    
    interpolated_path.append(path[-1])
    return interpolated_path


def _sample_from_npz(raster_values, transform_tuple, shape_2d, point, scale=1.0):
    """Get raster value at (point.x, point.y). Match rasterio: use floor for (row,col) so .npz matches .tif."""
    from rasterio.transform import Affine
    aff = Affine(*transform_tuple)
    col, row = ~aff * (point.x, point.y)
    # Use floor to match rasterio's src.index(x, y) default (op=numpy.floor)
    row, col = int(np.floor(row)), int(np.floor(col))
    h, w = shape_2d[0], shape_2d[1]
    row = max(0, min(row, h - 1))
    col = max(0, min(col, w - 1))
    val = float(raster_values[row, col])
    return val / scale if scale != 1.0 else val


def create_shapefiles_and_extract_raster_values(interpolated_routes, raster_path, output_dir):
    """Load raster from .tif (rasterio) or .npz (numpy). raster_path can be path to .tif or .npz."""
    t_total = time.perf_counter()
    os.makedirs(output_dir, exist_ok=True)
    shapefile_paths = {}
    gdfs = []
    use_npz = raster_path.lower().endswith(".npz")

    if use_npz:
        t = time.perf_counter()
        data = np.load(raster_path, allow_pickle=False)
        raster_values = data["values"]
        transform_tuple = tuple(data["transform"].tolist())
        sh = data.get("shape", np.array(raster_values.shape))
        shape_2d = (int(sh[0]), int(sh[1])) if sh.size >= 2 else raster_values.shape
        # UTCI values only: stored as int16 * scale; divide by scale when sampling (lat/lon unchanged)
        scale = float(data["scale"]) if "scale" in data else 1.0
        _log_profile("npz_load", time.perf_counter() - t)
    else:
        t = time.perf_counter()
        src = rasterio.open(raster_path)
        _log_profile("raster_open", time.perf_counter() - t)
        try:
            t = time.perf_counter()
            raster_values = src.read(1)
            _log_profile("raster_read_full_band", time.perf_counter() - t)
            transform_tuple = None
            shape_2d = raster_values.shape
        except Exception:
            src.close()
            raise

    for i, route in enumerate(interpolated_routes):
        t_route = time.perf_counter()

        t = time.perf_counter()
        points = [Point(lon, lat) for lat, lon in route]
        gdf = gpd.GeoDataFrame(geometry=points, crs="EPSG:4326")
        _log_profile(f"route_{i}_gdf_create", time.perf_counter() - t)

        t = time.perf_counter()
        gdf = gdf.to_crs(epsg=6343)
        _log_profile(f"route_{i}_to_crs", time.perf_counter() - t)

        t = time.perf_counter()
        raster_values_list = []
        if use_npz:
            for point in gdf.geometry:
                val = _sample_from_npz(raster_values, transform_tuple, shape_2d, point, scale)
                raster_values_list.append(val)
        else:
            for point in gdf.geometry:
                row, col = src.index(point.x, point.y)
                raster_values_list.append(raster_values[row, col])
        _log_profile(f"route_{i}_sample_points(n={len(gdf)})", time.perf_counter() - t)

        gdf["raster_value"] = raster_values_list
        gdfs.append(gdf)

        t = time.perf_counter()
        shapefile_name = f"route_{i+1}_with_raster_values.shp"
        shapefile_path = os.path.join(output_dir, shapefile_name)
        gdf.to_file(shapefile_path)
        _log_profile(f"route_{i}_to_file_shp", time.perf_counter() - t)

        shapefile_paths[i + 1] = shapefile_path
        _log_profile(f"route_{i}(TOTAL)", time.perf_counter() - t_route)

    if not use_npz:
        src.close()

    _log_profile("create_shapefiles_and_extract_raster_values(TOTAL_utils)", time.perf_counter() - t_total)
    return gdfs, shapefile_paths

import requests

def get_lat_lon_from_address(address, api_key):
    """Convert an address to latitude and longitude using Google Geocoding API."""
    t0 = time.perf_counter()
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": api_key}
    t = time.perf_counter()
    response = requests.get(base_url, params=params)
    _log_profile("geocode_http_request", time.perf_counter() - t)
    if response.status_code == 200:
        data = response.json()
        if data['status'] == 'OK':
            location = data['results'][0]['geometry']['location']
            _log_profile("get_lat_lon_from_address(TOTAL)", time.perf_counter() - t0)
            return (location['lat'], location['lng'])
        else:
            return None, None
    else:
        return None, None

def set_background_gradient():
    """
    A function to change the background to a gradient.
    """
    if st is not None:
        st.markdown(
            """
            <style>
            .stApp {
                background-image: linear-gradient(to right, lightblue, white);
                
            }
            h1 {
                color: black !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )