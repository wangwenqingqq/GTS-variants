# OPT-KNN-P7 arithmetic and coverage

The input is finite float32, promoted exactly to double. Distances use explicit
RN subtract, multiply, and ordered add; FMA is disabled. The independent oracle
has a different layout/kernel and is CPU checked. Small tables enumerate every
object on the CPU.

Let u=2^-53 and m=D+3. A nonzero difference between finite float32 inputs, its
square, and every positive accumulated sum are normal finite double values.
The minimum positive squared difference is 2^-298; even 960 terms of the
largest float32 difference are far below double overflow. Thus the normal
relative rounding model applies, including subnormal *float32* inputs.
For an exact squared Euclidean distance R and the ordered RN result S, each
term encounters at most two occurrences of subtraction error, one multiplication
error, and D additions. Standard products of (1+delta), |delta|<=u, imply
|S-R|<=gamma_m R, with gamma_m=mu/(1-mu). Zero is exact.

The CUDA helper computes an upper bound g>=gamma_m using directed rounding.
It encloses the mathematical norm by

    lo = sqrt_RD(div_RD(S, add_RU(1,g)))
    hi = sqrt_RU(div_RU(S, sub_RD(1,g))).

No empirical epsilon or float32 radius is used. If S<=U (the RN seed kth
distance), the true norm is <=sqrt_RU(div_RU(U,sub_RD(1,g))). For each tree
node the static refit obtains the minimum lower norm and maximum upper norm
to that node's actual pivot over **all** its members. A query-pivot enclosure
intersects that node interval expanded by the query radius whenever any member
has RN distance <=U, by the triangle inequality. Disjoint intervals prove safe
rejection. Equality and unproved bounds retain. Node ancestry and membership
partitions are checked. Identical sibling pivot IDs share the query-pivot work;
different IDs are always evaluated separately.

The seed set has at least K distinct real objects. Consequently the global kth
RN squared distance is <= the seed kth U. Nonnegative ordered accumulation is
monotone; a partial sum strictly >U cannot become an admissible final distance.
Each 256-object block retains K using (RN squared distance, original ID);
an omitted object has at least K predecessors in its own block. Repeating this
selection on the disjoint block unions therefore retains the global K. Seeds
are scanned again but never appended again to the result.

The proof applies to finite float32 inputs and the pinned dimensions/operations.
The float32 output field can overflow for extreme inputs even when the double
selection is valid; the delivery contract rejects such outputs. The edge tests
use large finite values with representable final fields. The proof is separate
from empirical quality on GIST and Deep and does not establish an external
library's numerical equivalence.
