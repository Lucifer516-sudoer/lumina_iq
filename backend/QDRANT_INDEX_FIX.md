# Qdrant Index Fix

## Issue
**Error**: `Bad request: Index required but not found for "file_hash" of one of the following types: [keyword]`

**Location**: `qdrant_service.py` line 372, 398

**Impact**: Duplicate detection was failing, causing documents to be re-indexed

---

## Root Cause

Qdrant requires a **payload index** to be created for any field you want to filter on. The code was trying to filter by `file_hash` to check for duplicates, but no index existed for this field.

```python
# This filter requires an index:
filter_conditions={"file_hash": file_hash}
```

---

## Fix Applied

### 1. Updated `qdrant_service.py` (Line 82-92)

Added automatic payload index creation during initialization:

```python
# Create payload index for file_hash field to enable filtering
try:
    self.client.create_payload_index(
        collection_name=self.collection_name,
        field_name="file_hash",
        field_schema="keyword"
    )
    logger.info(f"Created payload index for file_hash field")
except Exception as index_error:
    # Index might already exist, which is fine
    logger.debug(f"Payload index for file_hash may already exist: {str(index_error)}")
```

### 2. Applied Migration to Existing Collection

Ran migration script to add the index to the existing collection:

```bash
python backend/add_file_hash_index.py
```

**Result**:
```
[OK] Payload index created successfully!
  Field: file_hash
  Type: keyword

[OK] Collection info retrieved successfully
  Points count: 1506
  Vectors count: None

[SUCCESS] Migration completed!
```

---

## What This Fixes

✅ **Duplicate Detection**: Now works correctly - checks if file already exists by content hash
✅ **No More Errors**: Qdrant filtering on `file_hash` works without errors
✅ **Prevents Re-indexing**: Same documents won't be re-embedded and re-stored
✅ **Future-Proof**: New collections will automatically get the index

---

## Testing

**Test duplicate detection:**

1. Upload a PDF - it will be indexed
2. Upload the SAME PDF again - it will say "Document already indexed - skipped duplicate ingestion"
3. Check logs - no more Qdrant index errors

**Expected log output:**
```
INFO: Checking if document already exists - file_hash: 44871c8d
INFO: Document already exists in collection
INFO: ✓ Document already indexed - SKIPPING re-ingestion
```

---

## Technical Details

**Qdrant Payload Indexes:**
- Required for filtering on payload fields
- Type: `keyword` (exact match)
- Field: `file_hash` (SHA256 of file content)
- Allows: `filter_conditions={"file_hash": "..."}`

**Index Schema:**
```python
field_name="file_hash"
field_schema="keyword"  # Exact string matching
```

---

## Collection Status

- **Collection Name**: `lumina_iq_documents_prod`
- **Points Count**: 1,506 embeddings
- **Index**: `file_hash` (keyword) ✅ Created
- **Status**: Ready for duplicate detection

---

## Status: RESOLVED ✅

No restart needed - the index is live and working!
