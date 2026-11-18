# Does the first observation help select the second investigation?

Each public case discloses four distinct hypotheses. Each hypothesis predicts a binary answer for each of three channels. All predictions and delivered answers are accurate. The agent can query at most two distinct channels, must stop on a unique match and otherwise abstains after the second query.

The two planners receive the same four rows before the environment selects a true row. One commits to an ordered pair of channels. The other commits to a first channel and a continuation for each possible response. Each planner exhaustively selects the plan that resolves the most of the four equally weighted hypotheses, then minimizes projected total queries and uses lexicographic order to break ties. Planning computation is outside the observation budget. The adaptive search considers twelve plans, including the six static plans. Weak dominance on the primary objective follows from this inclusion. The measured quantities are the actual gain, its distribution and query cost.

All 70 four-element subsets of the eight possible binary rows are included. For each subset, all four possible truths are executed under both policies. Each compressed trace records the selected plan, actual channel/answer pairs and final conclusion. Row order follows the combinations of binary rows lexicographically, then truth index, then static and adaptive policy. The separate oracle ranks plans from leaf occupancy, checks every observed answer and conclusion, and challenges its report checks with two mutations.

Reproduce at the tested revision from the repository root:

```sh
export SOURCE_SHA="$(git rev-parse HEAD)"
python3 -I -B adaptive009/experiment.py > /tmp/adaptive009.json
python3 -I -B adaptive009/audit.py /tmp/adaptive009.json "$SOURCE_SHA"
```
