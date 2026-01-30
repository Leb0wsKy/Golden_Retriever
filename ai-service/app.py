from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
from sentence_transformers import SentenceTransformer
import os
import sys
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid
from datetime import datetime

# Add conflicts-collection directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'conflicts-collection'))
from network_monitor import get_network_monitor

load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize models
print("Loading AI models...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
print("Models loaded successfully!")

# Qdrant client
qdrant_client = QdrantClient(
    url=os.getenv('QDRANT_URL', 'http://localhost:6333'),
    api_key=os.getenv('QDRANT_API_KEY', None)
)

# Model registry
MODELS = [
    {
        'id': 'sentence-transformer',
        'name': 'Sentence Transformer',
        'description': 'all-MiniLM-L6-v2 for text embedding',
        'status': 'active',
        'dimension': 384
    },
    {
        'id': 'text-classifier',
        'name': 'Text Classifier',
        'description': 'Sentiment and topic classification',
        'status': 'active',
        'dimension': 384
    },
    {
        'id': 'similarity-search',
        'name': 'Similarity Search',
        'description': 'Semantic search engine',
        'status': 'active',
        'dimension': 384
    }
]

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'AI Service',
        'models_loaded': len(MODELS)
    })

@app.route('/models', methods=['GET'])
def get_models():
    """Get list of available AI models"""
    return jsonify(MODELS)

@app.route('/embed', methods=['POST'])
def generate_embedding():
    """Generate embedding for given text"""
    try:
        data = request.json
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'Text is required'}), 400
        
        # Generate embedding
        embedding = embedding_model.encode(text)
        
        return jsonify({
            'dimension': len(embedding),
            'vector': embedding.tolist(),
            'model': 'all-MiniLM-L6-v2'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/embed_batch', methods=['POST'])
def generate_batch_embeddings():
    """Generate embeddings for multiple texts"""
    try:
        data = request.json
        texts = data.get('texts', [])
        
        if not texts:
            return jsonify({'error': 'Texts array is required'}), 400
        
        # Generate embeddings
        embeddings = embedding_model.encode(texts)
        
        return jsonify({
            'dimension': len(embeddings[0]),
            'vectors': [emb.tolist() for emb in embeddings],
            'count': len(embeddings),
            'model': 'all-MiniLM-L6-v2'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/predict', methods=['POST'])
def predict():
    """Run prediction on input text"""
    try:
        data = request.json
        model_id = data.get('model_id', '')
        input_text = data.get('input', '')
        
        if not input_text:
            return jsonify({'error': 'Input text is required'}), 400
        
        # Generate embedding
        embedding = embedding_model.encode(input_text)
        
        # Simulate prediction (in real scenario, use actual model)
        confidence = float(np.random.uniform(0.7, 0.99))
        result = f"Processed: {input_text[:50]}..."
        
        return jsonify({
            'model_id': model_id,
            'confidence': confidence,
            'result': result,
            'embedding_dimension': len(embedding)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/similarity', methods=['POST'])
def calculate_similarity():
    """Calculate similarity between two texts"""
    try:
        data = request.json
        text1 = data.get('text1', '')
        text2 = data.get('text2', '')
        
        if not text1 or not text2:
            return jsonify({'error': 'Both text1 and text2 are required'}), 400
        
        # Generate embeddings
        emb1 = embedding_model.encode(text1)
        emb2 = embedding_model.encode(text2)
        
        # Calculate cosine similarity
        similarity = float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))
        
        return jsonify({
            'similarity': similarity,
            'text1_length': len(text1),
            'text2_length': len(text2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/insert', methods=['POST'])
def insert_vectors():
    """Insert vectors into Qdrant"""
    try:
        data = request.json
        collection_name = data.get('collection', 'default_collection')
        texts = data.get('texts', [])
        
        if not texts:
            return jsonify({'error': 'Texts array is required'}), 400
        
        # Generate embeddings
        embeddings = embedding_model.encode(texts)
        
        # Create points
        points = []
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            point_id = str(uuid.uuid4())
            points.append(PointStruct(
                id=point_id,
                vector=embedding.tolist(),
                payload={'text': text, 'index': i}
            ))
        
        # Insert into Qdrant
        try:
            qdrant_client.upsert(
                collection_name=collection_name,
                points=points
            )
        except Exception as e:
            # If collection doesn't exist, create it
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
            qdrant_client.upsert(
                collection_name=collection_name,
                points=points
            )
        
        return jsonify({
            'success': True,
            'inserted': len(points),
            'collection': collection_name
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search_similar', methods=['POST'])
def search_similar():
    """Search for similar vectors"""
    try:
        data = request.json
        query = data.get('query', '')
        collection_name = data.get('collection', 'default_collection')
        limit = data.get('limit', 5)
        
        if not query:
            return jsonify({'error': 'Query is required'}), 400
        
        # Generate query embedding
        query_embedding = embedding_model.encode(query)
        
        # Search in Qdrant
        results = qdrant_client.search(
            collection_name=collection_name,
            query_vector=query_embedding.tolist(),
            limit=limit
        )
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                'id': result.id,
                'score': result.score,
                'text': result.payload.get('text', ''),
                'metadata': result.payload
            })
        
        return jsonify({
            'query': query,
            'results': formatted_results,
            'count': len(formatted_results)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/conflicts/network-risk', methods=['POST'])
def get_network_risk():
    """
    Get network-level conflict risk assessment.
    
    Request body:
        {
            "network_id": "FS",  # Network identifier
            "current_time": "2026-01-28T19:00:00Z"  # Optional, defaults to now
        }
    
    Response:
        {
            "network_id": "FS",
            "overall_conflict_rate": 0.85,
            "current_hour_risk": 0.92,
            "risk_level": "critical",
            "high_risk_windows": [...],
            "conflict_types": {...},
            "available": true
        }
    """
    try:
        data = request.json
        network_id = data.get('network_id')
        
        if not network_id:
            return jsonify({'error': 'network_id is required'}), 400
        
        # Parse current time or use now
        current_time_str = data.get('current_time')
        if current_time_str:
            try:
                current_time = datetime.fromisoformat(current_time_str.replace('Z', '+00:00'))
            except:
                current_time = datetime.utcnow()
        else:
            current_time = datetime.utcnow()
        
        # Get network monitor instance
        monitor = get_network_monitor()
        
        # Get risk assessment
        risk_data = monitor.get_network_risk(network_id, current_time)
        
        return jsonify(risk_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/conflicts/networks-summary', methods=['GET'])
def get_networks_summary():
    """
    Get summary of all networks.
    
    Response:
        [
            {
                "network_id": "FS",
                "conflict_rate": 0.989,
                "total_snapshots": 386,
                "avg_train_count": 386.0,
                ...
            }
        ]
    """
    try:
        monitor = get_network_monitor()
        summary = monitor.get_all_networks_summary()
        
        return jsonify({
            'networks': summary,
            'total_networks': len(summary)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('AI_SERVICE_PORT', 5001))
    print(f"Starting AI Service on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
