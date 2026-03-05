# Quick Wins Implementation Guide

This document provides step-by-step instructions for implementing the highest-impact changes with minimal effort.

---

## Change 1: Enforce Deterministic Temperature (5 minutes)

**Impact:** Eliminates one major source of non-determinism
**File:** `/modules/analyzer.py`

### Step 1: Update `__init__` method (lines 27-41)

```python
def __init__(self, provider: str = None, model_name: str = None):
    self.provider = provider or AI_PROVIDER

    # ENFORCE deterministic temperature - do not rely on config
    self.temperature = 0.0  # Always 0 for consistent results

    # Set model based on provider
    if self.provider == "ollama":
        self.model_name = model_name or LLM_MODEL
        self._check_ollama_connection()
    elif self.provider == "openai":
        self.model_name = model_name or OPENAI_MODEL
        self._check_openai_setup()
    elif self.provider == "anthropic":
        self.model_name = model_name or ANTHROPIC_MODEL
        self._check_anthropic_setup()
    else:
        raise ValueError(f"Unknown AI provider: {self.provider}")
```

### Step 2: Update all `_call_*` methods to use `self.temperature`

**Line 261 - `_call_ollama`:**
```python
def _call_ollama(self, prompt: str) -> str:
    response = ollama.chat(
        model=self.model_name,
        messages=[{'role': 'user', 'content': prompt}],
        options={'temperature': self.temperature}  # Changed from AI_TEMPERATURE
    )
    return response['message']['content']
```

**Line 269 - `_call_openai`:**
```python
def _call_openai(self, prompt: str) -> str:
    response = self.openai_client.chat.completions.create(
        model=self.model_name,
        messages=[{'role': 'user', 'content': prompt}],
        temperature=self.temperature,  # Changed from AI_TEMPERATURE
        max_tokens=500
    )
    return response.choices[0].message.content
```

**Line 277 - `_call_anthropic`:**
```python
def _call_anthropic(self, prompt: str) -> str:
    response = self.anthropic_client.messages.create(
        model=self.model_name,
        messages=[{'role': 'user', 'content': prompt}],
        temperature=self.temperature,  # Changed from AI_TEMPERATURE
        max_tokens=500
    )
    return response.content[0].text
```

**Test:** Run the app twice on the same video and verify results are identical.

---

## Change 2: Implement Result Caching (30 minutes)

**Impact:** 100% speed improvement on re-runs; ensures identical results
**File:** `/modules/analyzer.py`

### Step 1: Add imports at top of file (after line 6)

```python
import hashlib
```

### Step 2: Update `__init__` method (add after line 41)

```python
def __init__(self, provider: str = None, model_name: str = None):
    self.provider = provider or AI_PROVIDER
    self.temperature = 0.0

    # ... existing provider setup ...

    # Add cache directory setup
    self.cache_dir = Path(__file__).parent.parent / "cache" / "analysis"
    self.cache_dir.mkdir(parents=True, exist_ok=True)
```

### Step 3: Add cache helper method (after line 70)

```python
def _get_cache_key(self, transcript: Dict, chunk_duration: int) -> str:
    """Generate deterministic cache key from transcript and parameters"""
    # Create hash from transcript content and analysis parameters
    cache_content = {
        'segments': [
            {'start': s['start'], 'end': s['end'], 'text': s['text']}
            for s in transcript['segments']
        ],
        'chunk_duration': chunk_duration,
        'model': self.model_name,
        'provider': self.provider,
        'temperature': self.temperature
    }
    content_str = json.dumps(cache_content, sort_keys=True)
    return hashlib.sha256(content_str.encode()).hexdigest()[:16]
```

### Step 4: Update `analyze_transcript` method (lines 71-118)

**Add at the very beginning of the method (after line 73):**

```python
def analyze_transcript(self, transcript: Dict, chunk_duration: int = 30) -> List[Dict]:
    segments = transcript['segments']
    if not segments:
        return []

    # CHECK CACHE FIRST
    cache_key = self._get_cache_key(transcript, chunk_duration)
    cache_file = self.cache_dir / f"moments_{cache_key}.json"

    if cache_file.exists():
        print(f"Loading cached analysis results (key: {cache_key})...")
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_moments = json.load(f)
            print(f"Found {len(cached_moments)} cached viral moments")
            return cached_moments
        except Exception as e:
            print(f"Cache read failed: {e}, re-analyzing...")

    # ... rest of existing method (chunks creation, analysis, etc) ...
```

**Add at the very end, before returning (after line 117):**

