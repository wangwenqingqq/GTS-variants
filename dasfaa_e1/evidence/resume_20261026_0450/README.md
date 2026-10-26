# Explicit E1 resumption — resource-stopped

This directory contains curated local receipts, not new GPU results.

- RECOVERY.json: prior CPU inventory end receipt recovered before new work.
- CPU_RUNNER_CANCELLATION.json: narrow Linux runner cancellation/lock proof.
  cpu_tested_sources preserves exact tested bytes. Current supervision source
  has later local-only corrections and must not inherit this runtime verdict.
- upload_refused.stderr and inventory_killed.stderr: authoritative guard97/98.
- STOP_CAMPAIGN.json: first-observed stop, missing remote receipts and scope.

The Linux fixture covers pre-created delayed/orphaned separate-session children,
not a fork concurrent with teardown. Standalone resource-watchdog killpg escape,
outer-runner death and unbounded quarantine remain unresolved. GPU admission
stays blocked. No raw process inventory, device configuration, credentials or
conversation transcript is published. Full raw local logs are kept outside Git.
