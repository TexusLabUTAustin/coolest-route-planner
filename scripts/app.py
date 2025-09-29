import streamlit as st
import requests
import polyline
import numpy as np
from pyproj import Proj, transform, Geod
import geopandas as gpd
import rasterio
from shapely.geometry import Point
import os
from utils import get_directions_polylines, decode_polyline, interpolate_geopath_equidistant, create_shapefiles_and_extract_raster_values, get_lat_lon_from_address, set_background_gradient
import plotly.express as px
import pandas as pd
import numpy as np
import pandas as pd
import plotly.express as px
from matplotlib.colors import LinearSegmentedColormap, to_hex
import plotly.graph_objects as go
import streamlit as st
import folium
from streamlit_folium import folium_static
from folium.plugins import HeatMap, AntPath
import geopandas as gpd


# Assuming all the functions you provided earlier are defined here
# (get_directions_polylines, decode_polyline, interpolate_geopath_equidistant, create_shapefiles_and_extract_raster_values)




import streamlit as st
from datetime import datetime, timedelta
import pytz

# Function to round the current time to the nearest hour
def get_nearest_hour():
    tz = pytz.timezone('US/Central')  # Adjust timezone to your local timezone
    now = datetime.now(tz)
    nearest_hour = now.replace(minute=0, second=0, microsecond=0)
    if now.minute >= 30:
        nearest_hour += timedelta(hours=1)
    return nearest_hour  # Return the datetime object instead of the string


# Streamlit application starts here
def main():
    set_background_gradient()
    st.title('Name Under Development')
    st.sidebar.header('Input Parameters')
    api_key = "AIzaSyDA1XsDPGVPIJGSHi7-NTRVZODYIlbI7OE"#= st.sidebar.text_input('Google Maps API Key')
    place_origin = st.sidebar.text_input('Origin (place name)')
    place_destination = st.sidebar.text_input('Destination (place name)')
    geotiff_path = "UTCI_1600.tif" #st.sidebar.text_input('Path to GeoTIFF File')
    output_dir = st.sidebar.text_input('Output Directory for Shapefiles', 'output')
