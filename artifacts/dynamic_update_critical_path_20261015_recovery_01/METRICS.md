# Denominators

- Primary operator ACK:request-ready Host timer around the unchanged native
  operation,including all checks,mapping,witness appends,copy submission and
  explicit stream synchronization. Replacement includes both native ACKs and
  intervening measured-harness recording;its nested fields are not additive
  extra work. The formal event span also includes request-vector construction
  and loop bookkeeping,whereas individual request-ready ACKs do not.
- For each process report finite ACK mean,p50,p95,total,ACKs/s andpoint updates/s.
  Aggregate by six-process distribution;the headline is median of process
  aggregates. Batch512 has16 formal ACKs/process. Do not call this a population
  tail,arrival SLA or concurrent throughput.
- Amortized microseconds/point divides byK for I/D and2K for R;replacement ACK
  microseconds/batch and perreplacement are separate meanings. No scalar called
  “update latency” silently switches these denominators.
- Native I/D ACKs nested in replacement retain their own samples. Pure insert
  starts after untimed deletions;pure delete starts from fullN. Their states are
  not identical:the withinreplacement I/D contrast is an additional control.
- API Host intervals are runtime-layer spans. Exclude nested driver-layer
  intervals from additive Host partitioning. Validation/ownership intervals
  subtract overlapping runtime APIs. “Other Host” includes gaps and NVTX/timer
  overhead,not a proven CPU compute category.
- Device kernel and DMA interval unions are overlaid with Host ranges,not added
  to CPU partitions. Explicit wait count does not imply a particular transport
  round trip;pageable Async transfers may themselves block.
- Issued payload bytes,CUPTI transfer activity bytes and sampled DRAM-interface
  activity are different. Request/ACK and activity-bytes/activity-duration are
  labeled effective payload rates,not achieved physical DRAM bandwidth.
- The installed gb20x metrics samplecopy-engine activity,SM activity/issue,
  compute warps and DRAM interface read/write activity at10kHz. They are
  device-wide,valid only under the targetGPU isolation guard. They are not
  exact DRAM/L2 byte counters or per-ACK metrics below100us resolution.
- Application kernel count/duration is measured by actual timeline records.
  With no explicit update kernel,NCU per-kernel SM/DRAM/L2 fields are N/A,not
  invented zero hardware traffic. Copy-engine/internal driver work may remain.
- The oneGiB pageable-H2D/disjoint-D2D reference gives a measured large-copy
  comparison,not a same-contract deletion or search baseline. Never promote
  its bandwidth to an attainable bound for dependent random row swaps.
- Whole-service controls retain parent events+release segmentation,complete
  outputs and final state. No startup/context/client-input storage is added to
  their established denominator. Profiler duration never replaces that scope.
