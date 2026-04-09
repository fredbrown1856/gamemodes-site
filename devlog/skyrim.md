# Skyrim Mod & Lydia-1B — Development Log

SKSE plugin + dialogue server for Skyrim. Lydia-1B model investigation and training.

## 2026-04-09
- Completed comprehensive Lydia-1B model investigation
- Root cause identified: body language failure (2.8/10) due to narrow gesture vocabulary in training data
- Archived original training data (389 examples) with documentation
- Updated quality plan with body language diversity requirements (30+ distinct gestures, 5% max frequency)
- Tested GLM-5.1 API: 6% pass rate due to chain-of-thought contamination (unfixable)
- Tested MiMo v2 Pro API: 100% pass rate with validated Prompt 2 (explicit format instructions)
- Created combined training dataset: 374 validated examples (37% of 800-1000 target)
- Generated training data generation script with real-time progress monitoring
- Next: Run 800-1500 example generation, retrain model with improved adapter config

## 2026-04-02
- LLM server with dual provider, caching, priority routing
- Dynamic prompt tier system

## 2026-04-01
- SKSE plugin foundation
- http_client, npc_resolver, papyrus_functions, subtitle_display