# Create a list of times for the dropdown
    times = [f"{i:02d}00" for i in range(24)]
    times_display = [(datetime.strptime(f"{i:02d}:00", "%H:%M").strftime("%I:%M %p")).lstrip("0") for i in range(24)]
    times_24hour = [f"{i:02d}00" for i in range(24)]



    # Current nearest hour
    current_nearest_hour = get_nearest_hour()
    current_nearest_hour_index = current_nearest_hour.hour

    # User selects the time from the dropdown
    #selected_time_display = st.sidebar.selectbox("Select the closest time of day:", times_display, index=current_nearest_hour_index)
    #selected_time_24hour = times_24hour[times_display.index(selected_time_display)]

    #geotiff_path = f"UTCI_{selected_time_24hour}.tif"


    # Show the selected file path (you can also add code to load and display the GeoTIFF here)

    if st.sidebar.button('Process Route'):
        if not api_key or not place_origin or not place_destination or not geotiff_path:
            st.error("Please fill in all fields.")
        else:
            # Get latitude and longitude for both origin and destination
            origin_lat, origin_lon = get_lat_lon_from_address(place_origin, api_key)
            destination_lat, destination_lon = get_lat_lon_from_address(place_destination, api_key)

            if origin_lat is None or destination_lat is None:
                st.error("Failed to find coordinates for one or more locations.")
            else:
                origin = f"{origin_lat}, {origin_lon}"
                destination = f"{destination_lat}, {destination_lon}"
            try:
                polylines = get_directions_polylines(origin, destination, api_key=api_key)
                decoded_coords = [decode_polyline(poly) for poly in polylines]
                interpolated_routes = [interpolate_geopath_equidistant(coords, 4) for coords in decoded_coords]

                gdfs, _ = create_shapefiles_and_extract_raster_values(interpolated_routes, geotiff_path, output_dir)

                all_routes_gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))

                if all_routes_gdf.crs != 'epsg:4326':
                    all_routes_gdf = all_routes_gdf.to_crs('epsg:4326')

                # Compute the mean raster value for each route and use it as a coloring measure
                all_routes_gdf['route_id'] = np.repeat(np.arange(len(gdfs)), [len(gdf) for gdf in gdfs])
                mean_raster_values = all_routes_gdf.groupby('route_id')['raster_value'].mean()
                
                # Normalize the mean raster values to 0-100 scale
                min_val = mean_raster_values.min()
                max_val = mean_raster_values.max()
                mean_raster_values_normalized = ((mean_raster_values - min_val) / (max_val - min_val)) * 100
                
                all_routes_gdf['mean_raster'] = all_routes_gdf['route_id'].map(mean_raster_values)
                all_routes_gdf['mean_raster_normalized'] = all_routes_gdf['route_id'].map(mean_raster_values_normalized)
                
                unique_values = np.sort(np.unique(all_routes_gdf['mean_raster_normalized']))
                num_unique_values = len(unique_values)

                # Create a color map from red to blue
                cmap = LinearSegmentedColormap.from_list("custom_red_blue", ["red", "blue"], N=num_unique_values)
                colors = [cmap(i) for i in range(num_unique_values)]
                colors_hex = [to_hex(color) for color in colors]

                # Create color scale for Plotly (value to color mapping)
                color_scale = [[unique_values[i], colors_hex[i]] for i in range(num_unique_values)]

                # Map the normalized raster values to colors for the plot
                all_routes_gdf['color'] = all_routes_gdf['mean_raster_normalized'].apply(
                    lambda x: colors_hex[np.where(unique_values == x)[0][0]]
                )               

                # Plot
                # Calculate bounds for auto-zoom
                bounds = []
                for route in interpolated_routes:
                    for coord in route:
                        bounds.append(coord)
                bounds = np.array(bounds)
                min_lat, min_lon = bounds.min(axis=0)
                max_lat, max_lon = bounds.max(axis=0)
                
                # Create map with auto-zoom
                m = folium.Map(location=[(min_lat + max_lat)/2, (min_lon + max_lon)/2])
                m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]], padding=(30, 30))
                
                # Add start and end markers with different symbols
                folium.Marker(
                    [origin_lat, origin_lon],
                    popup='Start',
                    icon=folium.Icon(color='green', icon='flag', prefix='fa')
                ).add_to(m)
                
                folium.Marker(
                    [destination_lat, destination_lon],
                    popup='End',
                    icon=folium.Icon(color='red', icon='flag-checkered', prefix='fa')
                ).add_to(m)
                
                # Add each route with its corresponding color
                for route_id, route in enumerate(interpolated_routes):
                    # Get the color for this route based on its normalized mean raster value
                    route_color = colors_hex[np.where(unique_values == mean_raster_values_normalized[route_id])[0][0]]
                    folium.PolyLine(
                        route,
                        color=route_color,
                        weight=5,
                        opacity=0.7,
                        popup=f"Route {route_id + 1}<br>Mean UTCI: {mean_raster_values[route_id]:.2f}"
                    ).add_to(m)

                # Add animated routes using AntPath
                for route_id, route in enumerate(interpolated_routes):
                    route_color = colors_hex[np.where(unique_values == mean_raster_values_normalized[route_id])[0][0]]
                    AntPath(
                        route,
                        color=route_color,
                        weight=3,
                        opacity=0.7,
                        delay=800,
                        dash_array=[10, 20],
                        popup=f"Route {route_id + 1}<br>Mean UTCI: {mean_raster_values[route_id]:.2f}"
                    ).add_to(m)

                # Display the map
                folium_static(m)

                # Add legend using Streamlit components
                st.markdown("### UTCI Temperature Legend")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("""
                        <div style="display: flex; align-items: center; gap: 12px; padding: 8px; background-color: #f0f2f6; border-radius: 8px;">
                            <div style="width: 25px; height: 25px; background-color: red;"></div>
                            <span style="font-size: 16px; font-weight: 500; color: black;">Warm</span>
                        </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown("""
                        <div style="display: flex; align-items: center; gap: 12px; padding: 8px; background-color: #f0f2f6; border-radius: 8px;">
                            <div style="width: 25px; height: 25px; background-color: purple;"></div>
                            <span style="font-size: 16px; font-weight: 500; color: black;">Cooler</span>
                        </div>
                    """, unsafe_allow_html=True)
                with col3:
                    st.markdown("""
                        <div style="display: flex; align-items: center; gap: 12px; padding: 8px; background-color: #f0f2f6; border-radius: 8px;">
                            <div style="width: 25px; height: 25px; background-color: blue;"></div>
                            <span style="font-size: 16px; font-weight: 500; color: black;">Coolest</span>
                        </div>
                    """, unsafe_allow_html=True)

                st.success('Shapefiles created, raster values extracted, and plots generated successfully.')

            except Exception as e:
                st.error(f"Error processing the data: {str(e)}")

if __name__ == "__main__":
    main()
