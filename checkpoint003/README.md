# Independent checkpoint fixture

The verifier receives a trusted checkpoint from its caller and checks a
synthetic journal and its co-located anchor. It accepts only the exact
generation and journal bytes already confirmed by the caller. It does not
mutate journal state or advance the checkpoint.

This covers a gap left open by CI-001 and CI-002. A journal and its local
anchor can still agree after both have been restored to an old snapshot.
The public driver supplies the confirmed head separately and independently
constructs the test snapshots. It checks expected reason, exact exit status
and that local files stay unchanged. A deliberate process SIGKILL after
the journal write and before anchor update must leave a detectable mismatch.

Run once on Linux with Python 3.12:

```sh
timeout --kill-after=5s 45s python3 -I checkpoint003/verify.py
```

This design assumes that a caller supplies an authentic, current checkpoint
from outside the state under review. The fixture demonstrates the comparison
using a parent test process. Storage independence, checkpoint authentication,
concurrent writers during verification, power loss, hostile same-UID isolation,
and production integration require separate evidence. The caller must quiesce
writes or provide an immutable snapshot. No cryptographic keys or networks
are used in the fixture.

GitHub Actions runs only on pushes to the dedicated branch that change code
or workflow paths. Evidence-only commits do not trigger another run.
