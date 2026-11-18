# Partial predictions experiment

Tested e782700f55be33cd2cec227f32492c5f4c823bce; run https://github.com/artemidamoon2223-collab/SOMA-Public-Tests/actions/runs/44340510459.

32,768 decisions, 16,384 cases per policy. The fixed policy produced 2,048 correct and 14,336 abstentions; the visible-separation policy produced 3,488 correct and 12,896 abstentions. Both produced zero incorrect decisions. Predictions were independently masked. Each policy consumes one query. The observer treats a missing prediction as compatible with either observation.

A preliminary local oracle mistakenly required both predictions to be visible for every valid conclusion. That local assertion failed; the checked-in oracle handles elimination when one prediction is unknown. This is a deterministic synthetic fixture with accurate visible predictions, not learning or real model inference. Its input-dependent cases are exhaustive, not independent real-world trials.

Reproduce: python3 -I -B partial007/test.py > report.json && python3 -I -B partial007/audit.py report.json. The GitHub log also contains the complete compressed report.
