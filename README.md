# Agent Verification v2.3

Black-box end-to-end verification of the externally observable execution
contract.

The black-box suite does not inspect the DFA implementation or call internal
transition functions. It supplies external attempt outcomes and optional user
responses, then verifies only the resulting outcome, attempt count,
clarification count, and failure history.

Covered externally:

- success -> COMPLETE;
- recoverable failure -> automatic retry -> COMPLETE;
- repeated failure -> bounded USER_REQUIRED;
- interpretation drift -> USER_REQUIRED -> clarification -> execution;
- blocked verification -> USER_REQUIRED -> cancel -> ABORTED;
- explicit abort;
- clarification preserves execution history;
- no user response means no silent continuation.
