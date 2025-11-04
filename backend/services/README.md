# Lumina IQ RAG Backend Services

## Overview

This directory contains all service modules for the Lumina IQ RAG (Retrieval-Augmented Generation) backend. The system is built with a modular architecture using:

- **LlamaIndex** for PDF extraction and chunking
- **LangChain** with **Together AI** for embeddings and chat
- **Qdrant Cloud** for vector storage
- **Redis Cloud** for caching
- **Celery** for background task processing

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     RAG Orchestrator                         │
│                  (rag_orchestrator.py)                       │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Document    │ │  Chunking    │ │  Embedding   │
│  Service     │ │  Service     │ │  Service     │
│ (LlamaIndex) │ │ (LlamaIndex) │ │ (LangChain)  │
└──────────────┘ └──────────────┘ └──────────────┘
        │            │            │
        └────────────┼────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Qdrant     │ │    Cache     │ │    Chat      │
│   Service    │ │   Service    │ │   Service    │
│  (Vectors)   │ │   (Redis)    │ │ (LangChain)  │
└──────────────┘ └──────────────┘ └──────────────┘
```

## Services

### 1. **cache_service.py**
Redis-based caching service with semantic cache support.

**Features:**
- Multi-level caching (embeddings, retrieval results, API responses)
- Automatic TTL management
- JSON serialization support
- Cache statistics and monitoring

**Key Methods:**
```python
await cache_service.initialize()
await cache_service.set(key, value, ttl)
await cache_service.get(key)
await cache_service.cache_embedding(text, embedding, model)
await cache_service.get_cached_embedding(text, model)
```

**Configuration:**
- `REDIS_URL`: Redis connection URL
- `REDIS_CACHE_DB`: Database number for caching
- `CACHE_TTL_SECONDS`: Default TTL for cache entries

---

### 2. **together_service.py**
Together AI API integration for LLM and embeddings.

**Features:**
- Direct Together AI client integration
- Embedding generation
- Chat completion
- Question generation from context

**Key Methods:**
```python
together_service.initialize()
await together_service.generate_embedding(text)
await together_service.generate_embeddings_batch(texts)
await together_service.chat_completion(messages, temperature, max_tokens)
await together_service.generate_questions(context, count, mode, topic)
```

**Configuration:**
- `TOGETHER_API_KEY`: Together AI API key
- `TOGETHER_MODEL`: LLM model name
- `EMBEDDING_MODEL`: Embedding model name

---

### 3. **qdrant_service.py**
Qdrant Cloud vector database service for storing and retrieving embeddings.

**Features:**
- Vector storage and retrieval
- Metadata filtering
- Collection management
- Batch operations

**Key Methods:**
```python
qdrant_service.initialize()
await qdrant_service.upsert_points(texts, embeddings, metadata)
await qdrant_service.search(query_vector, limit, filter_conditions)
await qdrant_service.delete_points(filter_conditions)
await qdrant_service.get_collection_info()
```

**Configuration:**
- `QDRANT_URL`: Qdrant Cloud URL
- `QDRANT_API_KEY`: API key
- `QDRANT_COLLECTION_NAME`: Collection name
- `EMBEDDING_DIMENSIONS`: Vector dimensions

---

### 4. **document_service.py**
PDF extraction and preprocessing using LlamaIndex.

**Features:**
- PDF text extraction with metadata
- File hash computation for deduplication
- Large file handling
- Document validation

**Key Methods:**
```python
document_service.initialize()
await document_service.extract_from_pdf(file_path)
await document_service.extract_from_directory(directory_path)
await document_service.validate_document(file_path)
await document_service.get_document_metadata(file_path)
```

**Configuration:**
- `LLAMAINDEX_USE_FOR_LARGE_PDFS`: Enable for large PDFs
- `LLAMAINDEX_LARGE_PDF_THRESHOLD_MB`: Size threshold

---

### 5. **chunking_service.py**
Text chunking using LlamaIndex SentenceSplitter.

**Features:**
- Sentence-based chunking
- Configurable chunk size and overlap
- Metadata enrichment
- Chunk statistics

**Key Methods:**
```python
chunking_service.initialize()
await chunking_service.chunk_documents(documents)
await chunking_service.chunk_text(text, metadata)
chunking_service.get_chunk_stats(nodes)
await chunking_service.merge_small_chunks(nodes, min_size)
```

**Configuration:**
- `LLAMAINDEX_CHUNK_SIZE`: Chunk size in characters
- `LLAMAINDEX_CHUNK_OVERLAP`: Overlap between chunks

---

### 6. **embedding_service.py**
Embedding generation using LangChain with Together AI.

**Features:**
- Single and batch embedding generation
- Automatic caching
- Similarity computation
- Rate limiting and batching

**Key Methods:**
```python
embedding_service.initialize()
await embedding_service.generate_embedding(text, use_cache)
await embedding_service.generate_embeddings_batch(texts, use_cache)
await embedding_service.compute_similarity(embedding1, embedding2)
```

**Configuration:**
- `TOGETHER_API_KEY`: Together AI API key
- `EMBEDDING_MODEL`: Embedding model
- `EMBEDDING_DIMENSIONS`: Vector dimensions
- `EMBEDDING_BATCH_SIZE`: Batch size for generation

---

### 7. **chat_service.py**
Chat and question generation using LangChain with Together AI.

**Features:**
- Chat completion with context
- Question generation (quiz and practice modes)
- Text summarization
- Prompt templating

**Key Methods:**
```python
chat_service.initialize()
await chat_service.generate_response(messages, temperature, max_tokens)
await chat_service.generate_questions(context, count, mode, topic)
await chat_service.summarize_text(text, max_length)
```

**Configuration:**
- `TOGETHER_API_KEY`: Together AI API key
- `TOGETHER_MODEL`: LLM model name

---

### 8. **rag_orchestrator.py**
Main RAG pipeline coordinator that integrates all services.

**Features:**
- End-to-end document ingestion
- Query and question generation pipeline
- Context retrieval
- System statistics and monitoring

**Key Methods:**
```python
rag_orchestrator.initialize()
await rag_orchestrator.ingest_document(file_path, metadata)
await rag_orchestrator.query_and_generate(query, count, mode, top_k, filter_conditions)
await rag_orchestrator.retrieve_context(query, top_k, filter_conditions)
await rag_orchestrator.get_system_stats()
await rag_orchestrator.delete_document(file_hash)
```

**Pipeline Flow:**
1. Document ingestion → PDF extraction → Chunking → Embedding → Qdrant storage
2. Query → Embedding → Vector search → Context retrieval → Question generation

---

### 9. **celery_service.py**
Background task processing using Celery with Redis.

**Features:**
- Async document ingestion
- Batch embedding generation
- Task status tracking
- Error handling and recovery

**Key Methods:**
```python
celery_service.initialize()
celery_service.submit_ingest_document(file_path, metadata)
celery_service.get_task_status(task_id)
```

**Configuration:**
- `CELERY_BROKER_URL`: Redis URL for task queue
- `CELERY_RESULT_BACKEND`: Redis URL for results
- `CELERY_TASK_SERIALIZER`: Serialization format

---

## Configuration

All services read configuration from environment variables defined in `.env`:

### Required Variables:
```bash
# Together AI
TOGETHER_API_KEY=your_api_key
TOGETHER_MODEL=meta-llama/Llama-3.3-70B-Instruct-Turbo-Free
EMBEDDING_MODEL=togethercomputer/m2-bert-80M-32k-retrieval
EMBEDDING_DIMENSIONS=768

