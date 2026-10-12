# Retained preflight attempts

1. The first CPU preparation stopped at the previous-allocation check: the prior
   campaign registered the same physical device by UUID, while the new CLI used
   its local numeric slot. No compilation, CUDA context, qualification or timing
   process ran. Preserve the failed log and empty preparation directory. The
   second preparation uses the exact previous UUID and the same NUMA node in a
   fresh external work directory; source, pools/seed and workload are unchanged.

2. CPU delivery verification found that the analysis import temporarily put the
   legacy artifact first on the Python module search path, causing a standalone
   verifier to import the wrong campaign module. Load the exact original SASS
   normalizer by file instead, and retain an import-order regression test. No
   measurement source, GPU run, counters, algorithm or observation changed.
