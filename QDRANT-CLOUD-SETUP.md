# Qdrant Cloud Setup Guide

## Getting Started with Qdrant Cloud

### Step 1: Create a Qdrant Cloud Account
1. Go to [https://cloud.qdrant.io](https://cloud.qdrant.io)
2. Sign up for a free account

### Step 2: Create a Cluster
1. Click "Create Cluster"
2. Choose a cluster name
3. Select region (choose closest to you)
4. Choose Free tier or paid plan
5. Click "Create"

### Step 3: Get Your API Credentials
1. Once cluster is created, go to "Data Access Control"
2. Click "Create API Key"
3. Copy your API key (save it securely)
4. Copy your cluster URL (format: `https://xxxxx.qdrant.io`)

### Step 4: Configure Your Application
Update the following files with your Qdrant Cloud credentials:

**1. Root `.env` file:**
```bash
QDRANT_URL=https://your-cluster-url.qdrant.io
QDRANT_API_KEY=your_qdrant_cloud_api_key_here
```

**2. Backend `.env` file (`backend/.env`):**
```bash
QDRANT_URL=https://your-cluster-url.qdrant.io
QDRANT_API_KEY=your_qdrant_cloud_api_key_here
```

### Step 5: Start Your Application

**Without Docker (Recommended for development):**
```bash
# In backend directory
cd backend
npm install
npm start

# In another terminal - frontend directory
cd frontend
npm install
npm start
```

**With Docker Compose:**
```bash
docker-compose up -d backend frontend
```

### Step 6: Verify Connection
Visit http://localhost:3000 and check that the application loads without errors.

## Important Notes

- ✅ No local Qdrant Docker container needed
- ✅ Data persists in the cloud automatically
- ✅ Access from anywhere with API key
- ✅ Free tier includes 1GB cluster
- ⚠️ Keep your API key secure (never commit to git)
- ⚠️ Use HTTPS URL from Qdrant Cloud
