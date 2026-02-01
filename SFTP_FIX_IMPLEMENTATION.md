# SFTP Connection Timeout Fix - Implementation Guide

## Problem
Videos process successfully but fail at SFTP upload due to stale connections after 60-90 minutes of processing.

## Solution
Implement "Just-In-Time Connection" - connect to SFTP only when needed, right before upload.

---

## Changes Required

### File 1: `main_hourly.py`

#### Change 1: Remove SFTP client from function signature
**Line 124:**
```python
# OLD:
def process_entry_with_canary(entry, proxy_manager, seafile_client, sftp_client):

# NEW:
def process_entry_with_canary(entry, proxy_manager, seafile_client):
```

#### Change 2: Add SFTP connection right before upload
**Replace lines 244-269 with:**

```python
        # Upload to SFTP
        logger.info("Step 5/5: Uploading to SFTP...")
        sftp_results = {}
        sftp_client = None

        # Use saved files for SFTP upload
        files_to_upload = [f for f in saved_files.values() if Path(f).exists()]
        
        if files_to_upload:
            try:
                # Initialize SFTP client with fresh connection
                logger.info("Connecting to SFTP server...")
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
                
                # Upload all files to flat incoming directory (no subfolders)
                upload_results_sftp = sftp_client.upload_files(files_to_upload, subfolder=None)
                
                for filename, success in upload_results_sftp.items():
                    if success:
                        logger.info(f"  ✅ Uploaded to SFTP: {filename}")
                        sftp_results[filename] = filename
                    else:
                        logger.warning(f"  ❌ Failed to upload to SFTP: {filename}")
                
                # Clean up local files after successful upload
                for f in files_to_upload:
                    try:
                        os.unlink(f)
                    except:
                        pass
                        
            except Exception as e:
                logger.error(f"  ❌ Error during SFTP upload: {e}")
            
            finally:
                # Always disconnect SFTP after upload attempt
                if sftp_client:
                    try:
                        sftp_client.disconnect()
                        logger.info("SFTP connection closed")
                    except Exception as e:
                        logger.warning(f"Error closing SFTP connection: {e}")
```

#### Change 3: Remove early SFTP initialization
**Delete lines 383-396:**
```python
# DELETE THIS ENTIRE BLOCK:
    # Initialize SFTP client
    logger.info("Initializing SFTP client...")
    try:
        sftp_client = SFTPClient(
            host=SFTP_HOST,
            port=SFTP_PORT,
            username=SFTP_USERNAME,
            password=SFTP_PASSWORD,
            upload_path=SFTP_UPLOAD_PATH
        )
        logger.info("✅ SFTP client initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize SFTP: {e}")
        return False
```

#### Change 4: Update function call
**Line 435:**
```python
# OLD:
result = process_entry_with_canary(entry, proxy_manager, seafile_client, sftp_client)

# NEW:
result = process_entry_with_canary(entry, proxy_manager, seafile_client)
```

---

## Testing Checklist

- [ ] Test with short meeting (< 10 minutes)
- [ ] Test with long meeting (> 60 minutes)
- [ ] Test with multiple meetings in sequence
- [ ] Verify SFTP connection logs show "connected" and "closed"
- [ ] Verify files upload successfully
- [ ] Test SFTP connection failure handling
- [ ] Check retry logic works correctly

---

## Rollback Plan

If issues occur, revert changes:
1. Restore `sftp_client` parameter to function signature
2. Restore early SFTP initialization (lines 383-396)
3. Restore original SFTP upload code (lines 244-269)
4. Restore function call with `sftp_client` parameter

---

## Expected Log Output

**Successful processing:**
```
[2026-01-16 10:00:00] Step 1/4: Downloading video...
[2026-01-16 10:05:00] Step 2/4: Extracting audio...
[2026-01-16 10:07:00] Step 3/4: Transcribing with Canary + Diarization...
[2026-01-16 11:07:00] Step 4/5: Uploading to Seafile...
[2026-01-16 11:08:00] Step 5/5: Uploading to SFTP...
[2026-01-16 11:08:01] Connecting to SFTP server...
[2026-01-16 11:08:02] ✅ SFTP connected
[2026-01-16 11:08:05] ✅ Uploaded to SFTP: meeting.json
[2026-01-16 11:08:06] ✅ Uploaded to SFTP: meeting.csv
[2026-01-16 11:08:07] ✅ Uploaded to SFTP: meeting.txt
[2026-01-16 11:08:08] SFTP connection closed
[2026-01-16 11:08:08] ✅ Entry processed successfully!
```

**Connection age comparison:**
- **Before:** Connection open for 60-90+ minutes → TIMEOUT
- **After:** Connection open for 5-10 seconds → SUCCESS

---

## Benefits

1. ✅ **Eliminates stale connections** - Fresh connection every time
2. ✅ **Reduces resource usage** - Connection only open when needed
3. ✅ **More reliable** - No dependency on keepalive or server timeouts
4. ✅ **Better error handling** - Clear connection lifecycle
5. ✅ **Easier debugging** - Connection timing visible in logs

---

## Notes

- This change only affects `main_hourly.py`
- Other scripts using `SFTPClient` are not affected
- No configuration changes needed
- Backward compatible with existing `SFTPClient` class

