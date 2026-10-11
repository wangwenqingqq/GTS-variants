# Post-measurement metric clarification (no rerun or estimator change)

The immutable CONTRACT.json uses `trace_ms - measured release/drain_ms` as its
primary Host-ready service metric. This is the registered metric, not an exact
new timestamp at the last ACK. P2 records drain, then `u10.finish()` performs one
additional final device fence before recording trace. E also reads the clock for
release and trace separately. Subtraction therefore retains the small unisolated
final synchronization/clock tail. Between-ACK observation/dispatch overhead is
also retained, as intended. Results call this **registered trace-minus-release
service metric**, and do not claim exact isolation of the last-ACK boundary.

No denominator, process, binary or source is replaced. The original inclusive
trace-plus-release metric is reported separately. Cold setup, context and warmup
remain separate. Neither metric adds GPU execution to the CPU wait for the same
execution. This limitation prevents an exact independently isolated last-ACK
measurement claim, not the directly observed fourfold gap under the registered
service accounting. A future endpoint-marker experiment requires a new contract.
