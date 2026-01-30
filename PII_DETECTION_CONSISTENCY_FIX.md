# PII Detection Consistency Fix

## Issue
PII detection showed an inconsistency where the HuggingFace NER API response contained certain entities, but those same entities were not visible in the "All Detections" list in the UI.

## Root Cause
The PII detector was using a **whitelist filter** that only included specific entity types:
- `PERSON`, `ORG`, `LOC`, `MISC`, `DATE`

However, the NER model (`dslim/bert-base-NER`) can return additional entity types:
- `B-PER`, `I-PER` (person name begin/inside)
- `B-ORG`, `I-ORG` (organization begin/inside)
- `B-LOC`, `I-LOC` (location begin/inside)
- `GPE` (geo-political entity)
- And others

This caused entities detected by the NER API to be dropped during processing, creating a mismatch between the raw API response and the processed detections.

## Solution

### Changes to `pii_detector.py`

1. **Expanded Entity Type Support** (line 40-58)
   - Updated `PII_RISK_LEVELS` to include all NER entity type variations
   - Added support for B-/I- prefixed entity types (BIO tagging scheme)
   - Added GPE (geo-political entity) support

2. **Removed Whitelist Filter** (line 103-107)
   - Changed from filtering only whitelisted entity types to including ALL entities from NER
   - Added confidence score threshold (≥70%) to filter out low-confidence predictions
   - This ensures consistency: if it's in the raw NER response, it's in the detections

### Changes to `static/main.js`

1. **Enhanced UI Documentation** (line 693-704)
   - Added clarifying note that explains the confidence threshold filtering
   - Shows confidence score (%) for each detected item
   - Explicitly states that all raw NER entities are visible in the "NER API Response" section

## Impact

✅ **Consistency**: What users see in the raw NER API response now matches what appears in the detected items list (minus items below 70% confidence)

✅ **Transparency**: Users can see the confidence score for each detection

✅ **Completeness**: All entity types from the NER model are now captured and displayed

✅ **Better Audit Trail**: The comprehensive entity detection improves compliance audit visibility

## Risk Level Classification

Entity types are classified by risk:

| Risk Level | Entity Types |
|-----------|-------------|
| HIGH | email, phone, ssn, credit_card, PERSON, B-PER, I-PER |
| MEDIUM | ipv4, DATE, ORG, B-ORG, I-ORG, B-LOC, I-LOC, LOCATION, GPE, B-GPE, I-GPE |
| LOW | MISC, B-MISC, I-MISC, OTHER |

## Testing

To verify the fix:
1. Submit a prompt/response pair with various PII types
2. View the PII details
3. Compare the raw NER response with the "All Detected Items" section
4. Note that all high-confidence entities from the raw response now appear in the detected items
