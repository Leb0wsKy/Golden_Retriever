/**
 * Solution Templates (Golden Runs)
 * 
 * Pre-defined best practice solutions for each conflict type and severity level
 */

const SOLUTION_TEMPLATES = {
  'delay': {
    'minor': 'Wait for next scheduled departure. Expected recovery within 10 minutes. Monitor real-time updates.',
    'moderate': 'Consider alternative route. Delay expected to persist. Check connecting services.',
    'severe': 'Service significantly impacted. Seek alternative transportation or contact station staff for assistance.'
  },
  'cancellation': {
    'minor': 'Service cancelled. Next available train in 15-30 minutes.',
    'moderate': 'Multiple cancellations. Consider alternative route or replacement bus service.',
    'severe': 'Line suspended. Use replacement bus service or seek alternative transportation.'
  },
  'speed_restriction': {
    'minor': 'Minor speed restriction. Allow 5-10 extra minutes for journey.',
    'moderate': 'Speed restriction in effect. Journey time increased by 15-20 minutes.',
    'severe': 'Significant speed restriction. Major delays expected. Consider alternative routes.'
  },
  'track_maintenance': {
    'minor': 'Scheduled maintenance. Minor service adjustments.',
    'moderate': 'Track work in progress. Some services diverted or replaced by buses.',
    'severe': 'Major engineering works. Line closed. Use designated replacement services.'
  },
  'weather': {
    'minor': 'Weather advisory. Services running with minor delays.',
    'moderate': 'Adverse weather conditions. Expect delays of 20-30 minutes.',
    'severe': 'Severe weather. Services suspended for safety. Do not travel unless essential.'
  },
  'incident': {
    'minor': 'Minor incident. Services resuming shortly.',
    'moderate': 'Incident on line. Emergency services attending. Delays of 30+ minutes expected.',
    'severe': 'Major incident. Line closed. Seek alternative transportation.'
  },
  'congestion': {
    'minor': 'High passenger volumes. Allow extra time for boarding.',
    'moderate': 'Overcrowding at stations. Consider traveling at off-peak times.',
    'severe': 'Severe congestion. Station entry may be restricted. Use alternative stations if possible.'
  }
};

/**
 * Detect conflict type from text description
 * @param {string} description - The conflict description
 * @returns {string} - Detected conflict type
 */
function detectConflictType(description) {
  const desc = description.toLowerCase();
  if (desc.includes('delay') || desc.includes('late') || desc.includes('behind schedule')) return 'delay';
  if (desc.includes('cancel') || desc.includes('terminated')) return 'cancellation';
  if (desc.includes('speed') || desc.includes('slow')) return 'speed_restriction';
  if (desc.includes('maintenance') || desc.includes('engineering') || desc.includes('track work')) return 'track_maintenance';
  if (desc.includes('weather') || desc.includes('storm') || desc.includes('flood') || desc.includes('snow')) return 'weather';
  if (desc.includes('incident') || desc.includes('emergency') || desc.includes('accident')) return 'incident';
  if (desc.includes('crowd') || desc.includes('busy') || desc.includes('congestion')) return 'congestion';
  return 'incident'; // Default
}

/**
 * Get solution template based on conflict type and severity
 * @param {string} conflictType - The type of conflict
 * @param {string} severity - The severity level (minor, moderate, severe)
 * @returns {string} - The recommended solution
 */
function getSolution(conflictType, severity) {
  const templates = SOLUTION_TEMPLATES[conflictType] || SOLUTION_TEMPLATES['incident'];
  return templates[severity] || templates['moderate'] || 'Monitor real-time updates and follow station announcements.';
}

module.exports = {
  SOLUTION_TEMPLATES,
  detectConflictType,
  getSolution,
};
