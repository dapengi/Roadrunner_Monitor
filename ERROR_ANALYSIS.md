# Roadrunner Monitor - Error Analysis Report

Generated: 2026-01-16

## Summary

I've analyzed the codebase for potential errors, bugs, and issues. Overall, the code is **well-structured with good error handling**, but I found several issues that should be addressed:

---

## 🔴 Critical Issues

### 1. **Proxy Fallback Logic Inconsistency**
**Location:** `modules/web_scraper.py:57`

**Issue:** The warning message says "will retry with direct connection" but the code is designed to NEVER use direct connections (to protect home IP). This is misleading.

```python
# Line 57
logger.warning("⚠️ Failed to get new proxy IP, will retry with direct connection")
```

**Impact:** Confusing log messages that don't match actual behavior.

**Fix:** Change message to: `"⚠️ Failed to get new proxy IP, will retry with current proxy"`

---

### 2. **Potential Exception Swallowing in Proxy Manager**
**Location:** `modules/proxy_manager.py:130-131`

**Issue:** When checking direct IP fails, the exception is caught but the code continues, potentially allowing a direct IP to pass validation.

```python
except Exception as direct_check_error:
    logger.warning(f"Could not verify direct IP for comparison: {direct_check_error}")
    # Code continues without knowing if proxy is actually working
```

**Impact:** Could allow direct IP leakage if the verification check fails.

**Fix:** Should fail-safe by raising an exception if direct IP check fails.

---

### 3. **Unreachable Return Statement**
**Location:** `modules/web_scraper.py:67`

**Issue:** The function has `return None` after the loop, but line 65 raises an exception, making line 67 unreachable.

```python
else:
    logger.error(f"All {max_retries} attempts failed for URL: {url}")
    raise  # Line 65
    
return None  # Line 67 - UNREACHABLE
```

**Impact:** Dead code that will never execute.

**Fix:** Remove the unreachable `return None` statement.

---

## ⚠️ Medium Priority Issues

### 4. **Timestamp Parsing Assumes MM:SS Format**
**Location:** `modules/transcript_pipeline_canary.py:69-73`

**Issue:** The timestamp parser assumes format is always `MM:SS`, but doesn't handle hours (`HH:MM:SS`) or edge cases.

```python
start_parts = times[0].split(':')
end_parts = times[1].split(':')

start_seconds = int(start_parts[0]) * 60 + int(start_parts[1])  # Assumes 2 parts
end_seconds = int(end_parts[0]) * 60 + int(end_parts[1])
```

**Impact:** Will crash on meetings longer than 60 minutes with `IndexError` or incorrect time calculations.

**Fix:** Add support for `HH:MM:SS` format and validate array length.

---

### 5. **Missing TODO Items**
**Location:** `modules/canary_transcription.py:160, 195`

**Issue:** Two TODO comments indicate incomplete features:
- Line 160: "TODO: Add VAD-based segmentation"
- Line 195: "TODO: Implement VAD-based segmentation for better timestamps"

**Impact:** Canary transcription returns single segment instead of properly segmented output, reducing transcript quality.

**Fix:** Implement VAD (Voice Activity Detection) segmentation or document as known limitation.

---

### 6. **File Size Check Uses Magic Number**
**Location:** Multiple files (e.g., `modules/video_processor.py:216, 280`)

**Issue:** File size validation uses hardcoded `1024` bytes without explanation.

```python
if os.path.exists(possible_file) and os.path.getsize(possible_file) > 1024:
```

**Impact:** Files between 0-1KB are considered invalid, which might be too aggressive.

**Fix:** Define as named constant (e.g., `MIN_VALID_FILE_SIZE = 1024`) with comment explaining rationale.

---

## 💡 Low Priority Issues

### 7. **Inconsistent Error Handling in Caption Downloader**
**Location:** `closedcaptioning/caption_downloader.py:51-53`

**Issue:** Uses `print()` instead of `logger` for error messages, inconsistent with rest of codebase.

```python
except Exception as e:
    print(f"❌ Webhook error: {e}")
    return False
```

**Impact:** Errors won't be captured in log files, only console output.

**Fix:** Replace `print()` with `logger.error()` throughout caption_downloader.py.

---

### 8. **Broad Exception Catching**
**Location:** Multiple locations (e.g., `main_hourly.py:329`)

**Issue:** Many functions catch generic `Exception` which can hide specific errors.

```python
except Exception as e:
    logger.error(f"Error processing entry: {e}")
```

**Impact:** Makes debugging harder; specific exceptions (like `KeyError`, `ValueError`) are treated the same.

