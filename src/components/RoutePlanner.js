import React, { useState, useEffect, useRef } from 'react';
import { Cartesian3, Cartesian2, createOsmBuildingsAsync, Ion, Math as CesiumMath, Terrain, Viewer, Color, CallbackProperty, Cartographic, Cesium3DTileStyle, createGooglePhotorealistic3DTileset, IonImageryProvider } from 'cesium';
import "cesium/Build/Cesium/Widgets/widgets.css";
import axios from 'axios';
import '../cesiumConfig';

// Set your Cesium ion access token
Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJmMjg0M2EzZC1kM2Q5LTRiOTYtODdhZi04NjA0OGQyZDZkZDMiLCJpZCI6MjkwODI1LCJpYXQiOjE3NDM3NDI0OTl9.WtGmTNEnb4Re5wuCI_F0UFmN7hHF0lEoyxyjBVSkx7s';

const RoutePlanner = () => {
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [routes, setRoutes] = useState([]);
  const [originCoords, setOriginCoords] = useState(null);
  const [destinationCoords, setDestinationCoords] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showRoutes, setShowRoutes] = useState(false);
  const [visibleRoutes, setVisibleRoutes] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const cesiumContainer = useRef(null);
  const viewerRef = useRef(null);
  const sidebarRef = useRef(null);
  const tilesetRef = useRef(null);
  const imageryLayerRef = useRef(null);

  // Distinct colors for routes
  const routeColors = [
    '#FF5733', // Red-Orange (Warm)
    '#33A1FF', // Blue (Cooler)
    '#33FF57', // Green (Coolest)
    '#FF33A1', // Pink
    
    '#A133FF', // Purple
    '#FFD700', // Gold
    '#00CED1', // Turquoise
    '#FF6347', // Tomato
    '#7B68EE', // Medium Slate Blue
    '#32CD32', // Lime Green
  ];

  // Get route label based on sorted order (warmest first, coolest last)
  const getRouteLabel = (routes, index) => {
    if (!routes || routes.length === 0) return `Route ${index + 1}`;
    
    // Routes are now sorted by UTCI (warmest first, coolest last)
    // index 0 = Warmest (Warm), index 1 = Middle (Cooler), index 2 = Coolest
    if (index === 0) return "Warm";
    if (index === 1) return "Cooler";
    if (index === 2) return "Coolest";
    
    return `Route ${index + 1}`;
  };

  useEffect(() => {
    if (cesiumContainer.current && !viewerRef.current) {
      // Initialize the Cesium Viewer
      viewerRef.current = new Viewer(cesiumContainer.current, {
        terrain: Terrain.fromWorldTerrain(),
        animation: false,
        baseLayerPicker: false,
        fullscreenButton: true,
        vrButton: false,
        geocoder: false,
        homeButton: true,
        infoBox: false,
        sceneModePicker: true,
        selectionIndicator: false,
        timeline: false,
        navigationHelpButton: true,
        skyBox: false,
        skyAtmosphere: false
      });

      // Add custom imagery layer that follows topography
      const addTopographicImagery = async () => {
        try {
          const imageryProvider = await IonImageryProvider.fromAssetId(3674571);
          const layer = viewerRef.current.imageryLayers.addImageryProvider(imageryProvider);
          
          // Store reference to the imagery layer
          imageryLayerRef.current = layer;
          
          // Configure the layer to follow terrain topography
          layer.alpha = 0.85; // Higher opacity to make it more visible above Google layer
          layer.brightness = 1.2; // Brighter to stand out
          layer.contrast = 1.3; // Enhanced contrast for better terrain visibility
          layer.hue = 0.0; // No hue adjustment
          layer.saturation = 1.1; // Slightly increased saturation to make it more prominent
          layer.gamma = 1.0; // Normal gamma
          
          // Enable terrain following - this makes the imagery follow the terrain contours
          layer.show = true;
          
          // Position the imagery layer above other layers
          // Move it to the top so it appears above the Google Photorealistic layer
          viewerRef.current.imageryLayers.raiseToTop(layer);
          
          // Add a height offset to make the imagery appear 500 feet higher
          // This creates a visual effect of the imagery being elevated above the terrain
          layer.alpha = 0.6; // More transparent to show it's elevated
          layer.brightness = 1.1; // Slightly brighter to emphasize elevation
          
          console.log('Topographic imagery layer added successfully with terrain following');
        } catch (error) {
          console.warn('Failed to load topographic imagery layer:', error);
        }
      };

      // Add Google Photorealistic 3D Tiles (only if not already loaded)
      if (!tilesetRef.current) {
        createGooglePhotorealistic3DTileset().then(tileset => {
          // Set initial style for buildings
          tileset.style = new Cesium3DTileStyle({
            color: 'color("white", 1)'  // 30% opacity for all buildings
          });
          
          viewerRef.current.scene.primitives.add(tileset);
          tilesetRef.current = tileset; // Store reference to prevent re-loading
        }).catch(error => {
          console.warn('Failed to load Google Photorealistic 3D Tiles:', error);
        });
      }

      // Add the topographic imagery layer
      addTopographicImagery();

      // Set initial view to Austin downtown
      viewerRef.current.camera.flyTo({
        destination: Cartesian3.fromDegrees(-97.7431, 30.2672, 800), // Austin downtown coordinates
        orientation: {
          heading: CesiumMath.toRadians(0.0),
          pitch: CesiumMath.toRadians(-20.0), // Slightly steeper angle for better downtown view
        }
      });
    }

    return () => {
      if (viewerRef.current) {
        // Remove imagery layer if it exists
        if (imageryLayerRef.current) {
          viewerRef.current.imageryLayers.remove(imageryLayerRef.current);
          imageryLayerRef.current = null;
        }
        
        // Remove tileset if it exists
        if (tilesetRef.current) {
          viewerRef.current.scene.primitives.remove(tilesetRef.current);
          tilesetRef.current = null;
        }
        
        // Let Cesium handle its own cleanup
        viewerRef.current.destroy();
        viewerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (viewerRef.current && originCoords && destinationCoords) {
      // Store references to our entities
      const entities = [];
      const animationStartTime = Date.now();
      const animationDuration = 4000; // 4 seconds per route (slower)
      const delayBetweenRoutes = 1000; // 1 second delay between routes

      // Add routes one by one with delays
      routes.forEach((route, index) => {
        // Convert coordinates to Cartesian3 with terrain height
        const positions = route.coordinates.map(coord => {
          const cartographic = Cartographic.fromDegrees(coord[1], coord[0]);
          // Sample terrain height with better precision
          const terrainHeight = viewerRef.current.scene.globe.getHeight(cartographic, new Cartographic()) || 0;
          // Add a larger offset to ensure visibility above terrain
          return Cartesian3.fromDegrees(coord[1], coord[0], terrainHeight + 5); // 10 meters above terrain
        });

        // Calculate delay for this route (each route starts after the previous one)
        const routeDelay = index * (animationDuration + delayBetweenRoutes);
        
        // Create animated positions with staggered timing
        const animatedPositions = new CallbackProperty((time) => {
          const elapsed = Date.now() - animationStartTime - routeDelay;
          
          // Don't start animation until delay has passed
          if (elapsed < 0) {
            return [];
          }
          
          const progress = Math.min(elapsed / animationDuration, 1.0);
          
          // Calculate how many points to show based on progress
          const numPoints = Math.floor(positions.length * progress);
          return positions.slice(0, numPoints);
        }, false);

        const routeEntity = viewerRef.current.entities.add({
          polyline: {
            positions: animatedPositions,
            width: 9,
            material: new Color.fromCssColorString(routeColors[index % routeColors.length]),
            clampToGround: false, // Ensure the line is not clamped to ground
          },
        });
        entities.push(routeEntity);

        // Add start point marker
        const startMarker = viewerRef.current.entities.add({
          position: positions[0],
          point: {
            pixelSize: 16,
            color: Color.fromCssColorString('#2ECC71'),
            outlineColor: Color.WHITE,
            outlineWidth: 3,
            heightReference: 1, // Clamp to ground
          },
          label: {
            text: `📍 START: ${origin}`,
            font: 'bold 18pt "Segoe UI", Arial, sans-serif',
            fillColor: Color.WHITE,
            outlineColor: Color.fromCssColorString('#27AE60'),
            outlineWidth: 3,
            style: 2, // FILL_AND_OUTLINE
            pixelOffset: new Cartesian2(0, -50),
            heightReference: 1, // Clamp to ground
            backgroundColor: Color.fromCssColorString('rgba(46, 204, 113, 0.9)'),
            backgroundPadding: new Cartesian2(14, 10),
            showBackground: true,
            scale: 1.0,
            horizontalOrigin: 1, // CENTER
            verticalOrigin: 2, // BOTTOM
            disableDepthTestDistance: Number.POSITIVE_INFINITY
          }
        });
        entities.push(startMarker);

        // Add end point marker
        const endMarker = viewerRef.current.entities.add({
          position: positions[positions.length - 1],
          point: {
            pixelSize: 16,
            color: Color.fromCssColorString('#E74C3C'),
            outlineColor: Color.WHITE,
            outlineWidth: 3,
            heightReference: 1, // Clamp to ground
          },
          label: {
            text: `🎯 END: ${destination}`,
            font: 'bold 18pt "Segoe UI", Arial, sans-serif',
            fillColor: Color.WHITE,
            outlineColor: Color.fromCssColorString('#C0392B'),
            outlineWidth: 3,
            style: 2, // FILL_AND_OUTLINE
            pixelOffset: new Cartesian2(0, -50),
            heightReference: 1, // Clamp to ground
            backgroundColor: Color.fromCssColorString('rgba(231, 76, 60, 0.9)'),
            backgroundPadding: new Cartesian2(14, 10),
            showBackground: true,
            scale: 1.0,
            horizontalOrigin: 1, // CENTER
            verticalOrigin: 2, // BOTTOM
            disableDepthTestDistance: Number.POSITIVE_INFINITY
          }
        });
        entities.push(endMarker);

        // If this is the first route, orient the camera
        if (index === 0 && positions.length >= 2) {
          // Calculate bearing between first and last points
          const start = positions[0];
          const end = positions[positions.length - 1];
          const bearing = CesiumMath.toDegrees(
            Math.atan2(
              end.x - start.x,
              end.y - start.y
            )
          );

          // Sample terrain height at start point
          const cartographic = Cartographic.fromDegrees(
            originCoords[1],
            originCoords[0]
          );
          const terrainHeight = viewerRef.current.scene.globe.getHeight(cartographic) || 0;

          // Calculate position 500 meters behind the start point
          const offsetDistance = 500; // meters
          const offsetBearing = (bearing + 180) % 360; // Opposite direction
          
          // Convert to radians
          const lat1 = CesiumMath.toRadians(originCoords[0]);
          const lon1 = CesiumMath.toRadians(originCoords[1]);
          const brng = CesiumMath.toRadians(offsetBearing);
          
          // Calculate new position
          const R = 6371000; // Earth's radius in meters
          const d = offsetDistance / R;
          
          const lat2 = Math.asin(
            Math.sin(lat1) * Math.cos(d) + 
            Math.cos(lat1) * Math.sin(d) * Math.cos(brng)
          );
          
          const lon2 = lon1 + Math.atan2(
            Math.sin(brng) * Math.sin(d) * Math.cos(lat1),
            Math.cos(d) - Math.sin(lat1) * Math.sin(lat2)
          );

          // Set camera position and orientation with terrain height
          viewerRef.current.camera.setView({
            destination: Cartesian3.fromDegrees(
              CesiumMath.toDegrees(lon2),
              CesiumMath.toDegrees(lat2),
              terrainHeight + 250 // Much closer to the ground
            ),
            orientation: {
              heading: CesiumMath.toRadians(bearing),
              pitch: CesiumMath.toRadians(-20), // More parallel to ground
              roll: 0
            }
          });
        }


      });

      // Cleanup function
      return () => {
        // Wait for next frame to ensure all operations are complete
        requestAnimationFrame(() => {
          if (viewerRef.current) {
            // Remove entities one by one
            entities.forEach(entity => {
              if (entity && viewerRef.current.entities.contains(entity)) {
                viewerRef.current.entities.remove(entity);
              }
            });
          }
        });
      };
    }
  }, [routes, originCoords, destinationCoords]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Prevent duplicate submissions
    if (isSubmitting || loading) {
      return;
    }
    
    setIsSubmitting(true);
    setLoading(true);
    setError(null);
    setShowRoutes(false);
    setRoutes([]);

    try {
      console.log('Sending request to backend...', { origin, destination });
      const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      const response = await axios.post(`${API_URL}/api/process-route`, 
        { origin, destination },
        {
          headers: {
            'Content-Type': 'application/json',
          },
          timeout: 30000, // 30 second timeout
        }
      );
      console.log('Response received:', response.data);
      
      // Log detailed information about the first route
      if (response.data.routes && response.data.routes.length > 0) {
        console.log('First route details:', JSON.stringify(response.data.routes[0], null, 2));
        // Check if distance and duration properties exist
        console.log('Route distance:', response.data.routes[0].distance);
        console.log('Route duration:', response.data.routes[0].duration);
      }

      // Check if routes data exists
      if (!response.data.routes || !Array.isArray(response.data.routes) || response.data.routes.length === 0) {
        throw new Error('No routes found. Please check your addresses and try again.');
      }

      const { routes: newRoutes, origin: orig, destination: dest } = response.data;
      
      // Check if coordinates exist and are valid
      if (!orig || !orig.lat || !orig.lng || !dest || !dest.lat || !dest.lng) {
        throw new Error('Invalid coordinates received from server. Please check your addresses and try again.');
      }
      
      setOriginCoords([orig.lat, orig.lng]);
      setDestinationCoords([dest.lat, dest.lng]);
      
      // Sort routes by UTCI (warmest first, coolest last)
      const sortedRoutes = [...newRoutes].sort((a, b) => b.mean_utci - a.mean_utci);
      
      setTimeout(() => {
        setRoutes(sortedRoutes);
        setShowRoutes(true);
        setVisibleRoutes([]); // Reset visible routes
        
        // Animate routes appearing one by one in sidebar when map routes start
        sortedRoutes.forEach((route, index) => {
          const routeDelay = index * (4000 + 1000); // Match map animation timing (4s + 1s delay)
          setTimeout(() => {
            setVisibleRoutes(prev => [...prev, route]);
            
            // Auto-scroll to show the new tile fully - FAST
            setTimeout(() => {
              const sidebar = sidebarRef.current;
              const routeList = document.querySelector('.route-list');
              
              if (sidebar && routeList) {
                // Instant scroll to bottom - no smooth animation
                sidebar.scrollTop = sidebar.scrollHeight;
                
                // Also try scrolling the last tile into view instantly
                const lastTile = routeList.lastElementChild;
                if (lastTile) {
                  lastTile.scrollIntoView({ behavior: 'auto', block: 'end' });
                }
              }
            }, 100); // Much faster delay
          }, routeDelay);
        });
      }, 100);
    } catch (err) {
      console.error('Error details:', {
        message: err.message,
        response: err.response?.data,
        status: err.response?.status,
        statusText: err.response?.statusText,
        config: err.config
      });
      setError(
        err.response?.data?.error || 
        err.message || 
        'An error occurred while processing the route. Please make sure the backend server is running.'
      );
    } finally {
      setLoading(false);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="route-planner">
      <div className="top-banner">
        <div className="banner-content">
          <div className="title-group">
            <h2>Coolest Route Planner</h2>
          </div>
          
          <div className="partners-section">
            <div className="partner-logo">
              <div className="logo-placeholder">
                <img src="/nasa_disasters_1.jpg" alt="NASA Disasters" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
              </div>
            </div>
            
            <div className="partner-logo">
              <div className="logo-placeholder">
                <span style={{ fontSize: '1.2em', fontWeight: 'bold', color: '#333', fontStyle: 'italic' }}>Austin CARES</span>
              </div>
            </div>
            
            <div className="partner-logo">
              <div className="logo-placeholder">
                <img src="/texus_logo_1.svg" alt="New Logo" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
              </div>
            </div>
            
            <div className="partner-logo">
              <div className="logo-placeholder">
                <img src="/Colab_blue_logo.avif" alt="UT City CoLab" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div className="main-content">
        <div className="sidebar" ref={sidebarRef}>
          <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label htmlFor="origin">Origin:</label>
            <input
              type="text"
              id="origin"
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
              placeholder="Enter origin address"
              required
            />
          </div>
          <div className="input-group">
            <label htmlFor="destination">Destination:</label>
            <input
              type="text"
              id="destination"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              placeholder="Enter destination address"
              required
            />
          </div>
          <button type="submit" disabled={loading || isSubmitting}>
            {loading ? 'Processing...' : 'Find Routes'}
          </button>
          
          {(routes.length > 0 || visibleRoutes.length > 0) && (
            <button 
              type="button" 
              onClick={() => {
                setRoutes([]);
                setVisibleRoutes([]);
                setOriginCoords(null);
                setDestinationCoords(null);
              }}
              className="clear-button"
            >
              Clear Routes
            </button>
          )}
        </form>
        {error && <div className="error">{error}</div>}
        
        {visibleRoutes.length > 0 && (
          <div className="route-list">
            {visibleRoutes.map((route, index) => {
              console.log(`Route ${index} data:`, route);
              return (
                <div key={index} className="route-item animate-slide-in">
                  <span className="route-label">
                    {getRouteLabel(visibleRoutes, index)}
                    <span className="route-utci">
                      (Mean UTCI: {route.mean_utci.toFixed(2)})
                    </span>
                    <span className="route-details">
                      <span className="route-distance">Distance: {route.distance || 'N/A'}</span>
                      <span className="route-duration">Time: {route.duration || 'N/A'}</span>
                    </span>
                  </span>
                  <div className="route-info">
                    <div className="route-header">
                      <h3>Route {index + 1}</h3>
                      <div className="route-stats">
                        <span className="route-stat">
                          <i className="fas fa-clock"></i> {route.duration}
                        </span>
                        <span className="route-stat">
                          <i className="fas fa-road"></i> {route.distance}
                        </span>
                        <span className="route-stat shade-percentage">
                          <i className="fas fa-umbrella-beach"></i> 
                          <span className="glow-text">{route.shade_percentage.toFixed(1)}%</span> in shade
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        </div>

        <div className="map-container" ref={cesiumContainer}></div>
      </div>

      <style jsx="true">{`
        .route-planner {
          display: flex;
          flex-direction: column;
          height: 100vh;
          background: linear-gradient(to right, lightblue, white);
          overflow: hidden;
        }

        .top-banner {
          background: white;
          box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
          padding: 15px 0;
          z-index: 10;
        }

        .banner-content {
          display: flex;
          align-items: center;
          justify-content: space-between;
          max-width: 90vw;
          margin: 0 auto;
          padding: 0 20px;
        }

        .main-content {
          display: flex;
          flex: 1;
          overflow: hidden;
        }

        .sidebar {
          width: 350px;
          min-width: 300px;
          max-width: 400px;
          padding: 15px;
          background: white;
          box-shadow: 2px 0 5px rgba(0, 0, 0, 0.1);
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          height: 100%;
          max-height: 100vh;
        }

        .header-section {
          margin-bottom: 20px;
          padding-bottom: 20px;
          border-bottom: 2px solid #f0f0f0;
        }

        .title-group {
          display: flex;
          align-items: center;
          padding: 15px 15px 15px 15px;
         background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border-radius: 10px;
          color: white;
        }

        .title-group h2 {
          margin: 0;
          margin-left: 0px;
          font-size:2.2em;
          font-weight: 1200;
          font-family: 'Montserrat', sans-serif;
          color: white;
        }

        .partners-section {
          display: flex;
          align-items: center;
          gap: 30px;
        }

        .partner-logo {
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .logo-placeholder {
          width: 200px;
          height: 100px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: transparent;
          border-radius: 0;
          font-size: 2em;
          flex-shrink: 0;
        }

        .map-container {
          flex: 1;
          position: relative;
          min-width: 0; /* Prevents flex item from overflowing */
        }

        .input-group {
          margin-bottom: 20px;
          position: relative;
        }

        label {
          display: block;
          margin-bottom: 8px;
          font-weight: 600;
          font-size: 0.95rem;
          color: #2c3e50;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        input {
          width: 100%;
          padding: 15px 20px;
          border: 2px solid #e1e8ed;
          border-radius: 12px;
          box-sizing: border-box;
          font-size: 1rem;
          background: #f8f9fa;
          transition: all 0.3s ease;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }

        input:focus {
          outline: none;
          border-color: #667eea;
          background: white;
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
          transform: translateY(-1px);
        }

        input::placeholder {
          color: #a0a0a0;
          font-style: italic;
        }

        button {
          width: 100%;
          padding: 16px 20px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          border: none;
          border-radius: 12px;
          cursor: pointer;
          transition: all 0.3s ease;
          margin-bottom: 20px;
          font-size: 1.1rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }

        button:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }

        button:active {
          transform: translateY(0);
        }

        button:disabled {
          background: linear-gradient(135deg, #bdc3c7 0%, #95a5a6 100%);
          cursor: not-allowed;
          transform: none;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .clear-button {
          background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%) !important;
          margin-top: 10px;
        }

        .clear-button:hover {
          background: linear-gradient(135deg, #c0392b 0%, #a93226 100%) !important;
        }

        .error {
          color: red;
          margin-top: 10px;
          font-size: 0.9rem;
        }

        .route-list {
          margin-top: 15px;
          padding-top: 15px;
          border-top: 1px solid #eee;
          overflow-y: auto;
          flex: 1;
          max-height: calc(100vh - 300px);
          min-height: 200px;
        }

        .route-item {
          display: flex;
          flex-direction: column;
          margin: 10px 0;
          padding: 8px;
          background: #f8f9fa;
          border-radius: 4px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .route-label {
          font-weight: 500;
          margin-bottom: 5px;
        }

        .route-utci {
          font-size: 0.8em;
          color: #6c757d;
          display: block;
          margin-top: 2px;
        }

        .route-details {
          font-size: 0.8em;
          color: #6c757d;
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 4px;
        }

        .route-distance, .route-duration {
          display: inline-block;
          padding: 2px 6px;
          background-color: #e9ecef;
          border-radius: 4px;
          white-space: nowrap;
        }

        .route-info {
          margin-top: 8px;
          padding: 8px;
          background: #f8f9fa;
          border-radius: 4px;
        }

        .route-header {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .route-header h3 {
          margin: 0;
          font-size: 1rem;
        }

        .route-stats {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .route-stat {
          display: flex;
          align-items: center;
          font-size: 0.85rem;
          white-space: nowrap;
        }

        .route-stat i {
          margin-right: 5px;
        }

        /* Animation for route items */
        .animate-slide-in {
          animation: slideInFromRight 0.6s ease-out forwards, newTileGlow 2s ease-out forwards;
          opacity: 0;
          transform: translateX(50px);
        }

        @keyframes slideInFromRight {
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }

        @keyframes newTileGlow {
          0% {
            box-shadow: 0 0 20px rgba(102, 126, 234, 0.8), 0 0 40px rgba(102, 126, 234, 0.6);
            background: linear-gradient(135deg, #f8f9fa 0%, #e3f2fd 100%);
            border: 2px solid rgba(102, 126, 234, 0.8);
          }
          50% {
            box-shadow: 0 0 30px rgba(102, 126, 234, 0.9), 0 0 60px rgba(102, 126, 234, 0.7);
            background: linear-gradient(135deg, #e3f2fd 0%, #f8f9fa 100%);
            border: 2px solid rgba(102, 126, 234, 1);
          }
          100% {
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            background: #f8f9fa;
            border: 1px solid transparent;
          }
        }

        /* Shade percentage styling */
        .shade-percentage .glow-text {
          color: #000000;
          font-size: 1.2em;
          font-weight: bold;
          background: rgba(255, 255, 255, 0.9);
          padding: 4px 8px;
          border-radius: 6px;
          border: 1px solid #ff6b35;
          animation: shadePulse 2s ease-in-out infinite;
          box-shadow: 0 0 8px rgba(255, 107, 53, 0.3);
        }

        @keyframes shadePulse {
          0% {
            box-shadow: 0 0 8px rgba(255, 107, 53, 0.3);
            transform: scale(1);
          }
          50% {
            box-shadow: 0 0 12px rgba(255, 107, 53, 0.5);
            transform: scale(1.02);
          }
          100% {
            box-shadow: 0 0 8px rgba(255, 107, 53, 0.3);
            transform: scale(1);
          }
        }

        /* Media queries for responsive design */
        @media (max-width: 768px) {
          .route-planner {
            flex-direction: column;
          }
          
          .sidebar {
            width: 100%;
            max-width: 100%;
            height: auto;
            max-height: 40vh;
          }
          
          .map-container {
            height: 60vh;
          }
        }
      `}</style>
    </div>
  );
};

export default RoutePlanner; 