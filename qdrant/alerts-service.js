/**
 * Alerts Service - Vector Database Operations
 * 
 * All alert-related operations with Qdrant
 */

const axios = require('axios');
const { qdrantClient, QDRANT_CONFIG } = require('./config');
const { detectConflictType, getSolution } = require('./solution-templates');

// AI Service URL from environment
const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:5001';

/**
 * Generate embedding for text using AI Service
 * @param {string} text - Text to embed
 * @returns {Promise<number[]>} - Vector embedding
 */
async function generateEmbedding(text) {
  try {
    const response = await axios.post(`${AI_SERVICE_URL}/embed`, { text });
    return response.data.vector;
  } catch (error) {
    console.warn(`AI Service unavailable, using placeholder vector: ${error.message}`);
    // Fallback to random vector if AI service is down
    return Array(QDRANT_CONFIG.VECTOR_DIMENSION).fill(0).map(() => Math.random() - 0.5);
  }
}

/**
 * Store a single alert in Qdrant
 * @param {Object} alert - Alert object
 * @returns {Promise<Object>} - Stored alert info
 */
async function storeAlert(alert) {
  const { conflict, conflictType, severity, solution, metadata = {}, source = 'manual' } = alert;

  if (!conflict) {
    throw new Error('Conflict description is required');
  }

  // Generate embedding
  const vector = await generateEmbedding(conflict);

  // Generate numeric ID
  const alertId = Date.now() * 1000 + Math.floor(Math.random() * 1000);
  const detectedType = conflictType || detectConflictType(conflict);
  const alertSeverity = severity || 'moderate';
  const alertSolution = solution || getSolution(detectedType, alertSeverity);

  // Store in Qdrant
  await qdrantClient.upsert(QDRANT_CONFIG.ALERTS_COLLECTION, {
    wait: true,
    points: [
      {
        id: alertId,
        vector: vector,
        payload: {
          conflict: conflict,
          conflictType: detectedType,
          severity: alertSeverity,
          solution: alertSolution,
          metadata: metadata,
          createdAt: new Date().toISOString(),
          source: source
        }
      }
    ]
  });

  return {
    id: alertId,
    conflict: conflict,
    conflictType: detectedType,
    severity: alertSeverity,
    solution: alertSolution
  };
}

/**
 * Store multiple alerts in batch
 * @param {Array} alerts - Array of alert objects
 * @returns {Promise<Object>} - Results summary
 */
async function storeBatch(alerts) {
  if (!Array.isArray(alerts) || alerts.length === 0) {
    throw new Error('Alerts array is required');
  }

  const storedAlerts = [];
  const errors = [];

  for (const alert of alerts) {
    try {
      const result = await storeAlert({ ...alert, source: 'batch_import' });
      storedAlerts.push(result);
    } catch (error) {
      console.error(`Error storing alert "${alert.conflict?.substring(0, 50) || 'unknown'}...": ${error.message}`);
      errors.push({ conflict: alert.conflict || 'unknown', error: error.message });
    }
  }

  return {
    success: true,
    stored: storedAlerts.length,
    failed: errors.length,
    storedAlerts,
    errors
  };
}

/**
 * Search for similar alerts
 * @param {string} conflictText - The conflict description to search for
 * @param {number} limit - Number of results to return
 * @returns {Promise<Object>} - Search results with suggested solution
 */
async function searchSimilar(conflictText, limit = 5) {
  if (!conflictText) {
    throw new Error('Conflict description is required');
  }

  // Generate embedding for search query
  const queryVector = await generateEmbedding(conflictText);

  // Search Qdrant
  const searchResults = await qdrantClient.search(QDRANT_CONFIG.ALERTS_COLLECTION, {
    vector: queryVector,
    limit: limit,
    with_payload: true
  });

  // Get suggested solution from best match
  let suggestedSolution = 'No similar incidents found. Contact station staff for assistance.';
  let confidence = 0;
  let usingAI = true;

  if (searchResults.length > 0) {
    const bestMatch = searchResults[0];
    suggestedSolution = bestMatch.payload.solution;
    confidence = bestMatch.score;
  } else {
    // Fallback to template if no matches
    const detectedType = detectConflictType(conflictText);
    suggestedSolution = getSolution(detectedType, 'moderate');
    usingAI = false;
  }

  return {
    query: conflictText,
    suggestedSolution: suggestedSolution,
    confidence: confidence,
    similarAlerts: searchResults.map(result => ({
      id: result.id,
      similarity: result.score,
      conflict: result.payload.conflict,
      conflictType: result.payload.conflictType,
      severity: result.payload.severity,
      solution: result.payload.solution,
      createdAt: result.payload.createdAt
    })),
    usingAI: usingAI,
    timestamp: new Date().toISOString()
  };
}

/**
 * Get all stored alerts (paginated)
 * @param {number} limit - Number of results per page
 * @param {number} offset - Offset for pagination
 * @returns {Promise<Object>} - Paginated alerts
 */
async function getAllAlerts(limit = 10, offset = 0) {
  const results = await qdrantClient.scroll(QDRANT_CONFIG.ALERTS_COLLECTION, {
    limit: limit,
    offset: offset,
    with_payload: true,
    with_vector: false
  });

  const alerts = results.points.map(point => ({
    id: point.id,
    ...point.payload
  }));

  // Get total count
  const collectionInfo = await qdrantClient.getCollection(QDRANT_CONFIG.ALERTS_COLLECTION);
  const totalCount = collectionInfo.points_count || 0;

  return {
    alerts: alerts,
    total: totalCount,
    limit: limit,
    offset: offset,
    timestamp: new Date().toISOString()
  };
}

/**
 * Update alert solution (manual annotation)
 * @param {number} alertId - Alert ID
 * @param {string} newSolution - Updated solution
 * @returns {Promise<Object>} - Update result
 */
async function updateSolution(alertId, newSolution) {
  if (!newSolution) {
    throw new Error('New solution is required');
  }

  // Get existing alert
  const existing = await qdrantClient.retrieve(QDRANT_CONFIG.ALERTS_COLLECTION, {
    ids: [alertId],
    with_payload: true,
    with_vector: true
  });

  if (!existing || existing.length === 0) {
    throw new Error('Alert not found');
  }

  const alert = existing[0];

  // Update with new solution
  await qdrantClient.upsert(QDRANT_CONFIG.ALERTS_COLLECTION, {
    wait: true,
    points: [
      {
        id: alertId,
        vector: alert.vector,
        payload: {
          ...alert.payload,
          solution: newSolution,
          updatedAt: new Date().toISOString()
        }
      }
    ]
  });

  return {
    success: true,
    alertId: alertId,
    message: 'Solution updated successfully'
  };
}

/**
 * Delete an alert
 * @param {number} alertId - Alert ID to delete
 * @returns {Promise<Object>} - Deletion result
 */
async function deleteAlert(alertId) {
  await qdrantClient.delete(QDRANT_CONFIG.ALERTS_COLLECTION, {
    wait: true,
    points: [alertId]
  });

  return {
    success: true,
    message: 'Alert deleted successfully'
  };
}

module.exports = {
  generateEmbedding,
  storeAlert,
  storeBatch,
  searchSimilar,
  getAllAlerts,
  updateSolution,
  deleteAlert,
};
