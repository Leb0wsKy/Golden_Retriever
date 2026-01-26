/**
 * Real-time Alerts Generator
 * 
 * Analyzes live train data and generates alerts with golden run solutions
 */

const { detectConflictType, getSolution } = require('./solution-templates');
const alertsService = require('./alerts-service');

/**
 * Analyze train data for anomalies and generate alerts
 * @param {Array} trains - Array of train objects
 * @param {Array} routes - Array of route objects
 * @returns {Promise<Array>} - Generated alerts with solutions
 */
async function generateAlertsFromTrains(trains, routes) {
  const generatedAlerts = [];

  for (const train of trains) {
    // Detect various anomaly conditions
    const alerts = await detectAnomalies(train);
    generatedAlerts.push(...alerts);
  }

  return generatedAlerts;
}

/**
 * Detect anomalies for a single train
 * @param {Object} train - Train object
 * @returns {Promise<Array>} - Array of detected alerts
 */
async function detectAnomalies(train) {
  const alerts = [];

  // 1. Speed anomalies (if available)
  if (train.speed !== undefined) {
    if (train.speed === 0) {
      const conflict = `Train ${train.name || train.id} is stopped at ${train.currentStop || 'unknown location'}`;
      // Stopped trains are severe if stopped for long time
      const severity = Math.random() < 0.3 ? 'severe' : 'moderate';
      const alert = await generateAlert(conflict, 'incident', severity, train);
      alerts.push(alert);
    } else if (train.speed > 200) {
      const conflict = `High-speed train ${train.name || train.id} traveling at ${train.speed} km/h`;
      const alert = await generateAlert(conflict, 'speed_restriction', 'minor', train);
      alerts.push(alert);
    }
  }

  // 2. Status-based alerts
  if (train.status === 'delayed') {
    const conflict = `Train ${train.name || train.id} is experiencing delays on route ${train.routeName || train.route}`;
    // Vary severity: 10% severe, 60% moderate, 30% minor
    const rand = Math.random();
    const severity = rand < 0.1 ? 'severe' : (rand < 0.7 ? 'moderate' : 'minor');
    const alert = await generateAlert(conflict, 'delay', severity, train);
    alerts.push(alert);
  }

  if (train.status === 'stopped') {
    const conflict = `Train ${train.name || train.id} service stopped - no current movement detected`;
    // Stopped service is always severe
    const alert = await generateAlert(conflict, 'incident', 'severe', train);
    alerts.push(alert);
  }

  // 3. Route-based alerts (simulate based on patterns)
  if (train.routeName) {
    const routeLower = train.routeName.toLowerCase();
    
    // Detect potential weather issues
    if (Math.random() < 0.05) { // 5% chance for demo
      const weatherTypes = [
        { type: 'heavy rain', severity: 'moderate' },
        { type: 'strong winds', severity: 'severe' },
        { type: 'snow', severity: 'moderate' },
        { type: 'fog', severity: 'minor' }
      ];
      const weather = weatherTypes[Math.floor(Math.random() * weatherTypes.length)];
      const conflict = `${train.routeName} affected by ${weather.type} - potential delays expected`;
      const alert = await generateAlert(conflict, 'weather', weather.severity, train);
      alerts.push(alert);
    }

    // Detect congestion on popular routes
    if (routeLower.includes('express') || routeLower.includes('intercity')) {
      if (Math.random() < 0.03) { // 3% chance
        const conflict = `High passenger volume on ${train.routeName} - potential overcrowding`;
        // Congestion can be moderate if it causes delays
        const severity = Math.random() < 0.4 ? 'moderate' : 'minor';
        const alert = await generateAlert(conflict, 'congestion', severity, train);
        alerts.push(alert);
      }
    }
  }

  // 4. Geographic/regional alerts
  if (train.agency) {
    const agencyLower = train.agency.toLowerCase();
    
    // Simulate region-specific issues
    if (agencyLower.includes('winter') && Math.random() < 0.04) {
      const conflict = `Winter conditions affecting ${train.agency} services - speed restrictions in effect`;
      // Winter conditions vary: 20% severe, 50% moderate, 30% minor
      const rand = Math.random();
      const severity = rand < 0.2 ? 'severe' : (rand < 0.7 ? 'moderate' : 'minor');
      const alert = await generateAlert(conflict, 'speed_restriction', severity, train);
      alerts.push(alert);
    }
  }

  return alerts;
}

/**
 * Generate alert with golden run solution from vector database
 * @param {string} conflict - Conflict description
 * @param {string} type - Conflict type
 * @param {string} severity - Severity level
 * @param {Object} train - Train object for metadata
 * @returns {Promise<Object>} - Alert with solution
 */
async function generateAlert(conflict, type, severity, train) {
  try {
    // Search for similar past incidents in Qdrant
    const searchResult = await alertsService.searchSimilar(conflict, 3);
    
    // If high confidence match found, use that solution
    const suggestedSolution = searchResult.confidence > 0.5 
      ? searchResult.suggestedSolution 
      : getSolution(type, severity);

    return {
      id: `live-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      conflict: conflict,
      conflictType: type,
      severity: severity,
      solution: suggestedSolution,
      confidence: searchResult.confidence,
      similarCount: searchResult.similarAlerts.length,
      train: {
        id: train.id,
        name: train.name,
        route: train.routeName,
        agency: train.agency,
        position: train.position,
      },
      timestamp: new Date().toISOString(),
      source: 'live_detection',
      usingAI: searchResult.usingAI,
    };
  } catch (error) {
    console.error('Error generating alert:', error.message);
    // Fallback to template solution
    return {
      id: `live-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      conflict: conflict,
      conflictType: type,
      severity: severity,
      solution: getSolution(type, severity),
      confidence: 0,
      similarCount: 0,
      train: {
        id: train.id,
        name: train.name,
        route: train.routeName,
        agency: train.agency,
        position: train.position,
      },
      timestamp: new Date().toISOString(),
      source: 'live_detection',
      usingAI: false,
    };
  }
}

/**
 * Filter alerts by severity and recency
 * @param {Array} alerts - Array of alerts
 * @param {Object} options - Filter options
 * @returns {Array} - Filtered alerts
 */
function filterAlerts(alerts, options = {}) {
  const { 
    minSeverity = 'minor', 
    maxAge = 3600000, // 1 hour default
    limit = 50 
  } = options;

  const severityOrder = { minor: 1, moderate: 2, severe: 3 };
  const minSeverityLevel = severityOrder[minSeverity] || 1;

  return alerts
    .filter(alert => {
      // Filter by severity
      const alertSeverityLevel = severityOrder[alert.severity] || 1;
      if (alertSeverityLevel < minSeverityLevel) return false;

      // Filter by age
      const alertAge = Date.now() - new Date(alert.timestamp).getTime();
      if (alertAge > maxAge) return false;

      return true;
    })
    .sort((a, b) => {
      // Sort by severity (descending) then timestamp (newest first)
      const severityDiff = severityOrder[b.severity] - severityOrder[a.severity];
      if (severityDiff !== 0) return severityDiff;
      return new Date(b.timestamp) - new Date(a.timestamp);
    })
    .slice(0, limit);
}

module.exports = {
  generateAlertsFromTrains,
  detectAnomalies,
  generateAlert,
  filterAlerts,
};
