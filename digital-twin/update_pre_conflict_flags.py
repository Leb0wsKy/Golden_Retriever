"""
Quick script to update existing pre-conflict memory records
to set conflict_occurred=True.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import UpdateStatus, PointStruct
import json

# Qdrant Cloud credentials
QDRANT_URL = "https://23c61f1a-2a97-459a-b2bc-ab20d78efaa6.europe-west3-0.gcp.cloud.qdrant.io:6333"
QDRANT_API_KEY = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL2V1cm9wZS13ZXN0My0wLmdjcC5jbG91ZC5xZHJhbnQuaW86NjMzMyIsInN1YiI6InZoYWhtZWRAZ21haWwuY29tIiwiYXVkIjpbImh0dHBzOi8vZXVyb3BlLXdlc3QzLTAuZ2NwLmNsb3VkLnFkcmFudC5pbzo2MzMzIl0sImV4cCI6MTc3MDczMDI1Nn0.EXpnLgd4f4dQIV6lLG6mhZdEF-tWPU87yoC67oCHEU_HoB4h4ItIIJyTXxO0wxEgLaL_yF93PJ5D9VH5SVy6fA"

def main():
    print("Connecting to Qdrant Cloud...")
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    
    print("Fetching all pre-conflict states...")
    offset = None
    updated_count = 0
    total_count = 0
    
    while True:
        # Scroll through all points
        results, next_offset = client.scroll(
            collection_name="pre_conflict_memory",
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=True
        )
        
        if not results:
            break
        
        total_count += len(results)
        
        # Update each point
        points_to_update = []
        for point in results:
            payload = point.payload
            
            # Check if needs update
            if not payload.get('conflict_occurred', False):
                # Update the payload
                payload['conflict_occurred'] = True
                
                # If metadata has conflict info, also set top-level fields
                metadata = payload.get('metadata', {})
                if 'later_conflict_type' in metadata:
                    payload['conflict_type'] = metadata['later_conflict_type']
                
                points_to_update.append(
                    PointStruct(
                        id=point.id,
                        vector=point.vector,
                        payload=payload
                    )
                )
        
        # Batch update
        if points_to_update:
            print(f"Updating {len(points_to_update)} points...")
            client.upsert(
                collection_name="pre_conflict_memory",
                points=points_to_update
            )
            updated_count += len(points_to_update)
        
        # Check if more results
        offset = next_offset
        if offset is None:
            break
    
    print(f"\n✅ Update complete!")
    print(f"   Total points: {total_count}")
    print(f"   Updated: {updated_count}")
    
    # Verify
    print("\n🔍 Verifying updates...")
    sample = client.scroll(
        collection_name="pre_conflict_memory",
        limit=1,
        with_payload=True
    )[0][0]
    
    print(f"\nSample record:")
    print(f"  - conflict_occurred: {sample.payload.get('conflict_occurred')}")
    print(f"  - conflict_type: {sample.payload.get('conflict_type')}")

if __name__ == "__main__":
    main()
