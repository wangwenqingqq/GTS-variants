# Numerical and counting contract

The radius is the FP32 bit pattern0x3f34a3d8, promoted to FP64. Its threshold is
the FP64 product of that promoted radius, **0x1.fddb427319000p-2**, not an FP32
squared radius. Equality is an inclusive hit. Original coordinates and query
rows are FP32 and remain in the original0..959 order.

For each occurrence, subtraction, product and addition are separate ordered
FP64 operations. Compilation disables contraction, fast math and reassociation;
the CPU function rejects non-nearest rounding and nonfinite inputs. The primary
diagnostic continues through all960 coordinates to compare every score bit
against the preexisting complete ordered-FP64 reference. It records the first
strict crossing as a **counterfactual stopping dimension**; the diagnostic does
not actually avoid those full reads or measure progressive performance.

Nonnegative finite squared terms make the rounded sequential sum nondecreasing.
Every recorded rejection also checks predecessor<=threshold, crossing>threshold
and crossing<=full; every reference hit must have required_dims=960 and cannot
be rejected. These checks refer to the frozen ordered-FP64 semantics, not a
real-number exactness proof or a GPU parallel-reduction arithmetic contract.
Future GPU arithmetic needs a new conservative numerical-safety gate.

Required_dims=960 contains two distinct populations: genuine hits and nonhits
that cross only at the last coordinate. They are separately counted. Duplicate
vectors remain distinct physical occurrence IDs; no deduplication is performed.

The required-dimension CDF is P(required_dims<=K), reaching1 at960 because full
evaluation resolves hits too. The rejection curve instead counts nonhits only;
at960 it reaches the nonhit fraction. Checkpoint unresolved counts include true
hits. Quantiles use linear interpolation on the complete population, not a
sample or histogram-bin midpoint. Near/medium/far margins are frozen at0.1× and
1× the exact threshold, and are diagnostic only.

Mean×4 is ideal FP32 coordinate payload. It excludes query loads, state,
alignment/sectors, masks, divergence, scheduling, compaction/relaunch and result
materialization. It is neither measured DRAM traffic nor an end-to-end speedup.
