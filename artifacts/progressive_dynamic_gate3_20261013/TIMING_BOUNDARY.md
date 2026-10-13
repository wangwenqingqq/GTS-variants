# Exact timer boundary and retained contract deviation

The frozen numeric estimator is `events_ms + release_ms`, in both systems. It is **not uninterrupted process wall time or complete Host-container teardown**. This clarification does not modify a timer, sample, kernel, acceptance threshold or the frozen `CONTRACT.json`.

1. `events_ms` spans every event ACK: query H2D, distance/selection/count waits, complete result D2H, one physical-to-logical mapping, updates, synchronization and event bookkeeping. Primary processes contain no extra stage probes.
2. The separately excluded `offline_final_and_probe_ms` interval contains direct comparison of every final device-vector byte, actual map export, and (diagnostic processes only) final probes and their audit serialization.
3. `release_ms` charges a final logical-map copy, native Faiss/norm/live-map/device-buffer and stream release; D1's additional device-state and CUDA events are freed here.
4. Ordinary retained answers, operation/ownership/metadata file serialization occur **after** release and are not included in the separately timed middle interval. Their retained Host containers, the copied final map, and D1's retained Host audit vectors are destroyed after the timer. This destruction is unmeasured, not proven free. Context teardown is also outside the service timer.

The contract phrases “complete resource release/bookkeeping” and middle-interval “serialization” were overbroad. The measured claim is restricted to the above segmented service boundary. A broader all-Host-resource/process-exit interpretation remains unvalidated; it cannot be obtained by relabeling this result. Required Gate3 numeric GO was not reached anyway, and no full dynamic-system or paper admission is asserted.

Ownership uses full-map **induction** from the actual local transition witnesses and frozen native mutation bodies, plus full independent replay after every update. It is not a full actual-map export after every event. Entire actual final maps and every actual final GPU vector byte are separately checked. The distinction is retained in all quality records.
