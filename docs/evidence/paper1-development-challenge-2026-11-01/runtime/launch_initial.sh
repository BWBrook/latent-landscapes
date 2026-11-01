#!/usr/bin/env bash
set -euo pipefail
cd /data/codex/latent-landscapes/challenge-20261101
panel=artifacts/paper1_development_challenge_20261101
.venv/bin/python - <<'PY'
from pathlib import Path
import json
p=Path('artifacts/paper1_development_challenge_20261101')
banks=json.loads((p/'jobs-banks.json').read_text())
profiles=json.loads((p/'jobs-profiles-archived.json').read_text())
assert len(banks['jobs'])==6 and len(profiles['jobs'])==48
out=p/'jobs-profiles-first12.json'
if out.exists() or (p/'bank-ledger').exists() or (p/'profiles-first12-ledger').exists():
    raise FileExistsError('initial launch already prepared or started')
out.write_text(json.dumps({**profiles,'phase':'profiles-first12','jobs':profiles['jobs'][:12]},indent=2)+'\n')
PY
nohup .venv/bin/python scripts/execute_development_jobs.py --jobs "$panel/jobs-banks.json" --workers 6 --ledger "$panel/bank-ledger" > "$panel/bank-runner.log" 2>&1 < /dev/null &
bank_pid=$!
nohup .venv/bin/python scripts/execute_development_jobs.py --jobs "$panel/jobs-profiles-first12.json" --workers 12 --ledger "$panel/profiles-first12-ledger" > "$panel/profiles-first12-runner.log" 2>&1 < /dev/null &
profile_pid=$!
printf '%s\n' "$bank_pid" > "$panel/bank-runner.pid"
printf '%s\n' "$profile_pid" > "$panel/profiles-first12-runner.pid"
printf 'bank_runner_pid=%s profile_runner_pid=%s\n' "$bank_pid" "$profile_pid"
