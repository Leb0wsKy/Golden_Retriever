/**
 * Seed Alert Data for Golden Retriever
 * 
 * This script populates your Qdrant database with training data for the
 * alerts vector database. Run this once to bootstrap your golden run data.
 * 
 * Usage: node seed-alerts.js
 */

const axios = require('axios');

const BACKEND_URL = 'http://localhost:5000';

// Seed data: Common train conflicts with annotated solutions (Golden Runs)
const SEED_ALERTS = [
  // === DELAYS ===
  {
    conflict: "Train delayed by 10 minutes due to signal failure at central station",
    conflictType: "delay",
    severity: "minor",
    solution: "Wait for service to resume. Signal issue being resolved. Expected recovery: 10-15 minutes.",
    metadata: { category: "signal", region: "central" }
  },
  {
    conflict: "Train delayed by 25 minutes due to earlier incident on the line",
    conflictType: "delay",
    severity: "moderate",
    solution: "Consider alternative routes if available. Service running with delays. Allow extra 30 minutes for journey.",
    metadata: { category: "knock-on", region: "general" }
  },
  {
    conflict: "Severe delays of 45+ minutes due to infrastructure damage",
    conflictType: "delay",
    severity: "severe",
    solution: "Seek alternative transportation. Replacement bus service may be available. Contact station staff for refund options.",
    metadata: { category: "infrastructure", region: "general" }
  },
  {
    conflict: "High-speed train running 15 minutes behind schedule due to speed restrictions",
    conflictType: "delay",
    severity: "minor",
    solution: "Train will attempt to recover time en route. Connections may still be achievable. Monitor announcements.",
    metadata: { category: "speed_restriction", region: "high_speed" }
  },
  {
    conflict: "Commuter train delayed during rush hour due to overcrowding",
    conflictType: "delay",
    severity: "moderate",
    solution: "Allow additional boarding time. Consider waiting for next service for better comfort. Peak delays expected.",
    metadata: { category: "congestion", region: "urban" }
  },

  // === CANCELLATIONS ===
  {
    conflict: "Train service cancelled due to driver shortage",
    conflictType: "cancellation",
    severity: "moderate",
    solution: "Board next available service (approximately 30 minutes). Tickets valid on alternative operators where available.",
    metadata: { category: "staffing", region: "general" }
  },
  {
    conflict: "Multiple trains cancelled due to strike action",
    conflictType: "cancellation",
    severity: "severe",
    solution: "Limited service running. Check timetable for confirmed services. Consider alternative transportation or postpone travel.",
    metadata: { category: "industrial_action", region: "national" }
  },
  {
    conflict: "Train cancelled due to technical fault with rolling stock",
    conflictType: "cancellation",
    severity: "moderate",
    solution: "Replacement service arranged. Board next train or use ticket on bus replacement service.",
    metadata: { category: "technical", region: "general" }
  },
  {
    conflict: "Last train of the day cancelled unexpectedly",
    conflictType: "cancellation",
    severity: "severe",
    solution: "Emergency taxi service may be available - check with station staff. Keep receipts for refund claim.",
    metadata: { category: "service_gap", region: "general" }
  },

  // === TRACK MAINTENANCE ===
  {
    conflict: "Planned engineering works affecting weekend services",
    conflictType: "track_maintenance",
    severity: "moderate",
    solution: "Bus replacement service in operation. Journey time extended by approximately 45 minutes. Check revised timetable.",
    metadata: { category: "planned_works", region: "general" }
  },
  {
    conflict: "Emergency track repair required after equipment failure",
    conflictType: "track_maintenance",
    severity: "severe",
    solution: "Line closed between stations A and B. Use alternative route via station C or replacement bus service.",
    metadata: { category: "emergency_repair", region: "general" }
  },
  {
    conflict: "Single line operation due to maintenance work",
    conflictType: "track_maintenance",
    severity: "minor",
    solution: "Services running at reduced frequency. Allow extra 15 minutes. Trains may wait at passing points.",
    metadata: { category: "single_line", region: "general" }
  },

  // === WEATHER ===
  {
    conflict: "Services disrupted due to heavy snow and ice on tracks",
    conflictType: "weather",
    severity: "severe",
    solution: "Do not travel unless essential. Services suspended until conditions improve. Check before traveling.",
    metadata: { category: "snow", region: "general", season: "winter" }
  },
  {
    conflict: "Delays expected due to high winds affecting overhead lines",
    conflictType: "weather",
    severity: "moderate",
    solution: "Speed restrictions in place. Allow extra 20-30 minutes. Services may be short-formed.",
    metadata: { category: "wind", region: "general" }
  },
  {
    conflict: "Train services suspended due to flooding on tracks",
    conflictType: "weather",
    severity: "severe",
    solution: "Line closed. No rail replacement available due to road flooding. Postpone travel if possible.",
    metadata: { category: "flood", region: "general" }
  },
  {
    conflict: "Minor delays due to leaves on the line affecting braking",
    conflictType: "weather",
    severity: "minor",
    solution: "Speed restrictions in leaf-fall areas. Allow extra 10 minutes. Normal service expected later.",
    metadata: { category: "leaves", region: "general", season: "autumn" }
  },
  {
    conflict: "Heat restrictions causing reduced speeds on high-speed lines",
    conflictType: "weather",
    severity: "moderate",
    solution: "Speed limits applied to prevent track buckling. Journey times extended by 15-25 minutes.",
    metadata: { category: "heat", region: "high_speed", season: "summer" }
  },

  // === INCIDENTS ===
  {
    conflict: "Services suspended due to trespass incident on the railway",
    conflictType: "incident",
    severity: "severe",
    solution: "Emergency services attending. Line closed. No estimated time for reopening. Seek alternative transport.",
    metadata: { category: "trespass", region: "general" }
  },
  {
    conflict: "Train struck object on track causing service disruption",
    conflictType: "incident",
    severity: "moderate",
    solution: "Train being inspected. Expect delays of 30-45 minutes. Following services affected.",
    metadata: { category: "obstruction", region: "general" }
  },
  {
    conflict: "Security alert at station causing evacuation",
    conflictType: "incident",
    severity: "severe",
    solution: "Station closed. Trains not stopping. Use alternative stations or await all-clear announcement.",
    metadata: { category: "security", region: "station" }
  },
  {
    conflict: "Medical emergency on board causing delay",
    conflictType: "incident",
    severity: "minor",
    solution: "Train held at station while emergency services attend. Service will resume shortly.",
    metadata: { category: "medical", region: "general" }
  },
  {
    conflict: "Level crossing failure blocking train movements",
    conflictType: "incident",
    severity: "moderate",
    solution: "Engineers en route. Trains held at stations either side. Expect 20-30 minute delays.",
    metadata: { category: "level_crossing", region: "general" }
  },

  // === CONGESTION ===
  {
    conflict: "Platform overcrowding at major station during event",
    conflictType: "congestion",
    severity: "moderate",
    solution: "Station entry control in place. Use alternative stations if possible. Extra services running.",
    metadata: { category: "event", region: "station" }
  },
  {
    conflict: "Trains at capacity during morning rush hour",
    conflictType: "congestion",
    severity: "minor",
    solution: "Consider traveling slightly earlier or later. Next train in 5 minutes may have more space.",
    metadata: { category: "peak_hours", region: "urban" }
  },

  // === SPEED RESTRICTIONS ===
  {
    conflict: "Temporary speed restriction due to track condition",
    conflictType: "speed_restriction",
    severity: "minor",
    solution: "Minor delays expected. Journey time increased by 5-10 minutes on affected section.",
    metadata: { category: "track_condition", region: "general" }
  },
  {
    conflict: "Severe speed restrictions following derailment in area",
    conflictType: "speed_restriction",
    severity: "severe",
    solution: "Major delays on all services. Consider alternative routes. Recovery expected within 24 hours.",
    metadata: { category: "safety", region: "general" }
  },

  // === REGIONAL SPECIFIC ===
  {
    conflict: "TGV service delayed departing Paris Gare de Lyon",
    conflictType: "delay",
    severity: "moderate",
    solution: "High-speed connection may be missed. SNCF will rebook on next available TGV at no extra cost.",
    metadata: { category: "connection", region: "france", operator: "SNCF" }
  },
  {
    conflict: "Deutsche Bahn ICE service running with reduced capacity",
    conflictType: "congestion",
    severity: "moderate",
    solution: "Seat reservations honored. Standing passengers expected. First class may have availability.",
    metadata: { category: "capacity", region: "germany", operator: "DB" }
  },
  {
    conflict: "Amtrak service delayed due to freight train priority",
    conflictType: "delay",
    severity: "moderate",
    solution: "Passenger train waiting for freight clearance. Typical delay 15-30 minutes on shared corridors.",
    metadata: { category: "freight_priority", region: "usa", operator: "Amtrak" }
  },
  {
    conflict: "Shinkansen service briefly halted due to earthquake detection",
    conflictType: "incident",
    severity: "minor",
    solution: "Automatic safety stop activated. Service resumes after track inspection, typically 10-15 minutes.",
    metadata: { category: "earthquake", region: "japan", operator: "JR" }
  }
];

