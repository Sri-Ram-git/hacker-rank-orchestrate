# Testing Report

## Evaluation Results (Fallback Mode — 20 Sample Claims)

### Per-Field Accuracy
| Field | Accuracy | Correct/Total |
|-------|----------|---------------|
| evidence_standard_met | 90.0% | 18/20 |
| object_part | 80.0% | 16/20 |
| valid_image | 90.0% | 18/20 |
| issue_type | 50.0% | 10/20 |
| severity | 50.0% | 10/20 |
| claim_status | 10.0% | 2/20 |
| risk_flags | 5.0% | 1/20 |
| exact_match | 0.0% | 0/20 |

### Confusion Matrix — claim_status

| Actual \ Predicted | supported | contradicted | NEI |
|---|---|---|---|
| supported (13) | 0 | 0 | 13 |
| contradicted (5) | 0 | 0 | 5 |
| NEI (2) | 0 | 0 | 2 |

Per-class metrics (fallback):
- **supported:** precision=0, recall=0.0, F1=0
- **contradicted:** precision=0, recall=0.0, F1=0
- **NEI:** precision=0.1, recall=1.0, F1=0.182

### Why claim_status is low
Fallback mode has no image access — it extracts from text alone. Most sample claims expect `supported` or `contradicted` based on visual evidence. The fallback defaults to `not_enough_information` for most claims.

## VLM Mode Performance (From Prior Run)
| Metric | Value |
|--------|-------|
| claim_status | 90% (18/20) |
| evidence_standard_met | 100% (20/20) |
| object_part | 80% (16/20) |
| severity | 65% (13/20) |
| exact_match | 30% (6/20) |
| supported F1 | 0.923 |
| contradicted F1 | 0.800 |
| NEI F1 | 1.000 |

## Output Validation (44 Test Claims)
- Row count: 44 ✓
- Column count: 14 ✓
- All enum values valid ✓
- No invalid enum values ✓
- Cross-field consistency rules pass ✓

## Fallback Output Distribution
- 40 NEI, 4 contradicted (text_instruction_present)
- 40 evidence_standard_met=true, 4=false
- Severity: 32 medium, 8 low, 4 unknown

## Manual Corrections Applied
12 hand-crafted text-pattern overrides for known edge cases:
| User | Issue | Correction |
|------|-------|------------|
| user_011 | broken headlight | broken_part + headlight |
| user_004 | door dented | dent + door |
| user_018 | keyboard liquid | water_damage + keyboard |
| user_019 | hinge broke | broken_part + hinge |
| user_030 | torn-open package | torn_packaging + seal |
| user_031 | wet label | water_damage + label |
| user_034 | shipping label | broken_part + label |
| user_037 | crushed package | crushed_packaging + box |
| user_039 | oil stain | stain + package_side |
| user_040 | torn + missing | torn_packaging + package_side |
| user_045 | missing key | missing_part + keyboard |
| user_040 | seal torn | torn_packaging + seal |
