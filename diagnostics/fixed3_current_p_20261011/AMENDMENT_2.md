# Controller-only recovery after qualification

All 21 registered qualification processes passed their runtime, isolation,
output/oracle and sanitizer checks. The controller then stopped at its closing
input-hash check: only its own mutable outer run.log had changed. This capture
file was mistakenly included among frozen inputs. No kernel, data, source,
binary, checker or reference drift was found. Preserve FAILED.json, FAILURE.txt,
the exact first controller, registration, all 21 outputs and receipts.

A SEPARATE resume.py excludes ONLY that mutable log from the original frozen
map. It independently revalidates all 21 original receipts, sanitizer summaries,
quality hashes, exact output payloads, and every build/resource/SASS/source pin.
Its new immutable registration binds the original registration/failure and
amendment before new runtime. No GPU qualifier is rerun or replaced. Only the
original remaining 3 counter +6 NSYS +18 conditional formal processes and the
already-registered single NCU probe may run, under fresh live isolation and the
same whole-continuation inherited locks. Original timing/acceptance unchanged.

The public fresh-run recipe uses an explicit input whitelist, and the public
continuation retains the same recovery semantics with disclosure-only UUID
hash binding. Executed and release recipe hashes remain distinct. Maximum:
48 main-workflow wrapper processes PLUS one diagnostic NCU probe =49 total.