async function seedAlerts() {
  console.log('🌱 Starting to seed alerts database...\n');
  
  try {
    // First, check if backend is running
    const healthCheck = await axios.get(`${BACKEND_URL}/api/health`);
    console.log('✅ Backend is healthy:', healthCheck.data.status);
    
    // Check current alert count
    try {
      const stats = await axios.get(`${BACKEND_URL}/api/alerts/stats`);
      console.log(`📊 Current alerts in database: ${stats.data.totalAlerts}`);
    } catch (e) {
      console.log('📊 Alerts collection will be created...');
    }
    
    console.log(`\n📝 Seeding ${SEED_ALERTS.length} training alerts...\n`);
    
    // Store alerts in batches
    const response = await axios.post(`${BACKEND_URL}/api/alerts/store-batch`, {
      alerts: SEED_ALERTS
    });
    
    console.log('✅ Seeding complete!');
    console.log(`   - Stored: ${response.data.stored} alerts`);
    console.log(`   - Failed: ${response.data.failed} alerts`);
    
    if (response.data.errors && response.data.errors.length > 0) {
      console.log('\n⚠️ Errors:');
      response.data.errors.forEach(err => console.log(`   - ${err.conflict}: ${err.error}`));
    }
    
    // Final stats
    const finalStats = await axios.get(`${BACKEND_URL}/api/alerts/stats`);
    console.log(`\n📊 Total alerts in database: ${finalStats.data.totalAlerts}`);
    
    console.log('\n🎉 Your Qdrant database is now populated with training data!');
    console.log('   You can now use /api/alerts/search-similar to find golden runs.\n');
    
  } catch (error) {
    console.error('❌ Error seeding alerts:', error.message);
    if (error.response) {
      console.error('   Response:', error.response.data);
    }
    console.log('\n💡 Make sure:');
    console.log('   1. Backend is running (npm start in backend folder)');
    console.log('   2. Qdrant is accessible (check QDRANT_URL in .env)');
    console.log('   3. AI Service is running for embeddings (optional)\n');
  }
}

// Run the seeder
seedAlerts();
