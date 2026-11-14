# CI-002 public synthetic IPC fixture

New standalone code only. Three long-lived processes: investigator, controller,
worker. Parent test harness registers the actual investigator PID. AF_UNIX kernel
SO_PEERCRED is authoritative; self-declared identity is compared, never trusted.
Controller authorizes only echo. Tickets bind PID, UID, action, payload and a
2-second expiry, using a fresh 32-byte synthetic HMAC key passed through anonymous
pipes to controller and worker only. No key/ticket material is persisted in Git.
Worker durably records RUNNING before a synthetic effect, and COMPLETED afterward.
Restart maps RUNNING to UNKNOWN_OUTCOME; replay never executes again.

This is cooperative same-UID process separation, NOT hostile process isolation.
Same-UID peers may access files or potentially inspect process memory. PID reuse,
coordinated database rollback, power loss, root compromise and distributed leases
are NOT VERIFIED. Different-UID execution is BLOCKED: no authorized means to
change Unix identities is used. Filesystem isolation is NOT VERIFIED. Mount
namespace remains BLOCKED as established by CI-001; no privileged retry occurs.
A separate worker impersonator is tested, and each real worker also attempts an
unauthorized controller operation and requires WRONG_PEER before its authorized
synthetic execution. No sudo, setuid, production code, custom credentials, models,
private checkout or paid resources.

Reproduce on Python 3.12 Linux with AF_UNIX: `timeout --kill-after=5s 90s python -B
ipc002/verify.py`. It exits nonzero immediately on a counterexample and prints
partial records in a finally block. Rejections require the exact intended reason
AND live servers. Corruption requires explicit diagnostic and exit 42; intentional
crash requires SIGKILL, not arbitrary process failure. Each workflow executes two
fresh independent repetitions, bounded by a five-minute job timeout. A failed
first repetition stops the second. No service calls or package dependencies.

Candidate is frozen by Git commit before runtime verification. Source hashes and
actual run logs will be preserved separately. Independent verification here means
a separate adversarial driver and source/log inspection, not an external audit.

SCIENTIFICALLY_VALIDATED=NO
CONFIRMATORY_SET_USED=FALSE
NEW_LIVE_MODEL_CALLS=0
