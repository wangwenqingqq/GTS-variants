# Source and dependency attribution

- Native storage,frozen exact-query operators,input caches,guard protocol,
  independent mutation replay pattern,and the interval/correlation parser are
  reused from this repository's reviewed parent `4b413f2`.
- `plan.hpp` is the frozen Tail-Provenance planner from the parent ownership
  study;it is included from there rather than silently replaced.
- The generic sparse propagation planner is a transparent implementation here,
  not an execution or copied implementation of LLVM or EnTT. Standard technique
  references and the novelty boundary are in `PRIOR_ART.md`.
- Standard GPU execution uses installed NVIDIA CCCL/Thrust headers and native
  CUDA APIs. Headers and shared-library code are not vendored or redistributed.
- The optional installed plotting style helper is not redistributed. Figures
  also support the standalone Matplotlib style specified by `plot.py`.

This artifact does not change the existing repository's visibility or license,
modify the confidential manuscript,or claim concurrency/production admission.
