# Coolest Route Planner

A React-based route planning application that uses Cesium 3D visualization to help users find the coolest (most comfortable) routes based on UTCI (Universal Thermal Climate Index) data.

## Features

- **3D Route Visualization**: Interactive 3D map using Cesium.js with Google Photorealistic tiles
- **Topographic Imagery**: Custom imagery layer that follows terrain topography
- **Route Analysis**: Multiple route options with UTCI thermal comfort analysis
- **Real-time Animation**: Animated route visualization with staggered timing
- **Thermal Comfort Metrics**: Routes sorted by thermal comfort (warmest to coolest)
- **Shade Analysis**: Percentage of route in shade for each option

## Technology Stack

- **Frontend**: React.js with Cesium.js for 3D visualization
- **Backend**: Python Flask API for route processing
- **3D Engine**: Cesium.js with Google Photorealistic 3D Tiles
- **Imagery**: Cesium Ion imagery providers with terrain following
- **Data Processing**: Geospatial analysis with raster data

## Project Structure

```
path-app-react-cesium/
├── src/
│   ├── components/
│   │   └── RoutePlanner.js    # Main React component
│   ├── cesiumConfig.js        # Cesium configuration
│   └── App.js                 # Main application
├── scripts/
│   ├── backend.py             # Flask API server
│   ├── app.py                 # Main backend application
│   └── utils.py               # Utility functions
├── public/
│   └── cesium/                # Cesium assets
└── package.json               # Node.js dependencies
```

## Setup Instructions

### Frontend Setup

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm start
```

### Backend Setup

1. Navigate to the scripts directory:
```bash
cd scripts
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Start the Flask server:
```bash
python backend.py
```

## Usage

1. Open the application in your browser (typically `http://localhost:3000`)
2. Enter origin and destination addresses
3. Click "Find Routes" to get thermal comfort analysis
4. View animated 3D routes with thermal comfort rankings
5. Routes are sorted from warmest to coolest based on UTCI data

## Key Features

### 3D Visualization
- Interactive Cesium 3D globe
- Google Photorealistic 3D buildings
- Topographic imagery that follows terrain
- Animated route visualization

### Thermal Analysis
- UTCI-based thermal comfort scoring
- Shade percentage analysis
- Route comparison by thermal comfort
- Real-time thermal data integration

### User Interface
- Clean, modern design
- Responsive layout
- Animated route tiles
- Real-time feedback

## API Endpoints

- `POST /api/process-route`: Process route requests with thermal analysis

## Dependencies

### Frontend
- React
- Cesium.js
- Axios
- CRACO (for Cesium configuration)

### Backend
- Flask
- Geospatial libraries (rasterio, geopandas, etc.)
- Route optimization algorithms

## Contributing

This project is part of the NASA Disasters program and Austin CARES initiative, focusing on urban heat mitigation through intelligent route planning.

## License

This project is developed for research and public benefit in urban heat mitigation.