# Qdrant Vector Database for Golden Retriever

This folder contains all Qdrant-related code for the alerts vector database system.

## 📁 File Structure

```
qdrant/
├── config.js              # Qdrant client configuration
├── solution-templates.js  # Golden run templates (21 pre-defined solutions)
├── collections.js         # Collection management (create, stats, delete)
├── alerts-service.js      # All alert operations (store, search, update, delete)
├── seed-alerts.js         # Seed script with 30 training alerts
└── README.md             # This file
```

## 🚀 Quick Start

### 1. Initialize Collection
Collection is automatically created when backend starts.

### 2. Seed Training Data
```powershell
cd C:\Users\MSI\Golden_Retriever\qdrant
node seed-alerts.js
```

This populates the database with 30 pre-annotated training alerts covering:
- Delays (signal failures, incidents, congestion)
- Cancellations (staffing, strikes, technical faults)
- Weather (snow, wind, flooding, heat, leaves)
- Incidents (trespass, security, medical emergencies)
- Track maintenance (planned works, emergency repairs)
- Speed restrictions
- Regional specifics (TGV, ICE, Amtrak, Shinkansen)

## 🔧 Configuration

### Environment Variables (in backend/.env)
```env
QDRANT_URL=https://your-cluster.gcp.cloud.qdrant.io:6333
QDRANT_API_KEY=your_api_key
AI_SERVICE_URL=http://localhost:5001
```

### Constants (in config.js)
- **Collection Name**: `train_alerts`
- **Vector Dimension**: 384 (SentenceTransformer all-MiniLM-L6-v2)
- **Distance Metric**: Cosine
- **Default Search Limit**: 5

## 📚 Module Documentation

### config.js
Exports:
- `qdrantClient` - QdrantClient instance
- `QDRANT_CONFIG` - Configuration constants

### solution-templates.js
Exports:
- `SOLUTION_TEMPLATES` - 7 conflict types × 3 severities = 21 templates
- `detectConflictType(description)` - Auto-categorize conflicts
- `getSolution(conflictType, severity)` - Get template solution

### collections.js
Exports:
- `initializeAlertsCollection()` - Create collection
- `getCollectionStats()` - Get metrics (count, status, dimension)
- `deleteCollection(name)` - Remove collection

### alerts-service.js
Exports:
- `generateEmbedding(text)` - Convert text → 384-dim vector
- `storeAlert(alert)` - Store single alert
- `storeBatch(alerts)` - Store multiple alerts
- `searchSimilar(text, limit)` - Find similar past incidents
- `getAllAlerts(limit, offset)` - List all stored alerts
- `updateSolution(id, solution)` - Update golden run manually
- `deleteAlert(id)` - Remove alert

## 🎯 Usage Examples

### Import in Your Code
```javascript
const { qdrantClient, QDRANT_CONFIG } = require('./qdrant/config');
const { storeAlert, searchSimilar } = require('./qdrant/alerts-service');
const { detectConflictType, getSolution } = require('./qdrant/solution-templates');

// Store new alert
await storeAlert({
  conflict: "Train delayed by 15 minutes",
  conflictType: "delay",
  severity: "minor",
  solution: "Wait for service to resume..."
});

// Search for similar incidents
const results = await searchSimilar("Signal problems causing delays", 5);
console.log(results.suggestedSolution);
console.log(results.confidence);
```

### Direct API Usage (from backend)
```javascript
// In server.js
const alertsService = require('../qdrant/alerts-service');

app.post('/api/alerts/search', async (req, res) => {
  const results = await alertsService.searchSimilar(req.body.conflict);
  res.json(results);
});
```

## 🔍 Solution Templates

### Conflict Types
1. **delay** - Signal failures, late running
2. **cancellation** - Service not running
3. **speed_restriction** - Reduced speed limits
4. **track_maintenance** - Engineering works
5. **weather** - Snow, wind, flooding, heat
6. **incident** - Trespass, security, accidents
7. **congestion** - Overcrowding, capacity issues

### Severity Levels
- **minor** - < 15 min impact, service continues
- **moderate** - 15-45 min impact, alternative routes needed
- **severe** - > 45 min impact, seek alternative transport

## 📊 Data Schema

Each alert contains:
```javascript
{
  id: 1769457038585842,                    // Numeric ID
  conflict: "Train delayed...",             // Description
  conflictType: "delay",                    // Auto-detected category
  severity: "minor",                        // minor/moderate/severe
  solution: "Wait for service...",          // Golden run
  metadata: {                               // Optional context
    category: "signal",
    region: "central",
    operator: "SNCF"
  },
  createdAt: "2026-01-26T19:50:38.585Z",   // Timestamp
  source: "batch_import"                    // Origin
}
```

## 🧪 Testing

```powershell
# Check collection stats
Invoke-RestMethod http://localhost:5000/api/alerts/stats

# View all alerts
Invoke-RestMethod http://localhost:5000/api/alerts/stored

# Search for solution
$body = @{conflict = "Signal failure causing delays"} | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:5000/api/alerts/search-similar `
  -Method POST -Body $body -ContentType "application/json"
```

## 🔗 Integration Points

### Backend (server.js)
- Imports alerts-service for all Qdrant operations
- Exposes REST API endpoints
- Handles request validation

### AI Service (ai-service/app.py)
- Generates 384-dimensional embeddings
- Uses SentenceTransformer model
- POST /embed endpoint

### Frontend (future)
- Display alerts dashboard
- Search for similar incidents
- Manual annotation interface

## 🛠️ Maintenance

### Re-seed Database
```powershell
cd qdrant
node seed-alerts.js
```

### Clear Database (careful!)
```javascript
const { deleteCollection } = require('./qdrant/collections');
await deleteCollection('train_alerts');
```

### Add New Training Data
Edit `seed-alerts.js` → Add to `SEED_ALERTS` array → Re-run script

## 📈 Performance

- **Vector Dimension**: 384 (optimal for semantic search)
- **Search Speed**: < 100ms for 5 results (up to 10K points)
- **Batch Import**: ~30 alerts/minute (with AI Service)
- **Storage**: ~2KB per alert (vector + payload)

## 🔐 Security

- API key stored in `.env` (not committed to git)
- Qdrant Cloud uses TLS encryption
- Backend validates all inputs before Qdrant operations

## 📝 Notes

- Always ensure AI Service is running for embeddings
- Fallback to random vectors if AI Service unavailable
- Numeric IDs required (not strings)
- Collection auto-created on backend startup
- Seed script is idempotent (can run multiple times)

## 🆘 Troubleshooting

**"Bad Request" errors during import:**
- Check ID format (must be numeric)
- Verify AI Service is running
- Check QDRANT_URL and QDRANT_API_KEY in .env

**Empty search results:**
- Run seed script to populate database
- Verify collection exists: `GET /api/alerts/stats`
- Check AI Service for embedding generation

**Low confidence scores (< 0.5):**
- Add more training data with similar conflicts
- Verify embeddings are being generated (not random vectors)
- Check conflict description quality