**Fix:** Catch specific exceptions where possible, or at least log full traceback.

---

### 9. **Potential Race Condition in File Cleanup**
**Location:** `modules/transcript_pipeline.py:229-233`

**Issue:** Audio file cleanup happens in try/except but doesn't check if file still exists.

```python
try:
    os.remove(audio_path)
except Exception as e:
    logger.warning(f"Could not remove audio file: {e}")
```

**Impact:** If file was already deleted, generates unnecessary warning.

**Fix:** Check `os.path.exists(audio_path)` before attempting removal.

---

## ✅ Good Practices Found

1. **Comprehensive retry logic** with exponential backoff
2. **Proper error notifications** via Pushover
3. **Good logging** throughout the codebase
4. **Proxy protection** to avoid exposing home IP
5. **File validation** before processing
6. **Connection keepalive** for SFTP to prevent timeouts
7. **Graceful degradation** when optional features fail

---

## Recommendations

### Immediate Actions:
1. Fix the misleading proxy fallback message (Issue #1)
2. Fix proxy IP validation exception handling (Issue #2)
3. Remove unreachable code (Issue #3)

### Short-term:
4. Add HH:MM:SS timestamp support (Issue #4)
5. Implement or document VAD segmentation (Issue #5)
6. Standardize logging in caption_downloader (Issue #7)

### Long-term:
7. Define file size constants (Issue #6)
8. Refine exception handling to be more specific (Issue #8)
9. Add file existence checks before cleanup (Issue #9)

---

## Testing Recommendations

1. **Test with long meetings** (>60 minutes) to verify timestamp parsing
2. **Test proxy failure scenarios** to ensure no IP leakage
3. **Test file cleanup** with missing/deleted files
4. **Load test** with multiple simultaneous meetings
5. **Test error recovery** by simulating network failures

---

**Overall Assessment:** The codebase is production-ready with good error handling, but the issues above should be addressed to improve robustness and maintainability.

---

# 🔥 CRITICAL: SFTP Connection Timeout Issue

## Problem Description

**User Report:** Videos process successfully (download, transcription complete) but then fail at SFTP upload stage due to lost connection.

## Root Cause Analysis

### Timeline of Processing:
1. **SFTP client initialized** at start of `main_hourly.py` (line 386)
2. **Video download** - can take 5-30+ minutes for long meetings
3. **Audio extraction** - 1-2 minutes
4. **Canary transcription** - 10-60+ minutes depending on meeting length
5. **Seafile upload** - 1-5 minutes
6. **SFTP upload** - Connection is now STALE (60-90+ minutes later)

### Current Keepalive Configuration:
**Location:** `modules/sftp_client.py:98`

```python
transport.set_keepalive(60)  # Sends keepalive every 60 seconds
```

### Why It's Failing:

1. **SSH keepalive only works if transport is active** - During long transcription, the Python process isn't using the SFTP connection at all
2. **Server-side timeout** - Many SFTP servers have idle timeouts (typically 10-30 minutes) that override client keepalive
3. **NAT/Firewall timeout** - Network devices between client and server may drop "idle" connections
4. **Single connection reuse** - The same SFTP client instance is reused across the entire hourly run, potentially staying open for hours

## Current Mitigation (Insufficient):

The code has `ensure_connection()` that checks and reconnects:
- Called before each `upload_file()` operation
- Uses `getcwd()` to test connection liveness
- **Problem:** By the time it detects the dead connection and reconnects, the upload may have already started failing

---

## 🔧 Recommended Solutions

### Solution 1: **Just-In-Time Connection** (RECOMMENDED - Easiest)

**Concept:** Don't connect to SFTP until right before upload, then disconnect immediately after.

**Changes needed:**

1. **Remove early SFTP initialization** in `main_hourly.py`
2. **Connect only when needed** - right before SFTP upload step
3. **Disconnect after upload** - clean up connection

**Pros:**
- ✅ Simple to implement
- ✅ Connection only open for ~1-2 minutes
- ✅ No stale connections
- ✅ Works with any server timeout settings

**Cons:**
- ❌ Slight overhead of connecting each time (negligible)

---

### Solution 2: **Connection Refresh Before Upload** (GOOD - More Robust)

**Concept:** Force disconnect and reconnect right before SFTP upload step.

**Changes needed:**

1. Add explicit reconnection before SFTP upload in `main_hourly.py:244`
2. Keep existing `ensure_connection()` as backup

**Pros:**
- ✅ Guarantees fresh connection for upload
- ✅ Minimal code changes
- ✅ Keeps existing error handling

**Cons:**
- ❌ Still maintains connection during processing (wastes resources)

---

### Solution 3: **Background Keepalive Thread** (COMPLEX - Overkill)

**Concept:** Run a background thread that periodically performs SFTP operations to keep connection alive.

**Pros:**
- ✅ Maintains persistent connection

**Cons:**
- ❌ Complex implementation
- ❌ May not work with all firewalls
- ❌ Wastes resources
- ❌ Not recommended for this use case

---

## 📋 Implementation Plan (Solution 1 - Recommended)

### Step 1: Modify `main_hourly.py`

**Remove early SFTP initialization:**
```python
# REMOVE lines 383-396 (early SFTP init)
```

**Add SFTP connection right before upload:**
```python
# At line 244, BEFORE "Upload to SFTP" step:
logger.info("Step 5/5: Uploading to SFTP...")

# Initialize SFTP client with fresh connection
logger.info("Connecting to SFTP server...")
try:
    sftp_client = SFTPClient(
        host=SFTP_HOST,
        port=SFTP_PORT,
        username=SFTP_USERNAME,
        password=SFTP_PASSWORD,
        upload_path=SFTP_UPLOAD_PATH
    )
    if not sftp_client.connect():
        raise Exception("Failed to connect to SFTP server")
    logger.info("✅ SFTP connected")
except Exception as e:
    logger.error(f"❌ Failed to connect to SFTP: {e}")
    # Handle failure with retry logic
    should_mark, is_max = handle_processing_failure(
        entry_link, "SFTP Connection Failed", committee_name, meeting_date_str, meeting_time_str)
    if should_mark:
        write_processed_entry(entry_link)
    return None
```

**Add cleanup after upload:**
```python
# After SFTP upload completes (around line 269):
finally:
    # Always disconnect SFTP after upload
    try:
        sftp_client.disconnect()
        logger.info("SFTP connection closed")
    except:
        pass
```

### Step 2: Update `process_entry_with_canary()` signature

Change from:
```python
def process_entry_with_canary(entry, proxy_manager, seafile_client, sftp_client):
```

To:
```python
def process_entry_with_canary(entry, proxy_manager, seafile_client):
```

Remove `sftp_client` parameter since we'll create it inside the function.

### Step 3: Update function calls

In `main_hourly.py:435`, change:
```python
result = process_entry_with_canary(entry, proxy_manager, seafile_client, sftp_client)
```

To:
```python
result = process_entry_with_canary(entry, proxy_manager, seafile_client)
```

---

## 🧪 Testing Plan

1. **Test with short meeting** (~10 min) - should work as before
2. **Test with long meeting** (~60+ min) - verify SFTP upload succeeds
3. **Test with multiple meetings** - verify each gets fresh connection
4. **Test SFTP failure** - verify retry logic works correctly
5. **Monitor logs** - check connection timing and cleanup

---

## 📊 Expected Results

**Before:**
```
[00:00] SFTP client initialized
[05:00] Video downloaded
[07:00] Audio extracted
[67:00] Transcription complete
[68:00] Seafile upload complete
[68:01] SFTP upload FAILED - connection timeout
```

**After:**
```
[00:00] Processing started
[05:00] Video downloaded
[07:00] Audio extracted
[67:00] Transcription complete
[68:00] Seafile upload complete
[68:01] SFTP client initialized (fresh connection)
[68:02] SFTP upload SUCCESS
[68:03] SFTP connection closed
```

---

## 🎯 Additional Improvements

### 1. Add Connection Timeout Logging
Track how long SFTP connection has been open:

```python
self.connection_time = None  # Add to __init__

# In connect():
self.connection_time = time.time()

# In upload_file():
if self.connection_time:
    age = time.time() - self.connection_time
    logger.info(f"SFTP connection age: {age:.1f}s")
```

### 2. Add Retry Logic for SFTP Connection
If initial connection fails, retry 2-3 times before giving up.

### 3. Consider Connection Pooling (Future)
For processing multiple meetings simultaneously, implement connection pooling.

---

## 🚨 Migration Notes

- **Backward compatible:** Changes don't affect other scripts using `SFTPClient`
- **No config changes needed:** Uses existing SFTP credentials
- **Minimal risk:** Only changes when connection is established
- **Easy rollback:** Can revert to old behavior if issues arise

---

**Recommendation:** Implement Solution 1 (Just-In-Time Connection) immediately. This is the cleanest, most reliable solution for the current architecture.

