"""
Quick fix: Add payload indexes to pre_conflict_memory collection
"""
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PayloadSchemaType

load_dotenv()

# Connect to Qdrant
client = QdrantClient(
    url=os.getenv('QDRANT_URL'),
    api_key=os.getenv('QDRANT_API_KEY')
)

print("Adding payload indexes to pre_conflict_memory collection...")

try:
    # Add source index (keyword for exact matching)
    print("  Creating index for 'source' field...")
    client.create_payload_index(
        collection_name="pre_conflict_memory",
        field_name="source",
        field_schema=PayloadSchemaType.KEYWORD
    )
    print("  ✓ source index created")
    
    # Add network_id index
    print("  Creating index for 'network_id' field...")
    client.create_payload_index(
        collection_name="pre_conflict_memory",
        field_name="network_id",
        field_schema=PayloadSchemaType.KEYWORD
    )
    print("  ✓ network_id index created")
    
    # Add probability index
    print("  Creating index for 'probability' field...")
    client.create_payload_index(
        collection_name="pre_conflict_memory",
        field_name="probability",
        field_schema=PayloadSchemaType.FLOAT
    )
    print("  ✓ probability index created")
    
    print("\n✅ All indexes created successfully!")
    
except Exception as e:
    if "already exists" in str(e).lower():
        print(f"\n⚠️  Indexes may already exist: {e}")
    else:
        print(f"\n❌ Error: {e}")
        raise
