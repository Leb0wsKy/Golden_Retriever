const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const dotenv = require('dotenv');
const { QdrantClient } = require('@qdrant/js-client-rest');
const axios = require('axios');

// Note: Legacy Qdrant modules for deprecated alerts system (lines 197-699) are no longer imported
// Digital Twin service now handles all conflict/alert management via proxy endpoints

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Qdrant client for direct database access (if needed)
// Note: Most operations now go through Digital Twin proxy endpoints
const qdrantClient = new QdrantClient({
  url: process.env.QDRANT_URL,
  apiKey: process.env.QDRANT_API_KEY,
});

// System stats
let systemStats = {
  vectors: 0,
  collections: 0,
  aiModels: 3,
  uptime: '0h 0m',
  startTime: Date.now(),
};

// Note: ALERTS_COLLECTION and initialization removed - Digital Twin manages collections
// Legacy alerts system (lines 197-699) has been deprecated

// Health Check
app.get('/api/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

// Transitland API - Get Live Train Data from Multiple Countries
app.get('/api/trains/live', async (req, res) => {
  try {
    const apiKey = process.env.TRANSITLAND_API_KEY;
    
    if (!apiKey || apiKey === 'your_transitland_api_key_here') {
      return res.status(400).json({ error: 'Transitland API key not configured' });
    }

    // Fetch routes with rail transit from around the world
    const routesResponse = await axios.get(
      `${process.env.TRANSITLAND_BASE_URL}/rest/routes`,
      {
        headers: {
          'apikey': apiKey
        },
        params: {
          route_type: 2, // 2=rail (1=subway/metro, 2=rail, 0=tram)
          limit: 10000, // Get as many as possible
          include_geometry: true
        }
      }
    );

    console.log(`Fetched ${routesResponse.data.routes?.length || 0} routes from Transitland`);

    // Transform routes data and group by network/agency
    const networkMap = new Map(); // Map of agency -> {trains: [], routes: [], center: [lat, lng], country: string}
    let routeIndex = 0;

    if (routesResponse.data.routes) {
      for (const route of routesResponse.data.routes) {
        // Get route geometry if available
        if (route.geometry && route.geometry.coordinates) {
          let coordinates = route.geometry.coordinates;
          
          // Handle different geometry types (LineString vs MultiLineString)
          if (route.geometry.type === 'MultiLineString' && Array.isArray(coordinates[0][0])) {
            // For MultiLineString, take the first LineString
            coordinates = coordinates[0];
          }
          
          if (coordinates && coordinates.length > 0) {
            // Create route line - convert [lng, lat] to [lat, lng]
            const routePath = coordinates.map(coord => {
              if (Array.isArray(coord) && coord.length >= 2) {
                return [coord[1], coord[0]];
              }
              return null;
            }).filter(coord => coord !== null);
            
            if (routePath.length > 0) {
              const agencyName = route.agency?.agency_name || 'Unknown Network';
              const agencyId = route.agency?.agency_id || 'unknown';
              const country = route.agency?.agency_timezone?.split('/')[0] || 'Unknown';
              
              // Initialize network if not exists
              if (!networkMap.has(agencyId)) {
                networkMap.set(agencyId, {
                  id: agencyId,
                  name: agencyName,
                  country: country,
                  trains: [],
                  routes: [],
                  center: null,
                  trainCount: 0,
                  routeCount: 0
                });
              }
              
              const network = networkMap.get(agencyId);
              
              // Add route to network
              const routeData = {
                id: route.id,
                name: route.route_long_name || route.route_short_name || `Route ${routeIndex++}`,
                color: route.route_color ? `#${route.route_color}` : '#1976d2',
                path: [routePath],
                agency: agencyName,
                type: route.route_type
              };
              network.routes.push(routeData);
              network.routeCount++;

              // Place a train at a random point along each route
              if (routePath.length > 2) {
                const midIndex = Math.floor(routePath.length / 2);
                const position = routePath[midIndex];
                
                // Set network center if not set
                if (!network.center) {
                  network.center = position;
                }
                
                const trainData = {
                  id: `train-${route.id}`,
                  name: route.route_short_name || route.route_long_name || `Train ${network.trains.length + 1}`,
                  position: position,
                  speed: Math.floor(Math.random() * 50) + 30,
                  status: Math.random() > 0.2 ? 'on-time' : 'delayed',
                  delay: Math.random() > 0.8 ? Math.floor(Math.random() * 10) : 0,
                  nextStop: 'Next Station',
                  route: route.route_long_name || route.route_short_name || 'Unknown',
                  agency: agencyName,
                  country: country,
                  networkId: agencyId
                };
                network.trains.push(trainData);
                network.trainCount++;
              }
            }
          }
        }
      }
    }

    // Convert map to array and sort by train count
    const networks = Array.from(networkMap.values())
      .filter(network => network.trains.length > 0)
      .sort((a, b) => b.trainCount - a.trainCount);

    console.log(`Organized into ${networks.length} networks with total ${networks.reduce((sum, n) => sum + n.trainCount, 0)} trains`);

    res.json({
      networks: networks,
      totalNetworks: networks.length,
      totalTrains: networks.reduce((sum, n) => sum + n.trainCount, 0),
      totalRoutes: networks.reduce((sum, n) => sum + n.routeCount, 0),
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error fetching train data:', error.message);
    console.error('Error details:', error.response?.data || error.message);
    res.status(500).json({ 
      error: 'Failed to fetch train data',
      message: error.message,
      details: error.response?.data 
    });
  }
});

// ============================================
// DEPRECATED: ALERTS VECTOR DATABASE ENDPOINTS
// ============================================
// These endpoints are DEPRECATED and replaced by Digital Twin service
// The Digital Twin service now handles:
// - Conflict generation and management
// - Transitland integration
// - Vector embeddings via AI service
// - Feedback loop and learning
//
// Use these Digital Twin endpoints instead:
// - POST /api/digital-twin/conflicts/generate-from-schedules (replaces sync-from-transitland)
// - GET /api/digital-twin/conflicts (replaces /api/alerts)
// - GET /api/digital-twin/conflicts/transitland/stats (replaces stats)
// - POST /api/digital-twin/recommendations (replaces vector search)
// ============================================

/* DEPRECATED - Use Digital Twin service instead
app.post('/api/alerts/sync-from-transitland', async (req, res) => {
  try {
    const apiKey = process.env.TRANSITLAND_API_KEY;
    
    if (!apiKey || apiKey === 'your_transitland_api_key_here') {
      return res.status(400).json({ error: 'Transitland API key not configured' });
    }

    console.log('🔄 Syncing alerts from Transitland API...');

    // Fetch service alerts from Transitland
    const alertsResponse = await axios.get(
      `${process.env.TRANSITLAND_BASE_URL}/rest/alerts`,
      {
        headers: { 'apikey': apiKey },
        params: { limit: 100 }
      }
    );

    const alerts = alertsResponse.data.alerts || [];
    console.log(`📥 Fetched ${alerts.length} alerts from Transitland`);

    if (alerts.length === 0) {
      return res.json({
        message: 'No alerts available from Transitland API at this time',
        stored: 0,
        timestamp: new Date().toISOString()
      });
    }

    // Transform and store alerts
    const storedAlerts = [];
    const errors = [];
    let skipped = 0;

    for (const alert of alerts) {
      try {
        const conflict = alert.header_text?.translation?.[0]?.text || 
                         alert.description_text?.translation?.[0]?.text || 
                         null;
        
        // Skip alerts without text
        if (!conflict || conflict === 'Unknown alert') {
          skipped++;
          continue;
        }

        const conflictType = detectConflictType(conflict);
        
        // Determine severity from alert data
        let severity = 'moderate';
        if (alert.severity_level !== undefined) {
          if (alert.severity_level <= 1) severity = 'minor';
          else if (alert.severity_level >= 3) severity = 'severe';
        }

        // Generate embedding
        let vector;
        try {
          const embeddingResponse = await axios.post(
            `${process.env.AI_SERVICE_URL}/embed`,
            { text: conflict },
            { timeout: 5000 }
          );
          vector = embeddingResponse.data.vector;
        } catch (embeddingError) {
          console.log('⚠️ AI Service unavailable, using placeholder vector');
          vector = Array(VECTOR_DIMENSION).fill(0).map(() => Math.random() - 0.5);
        }

        const alertId = alert.id || `transitland-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const solution = getSolution(conflictType, severity);

        // Store in Qdrant
        await qdrantClient.upsert(ALERTS_COLLECTION, {
          wait: true,
          points: [
            {
              id: alertId,
              vector: vector,
              payload: {
                conflict: conflict,
                conflictType: conflictType,
                severity: severity,
                solution: solution,
                source: 'transitland',
                affectedRoutes: alert.informed_entity?.map(e => e.route_id).filter(Boolean) || [],
                affectedAgencies: alert.informed_entity?.map(e => e.agency_id).filter(Boolean) || [],
                activePeriod: alert.active_period || [],
                cause: alert.cause,
                effect: alert.effect,
                url: alert.url?.translation?.[0]?.text || null,
                createdAt: new Date().toISOString()
              }
            }
          ]
        });

        storedAlerts.push({
          id: alertId,
          conflict: conflict,
          severity: severity
        });

        console.log(`✅ Stored: ${conflict.substring(0, 60)}...`);

      } catch (alertError) {
        console.error(`❌ Error storing alert:`, alertError.message);
        errors.push({
          alert: alert.header_text?.translation?.[0]?.text || 'Unknown',
          error: alertError.message
        });
      }
    }

    console.log(`\n🎉 Sync complete! Stored: ${storedAlerts.length}, Skipped: ${skipped}, Errors: ${errors.length}\n`);

    res.json({
      success: true,
      stored: storedAlerts.length,
      skipped: skipped,
      failed: errors.length,
      storedAlerts: storedAlerts,
      errors: errors,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('❌ Error syncing alerts from Transitland:', error.message);
    res.status(500).json({ 
      error: 'Failed to sync alerts from Transitland', 
      message: error.message,
      details: error.response?.data 
    });
  }
});

// Fetch alerts from Transitland API (view only, doesn't store)
app.get('/api/alerts/fetch-from-transitland', async (req, res) => {
  try {
    const apiKey = process.env.TRANSITLAND_API_KEY;
    
    if (!apiKey || apiKey === 'your_transitland_api_key_here') {
      return res.status(400).json({ error: 'Transitland API key not configured' });
    }

    // Fetch service alerts from Transitland
    const alertsResponse = await axios.get(
      `${process.env.TRANSITLAND_BASE_URL}/rest/alerts`,
      {
        headers: { 'apikey': apiKey },
        params: { limit: 100 }
      }
    );

    const alerts = alertsResponse.data.alerts || [];
    console.log(`Fetched ${alerts.length} alerts from Transitland`);

    // Transform alerts to our format
    const transformedAlerts = alerts.map(alert => {
      const conflict = alert.header_text?.translation?.[0]?.text || 
                       alert.description_text?.translation?.[0]?.text || 
                       'Unknown alert';
      const conflictType = detectConflictType(conflict);
      
      // Determine severity from alert data or default to moderate
      let severity = 'moderate';
      if (alert.severity_level) {
        if (alert.severity_level <= 1) severity = 'minor';
        else if (alert.severity_level >= 3) severity = 'severe';
      }

      return {
        id: alert.id || `alert-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        conflict: conflict,
        conflictType: conflictType,
        severity: severity,
        solution: getSolution(conflictType, severity),
        source: 'transitland',
        affectedRoutes: alert.informed_entity?.map(e => e.route_id).filter(Boolean) || [],
        affectedAgencies: alert.informed_entity?.map(e => e.agency_id).filter(Boolean) || [],
        activePeriod: alert.active_period || [],
        createdAt: new Date().toISOString()
      };
    });

    res.json({
      alerts: transformedAlerts,
      count: transformedAlerts.length,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error fetching alerts from Transitland:', error.message);
    res.status(500).json({ error: 'Failed to fetch alerts', message: error.message });
  }
});

// Generate alerts from live train data anomalies
app.get('/api/alerts/detect-anomalies', async (req, res) => {
  try {
    const apiKey = process.env.TRANSITLAND_API_KEY;
    
    // Get live train data
    const routesResponse = await axios.get(
      `${process.env.TRANSITLAND_BASE_URL}/rest/routes`,
      {
        headers: { 'apikey': apiKey },
        params: { route_type: 2, limit: 100, include_geometry: true }
      }
    );

    const detectedAlerts = [];
    const routes = routesResponse.data.routes || [];

    // Simulate anomaly detection (in production, compare with historical data)
    for (const route of routes) {
      // Random chance of detecting an anomaly (for demo purposes)
      if (Math.random() < 0.1) { // 10% chance per route
        const anomalyTypes = ['delay', 'speed_restriction', 'congestion'];
        const severities = ['minor', 'moderate', 'severe'];
        
        const conflictType = anomalyTypes[Math.floor(Math.random() * anomalyTypes.length)];
        const severity = severities[Math.floor(Math.random() * severities.length)];
        
        const agencyName = route.agency?.agency_name || 'Unknown Agency';
        const routeName = route.route_long_name || route.route_short_name || 'Unknown Route';
        
        const conflictMessages = {
          'delay': `Train delay detected on ${routeName} (${agencyName}). Service running behind schedule.`,
          'speed_restriction': `Speed restriction in effect on ${routeName} (${agencyName}).`,
          'congestion': `High passenger volumes reported on ${routeName} (${agencyName}).`
        };

        detectedAlerts.push({
          id: Date.now() * 1000 + Math.floor(Math.random() * 1000),
          conflict: conflictMessages[conflictType],
          conflictType: conflictType,
          severity: severity,
          solution: getSolution(conflictType, severity),
          source: 'anomaly_detection',
          affectedRoutes: [route.id],
          affectedAgencies: [route.agency?.agency_id],
          routeName: routeName,
          agencyName: agencyName,
          createdAt: new Date().toISOString()
        });
      }
    }

    res.json({
      alerts: detectedAlerts,
      count: detectedAlerts.length,
      analyzedRoutes: routes.length,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error detecting anomalies:', error.message);
    res.status(500).json({ error: 'Failed to detect anomalies', message: error.message });
  }
});

// Store alert in Qdrant vector database
app.post('/api/alerts/store', async (req, res) => {
  try {
    const { conflict, severity, solution, conflictType, metadata } = req.body;

    if (!conflict) {
      return res.status(400).json({ error: 'Conflict description is required' });
    }

    const result = await alertsService.storeAlert({
      conflict,
      severity,
      solution,
      conflictType,
      metadata,
      source: 'manual'
    });

    res.json({
      success: true,
      alertId: result.id,
      message: 'Alert stored in vector database',
      data: result
    });

  } catch (error) {
    console.error('Error storing alert:', error.message);
    res.status(500).json({ error: 'Failed to store alert', message: error.message });
  }
});

// Batch store multiple alerts
app.post('/api/alerts/store-batch', async (req, res) => {
  try {
    const { alerts } = req.body;

    if (!alerts || !Array.isArray(alerts) || alerts.length === 0) {
      return res.status(400).json({ error: 'Alerts array is required' });
    }

    const result = await alertsService.storeBatch(alerts);
    res.json(result);

  } catch (error) {
    console.error('Error batch storing alerts:', error.message);
    res.status(500).json({ error: 'Failed to batch store alerts', message: error.message });
  }
});

// Search for similar alerts (find golden run for new conflict)
app.post('/api/alerts/search-similar', async (req, res) => {
  try {
    const { conflict, limit = 5 } = req.body;

    if (!conflict) {
      return res.status(400).json({ error: 'Conflict description is required' });
    }

    const result = await alertsService.searchSimilar(conflict, limit);
    res.json(result);

  } catch (error) {
    console.error('Error searching similar alerts:', error.message);
    res.status(500).json({ error: 'Failed to search similar alerts', message: error.message });
  }
});

// Get all stored alerts from Qdrant
app.get('/api/alerts/stored', async (req, res) => {
  try {
    const { limit = 100, offset = 0 } = req.query;
    const result = await alertsService.getAllAlerts(parseInt(limit), parseInt(offset));
    res.json(result);
  } catch (error) {
    console.error('Error fetching stored alerts:', error.message);
    res.status(500).json({ error: 'Failed to fetch stored alerts', message: error.message });
  }
});

// Update alert solution (annotate golden run)
app.put('/api/alerts/:alertId/solution', async (req, res) => {
  try {
    const { alertId } = req.params;
    const { solution } = req.body;

    if (!solution) {
      return res.status(400).json({ error: 'Solution is required' });
    }

    const alertIdNumeric = parseInt(alertId);
    const result = await alertsService.updateSolution(alertIdNumeric, solution);
    
    res.json({
      ...result,
      message: 'Alert solution updated (golden run annotated)',
      newSolution: solution
    });

  } catch (error) {
    console.error('Error updating alert solution:', error.message);
    res.status(500).json({ error: 'Failed to update alert solution', message: error.message });
  }
});

// Delete alert from Qdrant
app.delete('/api/alerts/:alertId', async (req, res) => {
  try {
    const { alertId } = req.params;
    const alertIdNumeric = parseInt(alertId);
    
    const result = await alertsService.deleteAlert(alertIdNumeric);
    res.json({
      ...result,
      message: 'Alert deleted from vector database',
      alertId: alertId
    });

  } catch (error) {
    console.error('Error deleting alert:', error.message);
    res.status(500).json({ error: 'Failed to delete alert', message: error.message });
  }
});

// Get alert collection stats
app.get('/api/alerts/stats', async (req, res) => {
  try {
    const stats = await getCollectionStats();
    res.json(stats);
  } catch (error) {
    console.error('Error fetching alert stats:', error.message);
    res.status(500).json({ error: 'Failed to fetch alert stats', message: error.message });
  }
});

// Cache for train data and alerts
let alertsCache = {
  alerts: [],
  timestamp: 0,
  trainsAnalyzed: 0,
  stats: null
};
const ALERTS_CACHE_TTL = 30000; // 30 seconds cache

// Get live alerts from current train data
app.get('/api/alerts/live', async (req, res) => {
  try {
    // Check cache first
    const cacheAge = Date.now() - alertsCache.timestamp;
    if (cacheAge < ALERTS_CACHE_TTL && alertsCache.alerts.length > 0) {
      console.log('Serving alerts from cache (age: ' + Math.floor(cacheAge / 1000) + 's)');
      const { severity = 'minor', maxAge = 3600000, limit = 50 } = req.query;
      const filteredAlerts = alertsGenerator.filterAlerts(alertsCache.alerts, {
        minSeverity: severity,
        maxAge: parseInt(maxAge),
        limit: parseInt(limit)
      });
      
      return res.json({
        alerts: filteredAlerts,
        stats: alertsCache.stats,
        trainsAnalyzed: alertsCache.trainsAnalyzed,
        timestamp: new Date(alertsCache.timestamp).toISOString(),
        cached: true,
        cacheAge: Math.floor(cacheAge / 1000)
      });
    }
    
    console.log('Generating fresh alerts...');
    // Fetch current train data
    const trainsResponse = await axios.get('http://localhost:5000/api/trains/live');
    const networks = trainsResponse.data.networks || [];
    
    // Extract all trains from all networks
    const allTrains = networks.flatMap(network => network.trains);
    const allRoutes = networks.flatMap(network => network.routes);
    
    // Generate alerts from train data
    const generatedAlerts = await alertsGenerator.generateAlertsFromTrains(allTrains, allRoutes);
    
    // Filter alerts based on query parameters
    const { severity = 'minor', maxAge = 3600000, limit = 50 } = req.query;
    const filteredAlerts = alertsGenerator.filterAlerts(generatedAlerts, {
      minSeverity: severity,
      maxAge: parseInt(maxAge),
      limit: parseInt(limit)
    });
    
    // Calculate statistics
    const stats = {
      total: generatedAlerts.length,
      displayed: filteredAlerts.length,
      bySeverity: {
        severe: generatedAlerts.filter(a => a.severity === 'severe').length,
        moderate: generatedAlerts.filter(a => a.severity === 'moderate').length,
        minor: generatedAlerts.filter(a => a.severity === 'minor').length,
      },
      withAI: generatedAlerts.filter(a => a.usingAI).length,
      avgConfidence: generatedAlerts.reduce((sum, a) => sum + a.confidence, 0) / (generatedAlerts.length || 1),
    };
    
    // Update cache
    alertsCache = {
      alerts: generatedAlerts,
      timestamp: Date.now(),
      trainsAnalyzed: allTrains.length,
      stats: stats
    };
    console.log(`Generated ${generatedAlerts.length} alerts (severe: ${stats.bySeverity.severe}, moderate: ${stats.bySeverity.moderate}, minor: ${stats.bySeverity.minor})`);
    
    res.json({
      alerts: filteredAlerts,
      stats: stats,
      trainsAnalyzed: allTrains.length,
      timestamp: new Date().toISOString(),
      cached: false
    });
    
  } catch (error) {
    console.error('Error generating live alerts:', error.message);
    res.status(500).json({ error: 'Failed to generate live alerts', message: error.message });
  }
});
*/  // End of DEPRECATED alerts endpoints

// Get Stats (kept for system health monitoring)
app.get('/api/stats', async (req, res) => {
  try {
    const collections = await qdrantClient.getCollections();
    const uptime = Math.floor((Date.now() - systemStats.startTime) / 1000);
    const hours = Math.floor(uptime / 3600);
    const minutes = Math.floor((uptime % 3600) / 60);

    let totalVectors = 0;
    for (const collection of collections.collections) {
      const info = await qdrantClient.getCollection(collection.name);
      totalVectors += info.points_count || 0;
    }

    res.json({
      vectors: totalVectors,
      collections: collections.collections.length,
      aiModels: systemStats.aiModels,
      uptime: `${hours}h ${minutes}m`,
    });
  } catch (error) {
    console.error('Error fetching stats:', error);
    res.json({
      vectors: 0,
      collections: 0,
      aiModels: 3,
      uptime: '0h 0m',
    });
  }
});

// Train real-time data endpoint
app.get('/api/trains/realtime', async (req, res) => {
  try {
    const transitlandApiKey = req.headers['x-transitland-api-key'] || process.env.TRANSITLAND_API_KEY;
    
    // Mock data for now - replace with actual Transitland API call
    const trains = [
      { id: 1, name: 'Train A1', lat: 40.7128, lng: -74.0060, speed: 65, status: 'on-time', route: 'Route 1' },
      { id: 2, name: 'Train B2', lat: 40.7589, lng: -73.9851, speed: 58, status: 'delayed', route: 'Route 2' },
      { id: 3, name: 'Train C3', lat: 40.7489, lng: -73.9680, speed: 72, status: 'on-time', route: 'Route 1' },
      { id: 4, name: 'Train D4', lat: 40.7614, lng: -73.9776, speed: 45, status: 'on-time', route: 'Route 3' },
    ];
    
    const routes = [
      { id: 1, name: 'Route 1', coordinates: [[40.7128, -74.0060], [40.7589, -73.9851], [40.7489, -73.9680]] },
      { id: 2, name: 'Route 2', coordinates: [[40.7589, -73.9851], [40.7614, -73.9776]] },
      { id: 3, name: 'Route 3', coordinates: [[40.7614, -73.9776], [40.7489, -73.9680]] },
    ];
    
    res.json({ trains, routes });
  } catch (error) {
    console.error('Error fetching train data:', error);
    res.status(500).json({ error: 'Failed to fetch train data' });
  }
});

// Get Performance Data
app.get('/api/performance', (req, res) => {
  const data = [];
  for (let i = 0; i < 10; i++) {
    data.push({
      time: `T-${10 - i}`,
      queries: Math.floor(Math.random() * 100 + 50),
      latency: Math.floor(Math.random() * 50 + 10),
    });
  }
  res.json(data);
});

// Get Activity Data
app.get('/api/activity', async (req, res) => {
  try {
    const collections = await qdrantClient.getCollections();
    const data = await Promise.all(
      collections.collections.slice(0, 5).map(async (col) => {
        const info = await qdrantClient.getCollection(col.name);
        return {
          collection: col.name,
          inserts: Math.floor(Math.random() * 100),
          searches: Math.floor(Math.random() * 200),
        };
      })
    );
    res.json(data);
  } catch (error) {
    console.error('Error fetching activity:', error);
    res.json([]);
  }
});

// Get Collections
app.get('/api/collections', async (req, res) => {
  try {
    const collections = await qdrantClient.getCollections();
    const detailedCollections = await Promise.all(
      collections.collections.map(async (col) => {
        try {
          const info = await qdrantClient.getCollection(col.name);
          return {
            name: col.name,
            vectors_count: info.points_count || 0,
            dimension: info.config?.params?.vectors?.size || 384,
            distance: info.config?.params?.vectors?.distance || 'Cosine',
            status: 'active',
          };
        } catch (error) {
          return {
            name: col.name,
            vectors_count: 0,
            dimension: 384,
            distance: 'Cosine',
            status: 'inactive',
          };
        }
      })
    );
    res.json(detailedCollections);
  } catch (error) {
    console.error('Error fetching collections:', error);
    res.status(500).json({ error: 'Failed to fetch collections' });
  }
});

// Create Collection
app.post('/api/collections', async (req, res) => {
  try {
    const { name, dimension, distance } = req.body;
    await qdrantClient.createCollection(name, {
      vectors: {
        size: dimension || 384,
        distance: distance || 'Cosine',
      },
    });
    res.json({ success: true, message: 'Collection created successfully' });
  } catch (error) {
    console.error('Error creating collection:', error);
    res.status(500).json({ error: 'Failed to create collection' });
  }
});

// Search Vectors
app.post('/api/search', async (req, res) => {
  try {
    const { query, limit = 10, collection } = req.body;
    
    // Get embedding from AI service
    const embeddingResponse = await axios.post(
      `${process.env.AI_SERVICE_URL}/embed`,
      { text: query }
    );
    
    const queryVector = embeddingResponse.data.vector;
    const collectionName = collection || process.env.DEFAULT_COLLECTION;

    const searchResult = await qdrantClient.search(collectionName, {
      vector: queryVector,
      limit: limit,
      with_payload: true,
    });

    res.json(
      searchResult.map((result) => ({
        id: result.id,
        score: result.score,
        text: result.payload?.text || 'No text available',
        metadata: result.payload,
      }))
    );
  } catch (error) {
    console.error('Error searching vectors:', error);
    res.status(500).json({ error: 'Failed to search vectors' });
  }
});

// AI Models Routes (proxy to Flask service)
app.get('/api/ai/models', async (req, res) => {
  try {
    const response = await axios.get(`${process.env.AI_SERVICE_URL}/models`);
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching AI models:', error);
    res.json([
      {
        id: 'bert-base',
        name: 'BERT Base',
        description: 'Text embedding model',
        status: 'active',
      },
      {
        id: 'sentence-transformer',
        name: 'Sentence Transformer',
        description: 'Sentence embedding model',
        status: 'active',
      },
    ]);
  }
});

app.post('/api/ai/embed', async (req, res) => {
  try {
    const response = await axios.post(`${process.env.AI_SERVICE_URL}/embed`, req.body);
    res.json(response.data);
  } catch (error) {
    console.error('Error generating embedding:', error);
    res.status(500).json({ error: 'Failed to generate embedding' });
  }
});

app.post('/api/ai/predict', async (req, res) => {
  try {
    const response = await axios.post(`${process.env.AI_SERVICE_URL}/predict`, req.body);
    res.json(response.data);
  } catch (error) {
    console.error('Error running prediction:', error);
    res.status(500).json({ error: 'Failed to run prediction' });
  }
});

// ============================================
// DIGITAL TWIN ROUTES (FastAPI Proxy)
// ============================================

// Health check for digital twin service
app.get('/api/digital-twin/health', async (req, res) => {
  try {
    const response = await axios.get(`${process.env.DIGITAL_TWIN_URL}/health`, { timeout: 5000 });
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching digital twin health:', error.message);
    res.status(503).json({ 
      error: 'Digital twin service unavailable',
      service: 'digital-twin',
      url: process.env.DIGITAL_TWIN_URL
    });
  }
});

// ============================================
// CONFLICT MANAGEMENT ENDPOINTS
// ============================================

// List all conflicts
app.get('/api/digital-twin/conflicts', async (req, res) => {
  try {
    const { limit = 50, offset = 0 } = req.query;
    const response = await axios.get(
      `${process.env.DIGITAL_TWIN_URL}/api/v1/conflicts/`,
      { params: { limit, offset } }
    );
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching conflicts:', error.message);
    res.status(error.response?.status || 500).json({ 
      error: 'Failed to fetch conflicts',
      message: error.response?.data?.detail || error.message 
    });
  }
});

// Get specific conflict by ID
app.get('/api/digital-twin/conflicts/:conflictId', async (req, res) => {
  try {
    const response = await axios.get(
      `${process.env.DIGITAL_TWIN_URL}/api/v1/conflicts/${req.params.conflictId}`
    );
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching conflict:', error.message);
    res.status(error.response?.status || 500).json({ 
      error: 'Failed to fetch conflict',
      message: error.response?.data?.detail || error.message 
    });
  }
});

// Generate synthetic conflicts
app.post('/api/digital-twin/conflicts/generate', async (req, res) => {
  try {
    const response = await axios.post(
      `${process.env.DIGITAL_TWIN_URL}/api/v1/conflicts/generate`,
      req.body,
      { timeout: 30000 }
    );
    res.json(response.data);
  } catch (error) {
    console.error('Error generating conflicts:', error.message);
    res.status(error.response?.status || 500).json({ 
      error: 'Failed to generate conflicts',
      message: error.response?.data?.detail || error.message 
    });
  }
});

// Generate conflicts from Transitland schedules
app.post('/api/digital-twin/conflicts/generate-from-schedules', async (req, res) => {
  try {
    const response = await axios.post(
      `${process.env.DIGITAL_TWIN_URL}/api/v1/conflicts/generate-from-schedules`,
      req.body,
      { timeout: 60000 }
    );
    res.json(response.data);
  } catch (error) {
    console.error('Error generating conflicts from schedules:', error.message);
    res.status(error.response?.status || 500).json({ 
      error: 'Failed to generate conflicts from schedules',
      message: error.response?.data?.detail || error.message 
    });
  }
});

// Get Transitland integration statistics
app.get('/api/digital-twin/conflicts/transitland/stats', async (req, res) => {
  try {
    const response = await axios.get(
      `${process.env.DIGITAL_TWIN_URL}/api/v1/conflicts/transitland/stats`
    );
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching Transitland stats:', error.message);
    res.status(error.response?.status || 500).json({ 
      error: 'Failed to fetch Transitland stats',
      message: error.response?.data?.detail || error.message 
    });
  }
});

// Analyze specific conflict
app.post('/api/digital-twin/conflicts/analyze', async (req, res) => {
  try {
    const response = await axios.post(
      `${process.env.DIGITAL_TWIN_URL}/api/v1/conflicts/analyze`,
      req.body
    );
    res.json(response.data);
  } catch (error) {
    console.error('Error analyzing conflict:', error.message);
    res.status(error.response?.status || 500).json({ 
      error: 'Failed to analyze conflict',
      message: error.response?.data?.detail || error.message 
    });
  }
});

// Get recommendations for a conflict
app.get('/api/digital-twin/conflicts/:conflictId/recommendations', async (req, res) => {
  try {
    const { top_k = 5 } = req.query;
    const response = await axios.get(
      `${process.env.DIGITAL_TWIN_URL}/api/v1/conflicts/${req.params.conflictId}/recommendations`,
      { params: { top_k } }
    );
    res.json(response.data);
  } catch (error) {
    console.error('Error getting conflict recommendations:', error.message);
    res.status(error.response?.status || 500).json({ 
      error: 'Failed to get recommendations',
      message: error.response?.data?.detail || error.message 
    });
  }
});

// ============================================
// RECOMMENDATION ENDPOINTS
// ============================================

// Quick recommendation (POST with conflict data)
app.post('/api/digital-twin/recommendations', async (req, res) => {
  try {
    const response = await axios.post(
      `${process.env.DIGITAL_TWIN_URL}/api/v1/recommendations/`,
      req.body
    );
    res.json(response.data);
  } catch (error) {
    console.error('Error getting recommendations:', error.message);
    res.status(error.response?.status || 500).json({ 
      error: 'Failed to get recommendations',
      message: error.response?.data?.detail || error.message 
    });
  }
});

// Submit feedback for a recommendation
app.post('/api/digital-twin/recommendations/feedback', async (req, res) => {
  try {
    const response = await axios.post(
      `${process.env.DIGITAL_TWIN_URL}/api/v1/recommendations/feedback`,
      req.body
    );
    res.json(response.data);
  } catch (error) {
    console.error('Error submitting feedback:', error.message);
    res.status(error.response?.status || 500).json({ 
      error: 'Failed to submit feedback',
      message: error.response?.data?.detail || error.message 
    });
  }
});

// Get all feedback records
app.get('/api/digital-twin/recommendations/feedback', async (req, res) => {
  try {
    const { limit = 50, offset = 0 } = req.query;
    const response = await axios.get(
      `${process.env.DIGITAL_TWIN_URL}/api/v1/recommendations/feedback`,
      { params: { limit, offset } }
    );
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching feedback records:', error.message);
    res.status(error.response?.status || 500).json({ 
      error: 'Failed to fetch feedback records',
      message: error.response?.data?.detail || error.message 
    });
  }
});

// Get specific feedback by ID
app.get('/api/digital-twin/recommendations/feedback/:feedbackId', async (req, res) => {
  try {
    const response = await axios.get(
      `${process.env.DIGITAL_TWIN_URL}/api/v1/recommendations/feedback/${req.params.feedbackId}`
    );
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching feedback:', error.message);
    res.status(error.response?.status || 500).json({ 
      error: 'Failed to fetch feedback',
      message: error.response?.data?.detail || error.message 
    });
  }
});

// ============================================
// LEARNING & METRICS ENDPOINTS
// ============================================

// Get learning metrics (FIXED: was /metrics/learning, now /metrics)
app.get('/api/digital-twin/recommendations/metrics', async (req, res) => {
  try {
    const response = await axios.get(
      `${process.env.DIGITAL_TWIN_URL}/api/v1/recommendations/metrics`
    );
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching learning metrics:', error.message);
    res.status(error.response?.status || 500).json({ 
      error: 'Failed to fetch learning metrics',
      message: error.response?.data?.detail || error.message 
    });
  }
});

// Get metrics for specific strategy
app.get('/api/digital-twin/recommendations/metrics/strategy/:strategy', async (req, res) => {
  try {
    const response = await axios.get(
      `${process.env.DIGITAL_TWIN_URL}/api/v1/recommendations/metrics/strategy/${req.params.strategy}`
    );
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching strategy metrics:', error.message);
    res.status(error.response?.status || 500).json({ 
      error: 'Failed to fetch strategy metrics',
      message: error.response?.data?.detail || error.message 
    });
  }
});

// ============================================
// GOLDEN RUN ENDPOINTS
// ============================================

// List golden runs (verified successful resolutions)
app.get('/api/digital-twin/recommendations/golden-runs', async (req, res) => {
  try {
    const { limit = 50, offset = 0, strategy } = req.query;
    const response = await axios.get(
      `${process.env.DIGITAL_TWIN_URL}/api/v1/recommendations/golden-runs`,
      { params: { limit, offset, strategy } }
    );
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching golden runs:', error.message);
    res.status(error.response?.status || 500).json({ 
      error: 'Failed to fetch golden runs',
      message: error.response?.data?.detail || error.message 
    });
  }
});

// Get specific golden run by ID
app.get('/api/digital-twin/recommendations/golden-runs/:goldenRunId', async (req, res) => {
  try {
    const response = await axios.get(
      `${process.env.DIGITAL_TWIN_URL}/api/v1/recommendations/golden-runs/${req.params.goldenRunId}`
    );
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching golden run:', error.message);
    res.status(error.response?.status || 500).json({ 
      error: 'Failed to fetch golden run',
      message: error.response?.data?.detail || error.message 
    });
  }
});

// ============================================
// DEPRECATED ENDPOINTS (Kept for compatibility)
// ============================================

// Legacy: Simulation start/stop/reset are deprecated
// The Digital Twin now uses event-driven architecture

/* DEPRECATED - Simulation is now event-driven
app.post('/api/digital-twin/start', async (req, res) => {
  res.json({ 
    success: true, 
    message: 'Simulation is now event-driven. Generate conflicts to trigger simulation.',
    endpoint: '/api/digital-twin/conflicts/generate'
  });
});

app.post('/api/digital-twin/stop', async (req, res) => {
  res.json({ 
    success: true, 
    message: 'Simulation runs per-request. No continuous process to stop.'
  });
});

app.post('/api/digital-twin/reset', async (req, res) => {
  res.json({ 
    success: true, 
    message: 'No persistent state to reset. Each request is independent.'
  });
});
*/

// Legacy data endpoint - redirects to metrics
app.get('/api/digital-twin/data', async (req, res) => {
  res.json({
    timestamp: new Date().toISOString(),
    status: 'active',
    message: 'Use /api/digital-twin/recommendations/metrics for learning metrics'
  });
});

// Settings Routes
app.get('/api/settings', (req, res) => {
  res.json({
    qdrant_url: process.env.QDRANT_URL,
    qdrant_api_key: '***hidden***',
    collection_name: process.env.DEFAULT_COLLECTION,
    vector_dimension: parseInt(process.env.DEFAULT_VECTOR_DIMENSION),
    max_connections: 10,
    timeout: 30,
  });
});

app.post('/api/settings', (req, res) => {
  // In a real application, you would update environment variables or a config file
  res.json({ success: true, message: 'Settings saved successfully' });
});

// Start Server
app.listen(PORT, () => {
  console.log(`Backend server running on port ${PORT}`);
  console.log(`Qdrant URL: ${process.env.QDRANT_URL}`);
  console.log(`AI Service URL: ${process.env.AI_SERVICE_URL}`);
  console.log(`Digital Twin URL: ${process.env.DIGITAL_TWIN_URL}`);
});
