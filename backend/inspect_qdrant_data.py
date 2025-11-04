#!/usr/bin/env python3
"""
Qdrant Database Diagnostic Script

This script connects to the Qdrant vector database and provides detailed information
about collections, their configurations, and stored data points.
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Add parent directory to path to import config
sys.path.append(str(Path(__file__).parent))

from qdrant_client import QdrantClient
from qdrant_client.models import Distance
from config.settings import settings


class QdrantInspector:
    """Inspector class for examining Qdrant database contents"""

    def __init__(self):
        """Initialize Qdrant client with same configuration as the application"""
        try:
            self.client = QdrantClient(
                url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY, timeout=120
            )
            print("✅ Successfully connected to Qdrant database")
            print(f"   URL: {settings.QDRANT_URL}")
            print(f"   Environment: {settings.ENVIRONMENT}")
            print(f"   Expected collection: {settings.QDRANT_COLLECTION_NAME}")
            print()
        except Exception as e:
            print(f"❌ Failed to connect to Qdrant: {str(e)}")
            sys.exit(1)

    def list_collections(self) -> List[str]:
        """List all collections in the database"""
        try:
            collections_info = self.client.get_collections()
            collections = [c.name for c in collections_info.collections]
            print(f"📋 Found {len(collections)} collections:")
            for collection in collections:
                print(f"   - {collection}")
            print()
            return collections
        except Exception as e:
            print(f"❌ Failed to list collections: {str(e)}")
            return []

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get detailed information about a collection"""
        try:
            info = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vector_size": info.config.params.vectors.size,
                "distance_metric": info.config.params.vectors.distance.value,
                "vector_count": info.vectors_count,
                "indexed_vector_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "status": info.status.value,
                "payload_schema": info.config.params.payload_schema
                if hasattr(info.config.params, "payload_schema")
                else {},
            }
        except Exception as e:
            print(f"❌ Failed to get info for collection '{collection_name}': {str(e)}")
            return {}

    def count_points(self, collection_name: str) -> int:
        """Count total points in a collection"""
        try:
            # Use scroll with limit 1 to get total count efficiently
            result, total_count = self.client.scroll(
                collection_name=collection_name,
                limit=1,
                with_payload=False,
                with_vectors=False,
            )
            return total_count
        except Exception as e:
            print(f"❌ Failed to count points in '{collection_name}': {str(e)}")
            return 0

    def get_sample_points(
        self, collection_name: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get sample data points from a collection"""
        try:
            points, _ = self.client.scroll(
                collection_name=collection_name,
                limit=limit,
                with_payload=True,
                with_vectors=True,
            )

            sample_data = []
            for point in points:
                sample_data.append(
                    {
                        "id": point.id,
                        "vector": point.vector[:10]
                        if point.vector
                        else [],  # Truncate vector for display
                        "payload": point.payload,
                        "vector_full_length": len(point.vector) if point.vector else 0,
                    }
                )

            return sample_data
        except Exception as e:
            print(f"❌ Failed to get sample points from '{collection_name}': {str(e)}")
            return []

    def inspect_collection(self, collection_name: str):
        """Comprehensive inspection of a single collection"""
        print(f"🔍 Inspecting collection: {collection_name}")
        print("=" * 60)

        # Get collection info
        info = self.get_collection_info(collection_name)
        if not info:
            return

        print("📊 Collection Information:")
        print(f"   Name: {info['name']}")
        print(f"   Status: {info['status']}")
        print(f"   Vector Size: {info['vector_size']}")
        print(f"   Distance Metric: {info['distance_metric']}")
        print(f"   Total Points: {info['points_count']}")
        print(f"   Indexed Vectors: {info['indexed_vector_count']}")

        # Payload schema info if available
        if info.get("payload_schema"):
            print("   Payload Schema:")
            for field, schema_type in info["payload_schema"].items():
                print(f"     - {field}: {schema_type}")

        print()

        # Sample points
        if info["points_count"] > 0:
            sample_points = self.get_sample_points(collection_name, limit=5)
            if sample_points:
                print("📝 Sample Data Points (first 5):")
                for i, point in enumerate(sample_points, 1):
                    print(f"   Point {i}:")
                    print(f"     ID: {point['id']}")
                    print(
                        f"     Vector (first 10 values): {point['vector'][:10]}... (full length: {point['vector_full_length']})"
                    )
                    for key, value in point["payload"].items():
                        if key == "metadata" and isinstance(value, dict):
                            print(
                                f"       {key}: {dict(list(value.items())[:3])}..."
                                if len(value) > 3
                                else f"       {key}: {value}"
                            )
                        elif isinstance(value, str) and len(value) > 100:
                            print(f"       {key}: {value[:100]}...")
                        else:
                            print(f"       {key}: {value}")
                    print()
        else:
            print("📝 No data points found in this collection")

        print("=" * 60)
        print()

    def generate_summary(self, collections_data: List[Dict[str, Any]]):
        """Generate a summary of all collections"""
        print("📋 SUMMARY REPORT")
        print("=" * 80)
        print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Environment: {settings.ENVIRONMENT}")
        print(f"Qdrant URL: {settings.QDRANT_URL}")
        print()

        total_collections = len(collections_data)
        total_points = sum(info.get("points_count", 0) for info in collections_data)

        print(f"Total Collections: {total_collections}")
        print(f"Total Data Points: {total_points}")
        print()

        if collections_data:
            print("Collection Details:")
            for info in collections_data:
                print(
                    f"  • {info['name']}: {info.get('points_count', 0)} points "
                    f"({info.get('vector_size', 'N/A')}D, {info.get('distance_metric', 'N/A')})"
                )

        print()
        print("✅ Inspection completed successfully")


def main():
    """Main function to run the diagnostic inspection"""
    print("🚀 Starting Qdrant Database Diagnostic")
    print("=" * 80)
    print()

    inspector = QdrantInspector()

    # List all collections
    collections = inspector.list_collections()

    # Inspect each collection
    collections_data = []
    for collection_name in collections:
        inspector.inspect_collection(collection_name)
        info = inspector.get_collection_info(collection_name)
        if info:
            collections_data.append(info)

    # Generate summary
    inspector.generate_summary(collections_data)

    print("\n🎯 Script completed. Check the output above for detailed information.")


if __name__ == "__main__":
    main()
