#!/usr/bin/env python3
"""
Texas Capitol -> UT Tower: print exact route ranks, shade %, and mean UTCI for .tif and .npz,
and optionally what the backend API returns (so script and local app can be compared).

Usage:
  python report_tif_npz_texas_capitol_ut_tower.py           # script-only (TIF + NPZ blocks)
  python report_tif_npz_texas_capitol_ut_tower.py --api   # also call backend API (backend must be running)
"""
import os
import sys
import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
os.chdir(SCRIPT_DIR)
os.environ["PROFILE"] = "0"

from utils import (
    get_lat_lon_from_address,
    get_directions_polylines,
    decode_polyline,
    interpolate_geopath_equidistant,
    create_shapefiles_and_extract_raster_values,
)

API_KEY = "AIzaSyDA1XsDPGVPIJGSHi7-NTRVZODYIlbI7OE"
GEOTIFF_PATH = os.path.join(SCRIPT_DIR, "UTCI_1600.tif")
GEOTIFF_NPZ_PATH = os.path.join(SCRIPT_DIR, "UTCI_1600.npz")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Use same strings the frontend might send (user types in the app)
ORIGIN = "Texas Capitol, Austin"
DESTINATION = "UT Tower, Austin"
SHADE_PERCENTILE = 90
API_BASE = "http://localhost:5001"


def get_routes():
    o_lat, o_lon = get_lat_lon_from_address(ORIGIN, API_KEY)
    d_lat, d_lon = get_lat_lon_from_address(DESTINATION, API_KEY)
    if o_lat is None or d_lat is None:
        raise RuntimeError("Geocoding failed")
    routes_data = get_directions_polylines(
        f"{o_lat}, {o_lon}", f"{d_lat}, {d_lon}", api_key=API_KEY
    )
    if not routes_data:
        raise RuntimeError("No routes found")
    return [
        interpolate_geopath_equidistant(decode_polyline(r["polyline"]), 4)
        for r in routes_data
    ]


def stats(gdfs):
    import geopandas as gpd
    all_gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))
    all_gdf["route_id"] = np.repeat(np.arange(len(gdfs)), [len(g) for g in gdfs])
    mean_per_route = all_gdf.groupby("route_id")["raster_value"].mean()
    overall_min = all_gdf["raster_value"].min()
    overall_max = all_gdf["raster_value"].max()
    shade_threshold = overall_min + (overall_max - overall_min) * SHADE_PERCENTILE / 100
    shade_pcts = []
    for i in range(len(gdfs)):
        route_data = all_gdf[all_gdf["route_id"] == i]
        n = len(route_data)
        below = (route_data["raster_value"] < shade_threshold).sum()
        shade_pcts.append((below / n * 100) if n else 0.0)
    mean_list = [float(mean_per_route[i]) for i in range(len(gdfs))]
    order = np.argsort(mean_list)
    ranks = [0] * len(mean_list)
    ranks[order[0]] = 0
    for k in range(1, len(order)):
        ranks[order[k]] = ranks[order[k - 1]] if mean_list[order[k]] <= mean_list[order[k - 1]] + 1e-9 else k
    return mean_list, shade_pcts, ranks


def call_backend_api(origin, destination, base_url=API_BASE):
    """POST to /api/process-route and return response JSON."""
    try:
        import urllib.request
        import json
        url = f"{base_url.rstrip('/')}/api/process-route"
        body = json.dumps({"origin": origin, "destination": destination}).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def main():
    call_api = "--api" in sys.argv
    if not os.path.exists(GEOTIFF_PATH):
        print(f"Missing {GEOTIFF_PATH}")
        sys.exit(1)
    if not os.path.exists(GEOTIFF_NPZ_PATH):
        print(f"Missing {GEOTIFF_NPZ_PATH}")
        sys.exit(1)

    print(f"Origin:      '{ORIGIN}'")
    print(f"Destination: '{DESTINATION}'")
    print(f"Fetching routes...")
    routes = get_routes()
    n = len(routes)
    print(f"Found {n} route(s)\n")

    out_npz = os.path.join(OUTPUT_DIR, "report_npz")
    os.makedirs(out_npz, exist_ok=True)

    gdfs_tif, _ = create_shapefiles_and_extract_raster_values(routes, GEOTIFF_PATH, OUTPUT_DIR)
    gdfs_npz, _ = create_shapefiles_and_extract_raster_values(routes, GEOTIFF_NPZ_PATH, out_npz)

    mean_tif, shade_tif, ranks_tif = stats(gdfs_tif)
    mean_npz, shade_npz, ranks_npz = stats(gdfs_npz)

    # Backend uses .npz if present, else .tif
    raster_used = "NPZ" if os.path.exists(GEOTIFF_NPZ_PATH) else "TIF"
    mean_backend = mean_npz if raster_used == "NPZ" else mean_tif
    shade_backend = shade_npz if raster_used == "NPZ" else shade_tif
    ranks_backend = ranks_npz if raster_used == "NPZ" else ranks_tif

    print("=" * 60)
    print("TIF (script, same routes)")
    print("=" * 60)
    for i in range(n):
        print(f"  Route {i}:  rank={ranks_tif[i]}  mean_utci={mean_tif[i]:.4f}  shade%={shade_tif[i]:.2f}")
    print()

    print("=" * 60)
    print("NPZ (script, same routes)")
    print("=" * 60)
    for i in range(n):
        print(f"  Route {i}:  rank={ranks_npz[i]}  mean_utci={mean_npz[i]:.4f}  shade%={shade_npz[i]:.2f}")
    print()

    print("=" * 60)
    print(f"BACKEND WOULD USE: {raster_used} (script logic, same origin/dest)")
    print("=" * 60)
    for i in range(n):
        print(f"  Route {i}:  rank={ranks_backend[i]}  mean_utci={mean_backend[i]:.4f}  shade%={shade_backend[i]:.2f}")
    print("=" * 60)

    if call_api:
        print("\nCalling backend API (same origin/destination)...")
        data = call_backend_api(ORIGIN, DESTINATION)
        if "error" in data:
            print("API error:", data["error"])
            return
        routes_api = data.get("routes") or []
        print("\n" + "=" * 60)
        print("BACKEND API RESPONSE (what the app receives)")
        print("=" * 60)
        for i, r in enumerate(routes_api):
            print(f"  Route {i}:  mean_utci={r.get('mean_utci', 0):.4f}  shade%={r.get('shade_percentage', 0):.2f}")
        print("=" * 60)
        if len(routes_api) != n:
            print(f"\n>>> Route count mismatch: script has {n} routes, API returned {len(routes_api)}")


if __name__ == "__main__":
    main()
