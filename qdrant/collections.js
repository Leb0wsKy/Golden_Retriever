/**
 * Qdrant Collection Management
 * 
 * Initialize and manage Qdrant collections
 */

const { qdrantClient, QDRANT_CONFIG } = require('./config');

/**
 * Initialize the alerts collection
 * @returns {Promise<void>}
 */
async function initializeAlertsCollection() {
  try {
    const collections = await qdrantClient.getCollections();
    const exists = collections.collections.some(c => c.name === QDRANT_CONFIG.ALERTS_COLLECTION);
    
    if (exists) {
      console.log(`✅ '${QDRANT_CONFIG.ALERTS_COLLECTION}' collection already exists`);
      return;
    }
    
    // Create collection with vector configuration
    await qdrantClient.createCollection(QDRANT_CONFIG.ALERTS_COLLECTION, {
      vectors: {
        size: QDRANT_CONFIG.VECTOR_DIMENSION,
        distance: QDRANT_CONFIG.DISTANCE_METRIC
      }
    });
    console.log(`✅ Created '${QDRANT_CONFIG.ALERTS_COLLECTION}' collection in Qdrant`);
  } catch (error) {
    console.error('❌ Error initializing alerts collection:', error.message);
    throw error;
  }
}

/**
 * Get collection statistics
 * @returns {Promise<Object>}
 */
async function getCollectionStats() {
  try {
    const info = await qdrantClient.getCollection(QDRANT_CONFIG.ALERTS_COLLECTION);
    return {
      collection: QDRANT_CONFIG.ALERTS_COLLECTION,
      totalAlerts: info.points_count || 0,
      vectorDimension: QDRANT_CONFIG.VECTOR_DIMENSION,
      status: info.status || 'unknown',
      timestamp: new Date().toISOString()
    };
  } catch (error) {
    console.error('Error getting collection stats:', error.message);
    throw error;
  }
}

/**
 * Delete a collection (use with caution!)
 * @param {string} collectionName - Name of the collection to delete
 * @returns {Promise<void>}
 */
async function deleteCollection(collectionName) {
  try {
    await qdrantClient.deleteCollection(collectionName);
    console.log(`🗑️ Deleted collection: ${collectionName}`);
  } catch (error) {
    console.error(`Error deleting collection ${collectionName}:`, error.message);
    throw error;
  }
}

module.exports = {
  initializeAlertsCollection,
  getCollectionStats,
  deleteCollection,
};
