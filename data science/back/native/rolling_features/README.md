# Rolling Features Native Backend

This directory contains the optional C++ backend for the hottest rolling feature computations.

It is intentionally not part of the default App Engine dependency graph. Production keeps using the
Python fallback unless a compatible native module is built and explicitly enabled.

Build locally from the repo root:

```bash
./scripts/build_native_compute.sh
```
