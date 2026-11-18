# Which file supplied the effective limit?

The public fixture starts a real Python program reading four generated JSON files. defaults.json defines the initial integer. launch.json selects no profile, blue, or green. The selected profile overrides limit only if the key is present. Inactive files may contain plausible competing values. A value of zero is a valid override.

There are 54 configurations: two defaults, three launch modes and three contents (missing key, zero, seven) for each profile. For each configuration the application runs once normally, then once per existing definition with that definition alone replaced by 91. Exactly one intervention must change stdout. These are real file reads and process starts. Each intervention is restored before the next. Scoring requires both the original integer and its causal source filename, even when overriding with the same integer.

Three deterministic policies inspect the files through a reader. The defaults-only diagnostic always attributes an available default to defaults.json. The fixed comparison reads launch, defaults, then blue, stopping early on sufficient evidence. The adaptive comparison reads launch, follows its profile selection and reads defaults if needed. Both evidence-based policies know the precedence semantics. They share a three-read ceiling and see only the requested files. This comparison is against the specified fixed order. The strategies and the application's precedence rule were authored in advance; no learning or arbitrary code comprehension is tested.

We first expose every file, then withhold each of the four files from the investigator separately. The application has all files in every condition. A withheld file differs from an available file with an absent key. The separate audit enumerates every fixture matching the reader's observations, checks the subprocess results and intervention evidence and evaluates whether the value/source pair is uniquely supported.

From the repository root at the tested revision:

```sh
export SOURCE_SHA="$(git rev-parse HEAD)"
python3 -I -B config010/experiment.py > /tmp/config010.json
python3 -I -B config010/audit.py /tmp/config010.json "$SOURCE_SHA"
```