# Qdrant Cloud
QDRANT_URL=your_qdrant_url
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_COLLECTION_NAME=lumina_iq_documents

# Redis Cloud
REDIS_URL=your_redis_url
REDIS_CACHE_DB=0

# LlamaIndex
LLAMAINDEX_CHUNK_SIZE=256
LLAMAINDEX_CHUNK_OVERLAP=50
```

## Usage Example

### Complete RAG Pipeline:

```python
from services.rag_orchestrator import rag_orchestrator
from pathlib import Path

# Initialize
rag_orchestrator.initialize()

# Ingest a document
result = await rag_orchestrator.ingest_document(
    file_path=Path("document.pdf"),
    metadata={"source": "user_upload", "category": "education"}
)

# Generate questions
questions = await rag_orchestrator.query_and_generate(
    query="machine learning basics",
    count=25,
    mode="practice",
    top_k=10,
    use_cache=True
)

print(questions["response"])
```

### Individual Service Usage:

```python
# Generate embeddings
from services.embedding_service import embedding_service

embedding_service.initialize()
embedding = await embedding_service.generate_embedding("sample text")

# Search vectors
from services.qdrant_service import qdrant_service

qdrant_service.initialize()
results = await qdrant_service.search(
    query_vector=embedding,
    limit=5
)

# Cache results
from services.cache_service import cache_service

await cache_service.initialize()
await cache_service.set_json("key", {"data": "value"})
```

## Logging

All services use structured logging with context-rich information:

```python
from utils.logger import get_logger

logger = get_logger("service_name")
logger.info(
    "Operation completed",
    extra={
        "extra_fields": {
            "duration_ms": 100,
            "items_processed": 50
        }
    }
)
```

## Error Handling

Services implement comprehensive error handling with:
- Graceful degradation
- Detailed error logging
- Circuit breaker patterns (where applicable)
- Automatic retries with exponential backoff

## Testing

Run the test suite to verify all services:

```bash
cd backend
python test_services.py
```

This will test:
- Service initialization
- Basic operations
- Integration between services
- Configuration validation

## Performance

The system is optimized for production with:
- Redis caching for 70-90% cache hit rate
- Batch processing for embeddings
- Async operations throughout
- Connection pooling and keep-alive
- Configurable timeouts and limits

## Production Considerations

1. **Scaling**: Each service can be scaled independently
2. **Monitoring**: Use `get_system_stats()` for health checks
3. **Caching**: Tune TTL values based on usage patterns
4. **Rate Limits**: Together AI has rate limits, use batching
5. **Error Recovery**: Implement retry logic for transient failures

## Troubleshooting

### Common Issues:

1. **Redis Connection Failed**
   - Check `REDIS_URL` format
   - Verify network connectivity
   - Ensure Redis is accessible

2. **Qdrant Connection Failed**
   - Verify `QDRANT_URL` and `QDRANT_API_KEY`
   - Check collection exists
   - Verify dimensions match

3. **Together AI Errors**
   - Validate API key
   - Check rate limits
   - Verify model names

4. **Embedding Dimension Mismatch**
   - Ensure `EMBEDDING_DIMENSIONS` matches model output
   - Recreate Qdrant collection if changed

## Contributing

When adding new services:
1. Follow the singleton pattern
2. Implement `initialize()` method
3. Add comprehensive logging
4. Handle errors gracefully
5. Update this README
6. Add tests to `test_services.py`

## License

This is proprietary software for Lumina IQ.
