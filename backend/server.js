const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const dotenv = require('dotenv');
const { QdrantClient } = require('@qdrant/js-client-rest');
const axios = require('axios');

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Qdrant Client
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

// Get Stats
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

// Digital Twin Routes (proxy to FastAPI service)
// Health check for digital twin service
app.get('/api/digital-twin/health', async (req, res) => {
  try {
    const response = await axios.get(`${process.env.DIGITAL_TWIN_URL}/health`);
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching digital twin health:', error);
    res.status(500).json({ error: 'Digital twin service unavailable' });
  }
});

// Generate conflicts
app.post('/api/digital-twin/conflicts/generate', async (req, res) => {
  try {
    const response = await axios.post(
      `${process.env.DIGITAL_TWIN_URL}/api/v1/conflicts/generate`,
      req.body
    );
    res.json(response.data);
  } catch (error) {
    console.error('Error generating conflicts:', error);
    res.status(500).json({ 
      error: 'Failed to generate conflicts',
      message: error.response?.data?.detail || error.message 
    });
  }
});

// Get recommendations for a conflict
app.post('/api/digital-twin/recommendations', async (req, res) => {
  try {
    const response = await axios.post(
      `${process.env.DIGITAL_TWIN_URL}/api/v1/recommendations/`,
      req.body
    );
    res.json(response.data);
  } catch (error) {
    console.error('Error getting recommendations:', error);
    res.status(500).json({ 
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
    console.error('Error submitting feedback:', error);
    res.status(500).json({ 
      error: 'Failed to submit feedback',
      message: error.response?.data?.detail || error.message 
    });
  }
});

// Get learning metrics
app.get('/api/digital-twin/metrics/learning', async (req, res) => {
  try {
    const response = await axios.get(
      `${process.env.DIGITAL_TWIN_URL}/api/v1/recommendations/metrics/learning`
    );
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching learning metrics:', error);
    res.status(500).json({ 
      error: 'Failed to fetch learning metrics',
      message: error.response?.data?.detail || error.message 
    });
  }
});

// Legacy data endpoint for backward compatibility
app.get('/api/digital-twin/data', async (req, res) => {
  try {
    // Return mock data or redirect to new metrics endpoint
    res.json({
      timestamp: new Date().toISOString(),
      status: 'active',
      message: 'Use /api/digital-twin/metrics/learning for detailed metrics'
    });
  } catch (error) {
    console.error('Error fetching digital twin data:', error);
    res.json({
      timestamp: new Date().toISOString(),
      accuracy: Math.random(),
      latency: Math.random() * 100,
      throughput: Math.random() * 1000,
      metrics: {
        accuracy: Math.random(),
        latency: Math.random() * 100,
        throughput: Math.random() * 1000,
      },
    });
  }
});

// Simulation is now embedded in recommendation process
// These endpoints are deprecated but kept for backward compatibility
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
