#!/usr/bin/env python3
"""
Compare .tif vs .npz on two route legs; check that route ranks, shade %, and mean UTCI
match within tolerance.

Routes:
  1) 3233 Harmon Ave -> UT Tower
  2) UT Tower -> Texas Capitol

Requires: UTCI_1600.tif and UTCI_1600.npz in scripts/, and API key.
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

# (origin, destination) for each leg
LEGS = [
    ("3233 harmon ave, Austin", "UT Tower, Austin"),
    ("UT Tower, Austin", "Texas Capitol, Austin"),
]

SHADE_PERCENTILE = 90  # same as backend

# Tolerances (tight so route ranks don't flip between .tif and .npz)
TOL_MEAN_UTCI = 0.02   # mean UTCI: must match closely so ranking is identical
TOL_SHADE_PCT = 2.0    # shade percentage points
RANKS_MUST_MATCH = True


def get_routes_for_leg(origin, destination):
    """Return list of interpolated routes (one per alternative) for one leg."""
    o_lat, o_lon = get_lat_lon_from_address(origin, API_KEY)
    d_lat, d_lon = get_lat_lon_from_address(destination, API_KEY)
    if o_lat is None or d_lat is None:
        raise RuntimeError(f"Geocoding failed: {origin} / {destination}")
    routes_data = get_directions_polylines(
        f"{o_lat}, {o_lon}", f"{d_lat}, {d_lon}", api_key=API_KEY
    )
    if not routes_data:
        raise RuntimeError(f"No routes: {origin} -> {destination}")
    interpolated = []
    for r in routes_data:
        decoded = decode_polyline(r["polyline"])
        interpolated.append(interpolate_geopath_equidistant(decoded, 4))
    return interpolated


def route_stats_from_gdfs(gdfs):
    """Mirror backend: mean UTCI per route, shade threshold, shade % per route. Returns (mean_utci_list, shade_pct_list)."""
    import geopandas as gpd
    all_gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))
    all_gdf["route_id"] = np.repeat(np.arange(len(gdfs)), [len(g) for g in gdfs])
    mean_per_route = all_gdf.groupby("route_id")["raster_value"].mean()
    overall_min = all_gdf["raster_value"].min()
    overall_max = all_gdf["raster_value"].max()
    utci_range = overall_max - overall_min
    shade_threshold = overall_min + (utci_range * SHADE_PERCENTILE / 100)
    shade_pcts = []
    for i in range(len(gdfs)):
        route_data = all_gdf[all_gdf["route_id"] == i]
        n = len(route_data)
        below = (route_data["raster_value"] < shade_threshold).sum()
        shade_pcts.append((below / n * 100) if n else 0.0)
    mean_utci_list = [float(mean_per_route[i]) for i in range(len(gdfs))]
    return mean_utci_list, shade_pcts


def rank_by_mean_utci(mean_utci_list):
    """Rank routes by mean UTCI ascending (coolest = 0). Ties get same rank, next rank skips."""
    order = np.argsort(mean_utci_list)
    ranks = np.empty(len(mean_utci_list), dtype=int)
    ranks[order[0]] = 0
    for k in range(1, len(order)):
        if mean_utci_list[order[k]] <= mean_utci_list[order[k - 1]] + 1e-9:
            ranks[order[k]] = ranks[order[k - 1]]
        else:
            ranks[order[k]] = k
    return ranks.tolist()


def main():
    if not os.path.exists(GEOTIFF_PATH):
        print(f"Missing {GEOTIFF_PATH}. Need both .tif and .npz.")
        sys.exit(1)
    if not os.path.exists(GEOTIFF_NPZ_PATH):
        print(f"Missing {GEOTIFF_NPZ_PATH}. Run convert_utci_to_npz.py first.")
        sys.exit(1)

    # Build combined list of interpolated routes (all legs, all alternatives)
    all_routes = []
    labels = []
    for origin, dest in LEGS:
        print(f"Fetching: {origin} -> {dest}")
        leg_routes = get_routes_for_leg(origin, dest)
        for i, r in enumerate(leg_routes):
            all_routes.append(r)
            labels.append(f"{origin} -> {dest} (alt {i+1})")
    n_routes = len(all_routes)
    print(f"Total routes: {n_routes}\n")

    # Run with .tif
    print("Running with .tif...")
    gdfs_tif, _ = create_shapefiles_and_extract_raster_values(
        all_routes, GEOTIFF_PATH, OUTPUT_DIR
    )
    mean_tif, shade_tif = route_stats_from_gdfs(gdfs_tif)
    ranks_tif = rank_by_mean_utci(mean_tif)

    # Run with .npz
    out_npz = os.path.join(OUTPUT_DIR, "compare_npz")
    os.makedirs(out_npz, exist_ok=True)
    print("Running with .npz...")
    gdfs_npz, _ = create_shapefiles_and_extract_raster_values(
        all_routes, GEOTIFF_NPZ_PATH, out_npz
    )
    mean_npz, shade_npz = route_stats_from_gdfs(gdfs_npz)
    ranks_npz = rank_by_mean_utci(mean_npz)

    # Compare
    print("\n" + "=" * 70)
    print("TIF vs NPZ — route ranks, shade %, and mean UTCI (within tolerance)")
    print("=" * 70)

    all_ok = True
    for i in range(n_routes):
        diff_mean = abs(mean_tif[i] - mean_npz[i])
        diff_shade = abs(shade_tif[i] - shade_npz[i])
        rank_ok = ranks_tif[i] == ranks_npz[i]
        mean_ok = diff_mean <= TOL_MEAN_UTCI
        shade_ok = diff_shade <= TOL_SHADE_PCT
        if not (rank_ok and mean_ok and shade_ok):
            all_ok = False
        status = "OK" if (rank_ok and mean_ok and shade_ok) else "FAIL"
        print(f"\nRoute {i}: {labels[i]}")
        print(f"  rank:     tif={ranks_tif[i]} npz={ranks_npz[i]}  {'match' if rank_ok else 'MISMATCH'}")
        print(f"  mean UTCI: tif={mean_tif[i]:.4f} npz={mean_npz[i]:.4f}  diff={diff_mean:.4f}  (tol {TOL_MEAN_UTCI})  {'OK' if mean_ok else 'FAIL'}")
        print(f"  shade %:   tif={shade_tif[i]:.2f} npz={shade_npz[i]:.2f}  diff={diff_shade:.2f}  (tol {TOL_SHADE_PCT})  {'OK' if shade_ok else 'FAIL'}")
        print(f"  -> {status}")

    print("\n" + "-" * 70)
    if all_ok:
        print("PASS: Ranks, mean UTCI, and shade % match within tolerance for all routes.")
    else:
        print("FAIL: At least one route outside tolerance (see above).")
    print("=" * 70)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
