# BFCL-derived routing subset

`bfcl-routing-subset.json` is a 30-case Stage-1 tool-routing benchmark derived
from the official Berkeley Function Calling Leaderboard (BFCL) V4 data.

It contains 20 non-live `multiple` cases, which require selecting one function
from several schemas, and 10 non-live `irrelevance` cases, where no supplied
function should be invoked. The `multiple` cases contain only candidate tools;
the `irrelevance` cases pair the supplied function with `no_tool`, matching
BFCL's category separation. Function arguments are retained for context but are
not scored.

This is **not an official BFCL leaderboard score**. It isolates the portion of
BFCL that a classifier can answer: route to a declared tool or abstain. Official
AST and executable evaluation also require argument generation and execution.

Source: [ShishirPatil/gorilla](https://github.com/ShishirPatil/gorilla), commit
`6ea57973c7a6097fd7c5915698c54c17c5b1b6c8`, Apache-2.0. The exact selection
and transformation are reproducible with `poc/build_bfcl_routing_subset.py`.
