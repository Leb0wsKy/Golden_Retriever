/**
 * Qdrant Configuration
 * 
 * Centralized configuration for Qdrant Cloud connection
 */

const { QdrantClient } = require('@qdrant/js-client-rest');
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '../backend/.env') });

// Qdrant Client Instance
const qdrantClient = new QdrantClient({
  url: process.env.QDRANT_URL,
  apiKey: process.env.QDRANT_API_KEY,
});

// Configuration Constants
const QDRANT_CONFIG = {
  ALERTS_COLLECTION: 'train_alerts',
  VECTOR_DIMENSION: 384,
  DISTANCE_METRIC: 'Cosine',
  DEFAULT_SEARCH_LIMIT: 5,
  BATCH_SIZE: 100,
};

module.exports = {
  qdrantClient,
  QDRANT_CONFIG,
};