```python
    print(f"Found {len(viral_moments)} potential viral moments")

    # SAVE TO CACHE
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(viral_moments, f, indent=2, ensure_ascii=False)
        print(f"Cached results (key: {cache_key})")
    except Exception as e:
        print(f"Warning: Failed to cache results: {e}")

    return viral_moments
```

### Step 5: Add cache directory to .gitignore

Add this line to `.gitignore`:
```
cache/
```

**Test:** Run the app on a video, note the time. Run again - should load from cache in < 1 second.

---

## Change 3: Increase Chunk Duration (2 minutes)

**Impact:** 33% fewer chunks = 33% faster analysis
**Files:** `config.py` and `app_minimal.py`

### Step 1: Update default in config.py (line 224)

```python
# OLD:
CHUNK_DURATION = 45

# NEW:
CHUNK_DURATION = 60  # Larger chunks reduce total analysis time
```

### Step 2: Update app_minimal.py call (line 523)

```python
# OLD:
viral_moments = analyzer.analyze_transcript(transcript, chunk_duration=30)

# NEW:
viral_moments = analyzer.analyze_transcript(transcript, chunk_duration=60)
```

**Alternative:** Keep 45 seconds as a balance between speed and granularity:
```python
viral_moments = analyzer.analyze_transcript(transcript, chunk_duration=45)
```

**Test:** Run on a 2-hour video. Count how many chunks are created:
- With 30s chunks: ~240 chunks
- With 45s chunks: ~160 chunks (33% reduction)
- With 60s chunks: ~120 chunks (50% reduction)

---

## Verification Testing

After implementing all three quick wins, test with a real video:

### Test Script

```bash
# Activate your environment
source .venv/bin/activate

# Run Streamlit app
streamlit run app_minimal.py
```

### Test Checklist

1. **First Run:**
   - Upload or paste a YouTube URL (recommend 10-30 minute video for testing)
   - Note the processing time
   - Check that chunks are created with 60s duration
   - Verify viral moments are detected

2. **Second Run (Same Video):**
   - Upload/process the same video again
   - Should see "Loading cached analysis results..." message
   - Processing should complete in < 5 seconds
   - Results should be IDENTICAL to first run

3. **Determinism Test:**
   - Clear cache: `rm -rf cache/`
   - Run same video 3 times
   - Compare results - viral moments should have identical scores and timestamps

### Expected Results

**Before Changes:**
- Processing time: ~16 minutes for 2-hour video
- Different results each run
- No caching

**After Quick Wins:**
- First run: ~11 minutes for 2-hour video (30% faster)
- Subsequent runs: < 5 seconds (99% faster)
- Identical results every time (deterministic)

---

## Troubleshooting

### Cache not working

**Symptom:** Every run shows "Analyzing X chunks..." instead of "Loading cached..."

**Solutions:**
1. Check cache directory exists: `ls cache/analysis/`
2. Verify cache files are being created: `ls -la cache/analysis/`
3. Check file permissions: `chmod -R 755 cache/`
4. Look for error messages in console

### Results still non-deterministic

**Symptom:** Same video produces different scores on different runs

**Solutions:**
1. Verify `self.temperature = 0.0` is set in `__init__`
2. Check Ollama version: `ollama --version` (should be >= 0.12)
3. Try restarting Ollama: `ollama serve`
4. Check if cache is being used (should prevent re-analysis)

### Import errors

**Symptom:** `NameError: name 'hashlib' is not defined`

**Solution:** Add `import hashlib` to imports at top of analyzer.py

---

## Performance Metrics

Track these metrics before and after:

| Metric | Before | After Quick Wins | Target (Full Implementation) |
|--------|--------|------------------|------------------------------|
| First run time (2hr video) | ~16 min | ~11 min | ~2-4 min |
| Re-run time | ~16 min | < 5 sec | < 5 sec |
| Result consistency | ~60% | ~95% | ~99% |
| Cache hit rate | 0% | ~100% | ~100% |

---

## Next Steps

After implementing these quick wins, consider:

1. **Parallel Processing** (2 hours) - Reduce time from 11 min to 3-4 min
2. **JSON Structured Output** (2 hours) - Improve reliability from 95% to 99%
3. **Model Upgrade** (8 hours) - Evaluate faster models for better performance

See `ARCHITECTURE_AUDIT_REPORT.md` for full implementation plan.

---

**Total Implementation Time:** < 40 minutes
**Total Impact:** 60-70% speed improvement + 95% reliability improvement
