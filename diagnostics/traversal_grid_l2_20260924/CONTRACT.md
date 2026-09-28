# L2 large-scale traversal screen

The audited million-point query profile shows original `findNextRnn` occupying
86.7% of GIST and 84.2% of Deep query kernel time. Its batch-one launch has
one 512-thread CTA, regardless of level size, on a 188-SM device. This screen
tests the execution-ownership hypothesis without changing tree construction,
pruning predicates, distance arithmetic, result fusion, Graph, output transfer,
query IDs, radius, or fixed capacity.

Modes are E: previously audited original traversal; S: the same L2 arithmetic
and predicates in a specialized one-CTA kernel; P: that kernel with each child
owned by a distinct lane across ceil(level_children/512) CTAs. E/S isolates
metric specialization; S/P isolates CTA distribution. All three use the same
new executable and are measured together on one admitted GPU. The previous
GPU-0 timings are context, never the denominator.

First verify normal-radius complete outputs against CPU float64 oracle and
original ordered float32 hashes for GIST, Deep and Tloc at N=1M. Then run
memcheck/synccheck and a four-round paired timing screen in alternating orders
ESP, PSE, SPE, EPS. Then profile one E/S/P trace per dataset to verify kernel
identity and launch structure; profiler time is diagnostic, not a latency
denominator. If the screen is promising, extend correctness to zero,
negative and all-hit radii and to N=65,536 before considering promotion.
Time one completed hot batch-one query including transfers and host readiness;
exclude build, tree construction, setup/capture, warmups and hashing. Record
independent process means and paired ratios. Any correctness or sanitizer
failure rejects the candidate. No production source is modified.

Use an idle GPU under its advisory lock, record physical index/UUID and
check for foreign compute activity throughout; stop only owned work on
interference. Preserve failed attempts. Do not change device settings.
