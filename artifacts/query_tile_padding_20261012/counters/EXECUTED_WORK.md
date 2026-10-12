# Executed work

One selected native distance invocation/B; predicated-on FADD + FMUL + 2×FFMA. Not complete-output ACK timing. No counter sampling CI is claimed.

| B | Kernel ms | Executed FP32 proxy G | Useful proxy G | Inflation | Inflation × B |
| --- | --- | --- | --- | --- | --- |
| 1 | 3.339168 | 184.320 | 2.879 | 64.02223 | 64.02223 |
| 2 | 3.340832 | 184.320 | 5.758 | 32.01111 | 64.02223 |
| 4 | 3.353472 | 184.320 | 11.516 | 16.00556 | 64.02223 |
| 8 | 3.372352 | 184.320 | 23.032 | 8.00278 | 64.02223 |
| 16 | 3.418240 | 184.320 | 46.064 | 4.00139 | 64.02223 |
| 32 | 3.472864 | 184.320 | 92.128 | 2.00069 | 64.02223 |
| 64 | 3.600608 | 184.320 | 184.256 | 1.00035 | 64.02223 |
| 128 | 7.146368 | 368.640 | 368.512 | 1.00035 | 128.04446 |
