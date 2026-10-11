# Publication view and executed-source boundary

CONTRACT.json, prepare.py, run.py and test_recipe.py are byte-identical to the
executed registration recipes. They bind hardware by public UUID SHA256 and take
private paths as explicit arguments. Exact device UUID, actual commands/paths,
source trees, binaries, library/data paths, full outputs and profiler reports
remain in the private raw archive, never in the public Git set.

Analysis/profile/raw-verification scripts are post-campaign readers. They do not
alter or execute a GPU workload and never substitute a timing sample. The metric
clarification narrows wording to the registered trace-minus-release measure,
without changing the original contract or its numerical formula. The kernel/API
interval overlap ledger is diagnostic attribution, not a new latency denominator.

Raw manifest contains only relative archive filenames, sizes and hashes. Exact
file bytes and all 26 process receipts/156 full payload bindings were independently
verified locally without extraction. Public source/resource/library names+hashes
preserve provenance without shipping data, device configuration or private roots.

Inherited statistical and lock helpers are reused from existing committed task
folders. New tests cover budgets, direction and service subtraction; release
checks run from a clean committed archive, not only a mutable working tree.
