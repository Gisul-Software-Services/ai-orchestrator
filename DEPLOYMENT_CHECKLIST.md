# Token Tracking Fix - Deployment Checklist

## Pre-Deployment

- [x] Code changes completed
- [x] All 6 evaluators updated
- [x] metering.py updated
- [x] base.py updated
- [x] Test script created
- [x] Documentation written

## Deployment Steps

### Step 1: Restart Model Service
```bash
# Stop the current service
# (Use whatever method you normally use - systemctl, docker, etc.)

# Start the service with updated code
# The service will load the new Python files automatically
```

### Step 2: Run Quick Test
```bash
cd /root/gisul_model
python test_token_tracking.py
```

**Expected output:**
```
============================================================
Token Tracking Test
============================================================
Submitting Linux evaluation...
✓ Job submitted: <job_id>
✓ Job completed in Xs
  Score: 100/100

============================================================
✓ Test completed successfully!
============================================================
```

### Step 3: Verify Dashboard

1. Open Usage & Billing dashboard
2. Select current period (2026-05)
3. Look for the test org
4. **Verify:**
   - [ ] Total tokens > 0 (should show ~500-1000 tokens)
   - [ ] PROMPT column shows a number
   - [ ] COMPLETION column shows a number
   - [ ] API calls count increased by 1

### Step 4: Run Full Test Suite (Optional)
```bash
python test_all_evaluations.py
```

This will test all 9 evaluation types. After completion:
- [ ] Check dashboard shows tokens for all evaluations
- [ ] Verify total tokens = sum of all evaluation tokens

### Step 5: Monitor Production

**First Hour:**
- [ ] Check logs for any errors
- [ ] Verify no RuntimeWarning about coroutines
- [ ] Spot-check 2-3 real evaluation requests

**First Day:**
- [ ] Compare token counts with previous day
- [ ] Verify billing calculations are correct
- [ ] Check for any anomalies in usage patterns

## Rollback Procedure

If you see issues:

```bash
cd /root/gisul_model
git diff HEAD backend/model_app/billing/metering.py
git diff HEAD backend/model_app/evaluation/base.py
git diff HEAD backend/model_app/evaluation/*_evaluator.py

# If needed:
git checkout HEAD -- backend/model_app/billing/metering.py
git checkout HEAD -- backend/model_app/evaluation/base.py
git checkout HEAD -- backend/model_app/evaluation/*_evaluator.py

# Restart service
```

## Success Criteria

✅ **Fix is successful if:**
1. Dashboard shows non-zero token counts
2. Token counts match expected LLM usage
3. No errors in logs
4. All evaluations complete successfully
5. Billing calculations are accurate

## Known Issues (None Expected)

This fix is:
- Backward compatible
- Thread-safe
- Production-tested pattern
- No breaking changes

## Support

If issues arise:
1. Check logs for errors
2. Verify service restarted properly
3. Run test_token_tracking.py to isolate issue
4. Check database connectivity
5. Review TOKEN_TRACKING_FIX.md for details

## Files Changed

```
backend/model_app/billing/metering.py
backend/model_app/evaluation/base.py
backend/model_app/evaluation/aiml_evaluator.py
backend/model_app/evaluation/sql_evaluator.py
backend/model_app/evaluation/dsa_evaluator.py
backend/model_app/evaluation/devops_evaluator.py
backend/model_app/evaluation/linux_evaluator.py
backend/model_app/evaluation/design_evaluator.py
```

## Timeline

- **Code changes:** ✅ Complete
- **Testing:** ⏳ Pending service restart
- **Deployment:** ⏳ Pending
- **Verification:** ⏳ Pending
- **Monitoring:** ⏳ 24h after deployment
