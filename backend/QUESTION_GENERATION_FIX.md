# Question Generation KeyError Fix

## Issue
**Error**: `KeyError: 'num'`

**Location**: 
- `services/chat_service.py` line 236
- `services/together_service.py` line 238

**Impact**: Question generation was failing with 500 errors

---

## Root Cause

Python string `.format()` method was trying to substitute `{num}` as a variable, but `{num}` was meant to be literal text in the AI prompt (showing the format the AI should use).

**Incorrect Code**:
```python
user_prompt = """...generate {count} questions.
Format each question as:
Q{num}: [Question]
...
Context:
{context}
..."""

# Later:
formatted_prompt = user_prompt.format(
    count=count,
    context=context,
    topic_instruction=topic_instruction
)
# ❌ ERROR: 'num' not provided to format()!
```

---

## Fix Applied

Escaped `{num}` by doubling the braces to `{{num}}` - this tells Python to treat it as literal text, not a format variable.

### Files Fixed:

**1. `services/chat_service.py` (Lines 161, 185)**:
```python
# BEFORE (causing error):
Q{num}: [Question]

# AFTER (fixed):
Q{{num}}: [Question]
```

**2. `services/together_service.py` (Line 238)**:
```python
# BEFORE (causing error):
Q{num}: [Question]

# AFTER (fixed):
Q{{num}}: [Question]
```

---

## How Double Braces Work

```python
# Single braces = format variable (substituted)
"Hello {name}".format(name="World")  → "Hello World"

# Double braces = literal braces (not substituted)
"Q{{num}}: Question".format()  → "Q{num}: Question"

# Mixed example:
"Generate {count} questions as Q{{num}}: ...".format(count=5)
→ "Generate 5 questions as Q{num}: ..."
```

---

## What This Fixes

✅ **Question Generation**: Now works for both quiz and practice modes
✅ **Chat Endpoint**: No more 500 errors when asking questions
✅ **AI Prompt**: Correctly shows format example to the AI

---

## Testing

**Test the fix:**

1. Start backend:
   ```bash
   uv run backend/run.py
   ```

2. Send a chat message requesting questions:
   ```
   "Generate 5 practice questions about this topic"
   ```

3. Expected response:
   ```
   Q1: What are the main concepts...?
   Q2: How does the author explain...?
   Q3: Why is this important...?
   ...
   ```

---

## API Endpoints Affected

✅ Fixed:
- `POST /api/chat/` - General chat with question requests
- `POST /api/chat/generate-questions` - Direct question generation

---

## Status: RESOLVED ✅

Question generation now works without KeyError!
