# Cheap novelty kill before Gate1 measurement

**Partial-distance early termination is established; this round claims no novel
search mechanism.** A fixed-radius variant of the same nonnegative-prefix rule
does not rescue a subsumed novelty claim. Gate1 measures the opportunity on one
frozen workload, not a new algorithm or a demonstrated GPU advantage.

| Primary source | Established mechanism | Boundary here |
|---|---|---|
| [Ramasubramanian and Paliwal, Pattern Recognition2000](https://www.sciencedirect.com/science/article/pii/S003132039900134X) | Partial accumulated Euclidean distance can eliminate a candidate before completing all coordinates. | Publisher access was limited; the primary publisher excerpt was inspected, not the complete article. |
| [Rakthanmanon et al., SIGKDD2012, Section4.1.3](https://www.cs.ucr.edu/~eamonn/SIGKDD_trillion.pdf) | Early abandoning of Euclidean distance uses an accumulated squared-distance threshold. | Time-series nearest-neighbor setting, not measured GIST B1 complete-output GPU range. |
| [Weber, Schek and Blott, VLDB1998, Section4](https://www.vldb.org/conf/1998/p194.pdf) | Compact vector approximations support safe candidate filtering and exact refinement. | No approximation representation, coding or refinement is implemented in this round. |

Retrieval hashes and limitations are retained in SOURCES.json. Original papers
and retrieval failures stay in private evidence. This is not an exhaustive
GPU/SIMD or representation survey. Any future prototype must separately audit
GPU/SIMD early-exit, exact screening, quantized bounds and progressive search,
and must beat a strengthened same-contract baseline after control/update/output
costs. A positive headroom result is not novelty admission.

Positive hypothesis: many original-order nonhits cross the radius threshold
well before960 coordinates. Negative hypothesis: hits and near nonhits require
most coordinates, leaving insufficient payload headroom. The full32M-pair CPU
test evaluates both under identical queries, radius, order and reference.
