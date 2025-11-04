"""
Test script to verify RAG services initialization and basic functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.logger import get_logger
from services.cache_service import cache_service
from services.qdrant_service import qdrant_service
from services.embedding_service import embedding_service
from services.together_service import together_service
from services.document_service import document_service
from services.chunking_service import chunking_service
from services.chat_service import chat_service
from services.rag_orchestrator import rag_orchestrator

logger = get_logger("test_services")


async def test_cache_service():
    """Test Redis cache service."""
    try:
        logger.info("Testing cache service...")
        await cache_service.initialize()
        
        # Test basic operations
        await cache_service.set("test_key", "test_value")
        value = await cache_service.get("test_key")
        
        assert value == "test_value", "Cache get/set failed"
        
        # Test JSON operations
        await cache_service.set_json("test_json", {"key": "value"})
        json_value = await cache_service.get_json("test_json")
        
        assert json_value["key"] == "value", "Cache JSON operations failed"
        
        # Get stats
        stats = await cache_service.get_stats()
        logger.info(f"Cache stats: {stats}")
        
        logger.info("✓ Cache service test passed")
        return True
    except Exception as e:
        logger.error(f"✗ Cache service test failed: {str(e)}")
        return False


def test_qdrant_service():
    """Test Qdrant vector database service."""
    try:
        logger.info("Testing Qdrant service...")
        qdrant_service.initialize()
        
        # Get collection info
        collection_info = asyncio.run(qdrant_service.get_collection_info())
        logger.info(f"Collection info: {collection_info}")
        
        logger.info("✓ Qdrant service test passed")
        return True
    except Exception as e:
        logger.error(f"✗ Qdrant service test failed: {str(e)}")
        return False


def test_together_service():
    """Test Together AI service."""
    try:
        logger.info("Testing Together AI service...")
        together_service.initialize()
        
        logger.info("✓ Together AI service test passed")
        return True
    except Exception as e:
        logger.error(f"✗ Together AI service test failed: {str(e)}")
        return False


def test_embedding_service():
    """Test embedding service."""
    try:
        logger.info("Testing embedding service...")
        embedding_service.initialize()
        
        # Test embedding generation
        embedding = asyncio.run(
            embedding_service.generate_embedding("Test text for embedding", use_cache=False)
        )
        
        assert len(embedding) == 768, f"Expected 768 dimensions, got {len(embedding)}"
        
        logger.info(f"✓ Embedding service test passed (dimension: {len(embedding)})")
        return True
    except Exception as e:
        logger.error(f"✗ Embedding service test failed: {str(e)}")
        return False


def test_document_service():
    """Test document service."""
    try:
        logger.info("Testing document service...")
        document_service.initialize()
        
        logger.info("✓ Document service test passed")
        return True
    except Exception as e:
        logger.error(f"✗ Document service test failed: {str(e)}")
        return False


def test_chunking_service():
    """Test chunking service."""
    try:
        logger.info("Testing chunking service...")
        chunking_service.initialize()
        
        # Test text chunking
        test_text = "This is a test text. " * 50
        nodes = asyncio.run(chunking_service.chunk_text(test_text))
        
        assert len(nodes) > 0, "Chunking produced no nodes"
        
        stats = chunking_service.get_chunk_stats(nodes)
        logger.info(f"Chunk stats: {stats}")
        
        logger.info(f"✓ Chunking service test passed ({len(nodes)} chunks)")
        return True
    except Exception as e:
        logger.error(f"✗ Chunking service test failed: {str(e)}")
        return False


def test_chat_service():
    """Test chat service."""
    try:
        logger.info("Testing chat service...")
        chat_service.initialize()
        
        logger.info("✓ Chat service test passed")
        return True
    except Exception as e:
        logger.error(f"✗ Chat service test failed: {str(e)}")
        return False


def test_rag_orchestrator():
    """Test RAG orchestrator."""
    try:
        logger.info("Testing RAG orchestrator...")
        rag_orchestrator.initialize()
        
        # Get system stats
        stats = asyncio.run(rag_orchestrator.get_system_stats())
        logger.info(f"RAG system stats: {stats}")
        
        logger.info("✓ RAG orchestrator test passed")
        return True
    except Exception as e:
        logger.error(f"✗ RAG orchestrator test failed: {str(e)}")
        return False


async def main():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Starting RAG Services Test Suite")
    logger.info("=" * 60)
    
    results = {}
    
    # Test each service
    results["cache"] = await test_cache_service()
    results["qdrant"] = test_qdrant_service()
    results["together"] = test_together_service()
    results["embedding"] = test_embedding_service()
    results["document"] = test_document_service()
    results["chunking"] = test_chunking_service()
    results["chat"] = test_chat_service()
    results["rag_orchestrator"] = test_rag_orchestrator()
    
    # Clean up
    await cache_service.close()
    
    # Summary
    logger.info("=" * 60)
    logger.info("Test Results Summary")
    logger.info("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for service, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        logger.info(f"{service:20s}: {status}")
    
    logger.info("=" * 60)
    logger.info(f"Total: {passed}/{total} tests passed")
    logger.info("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
