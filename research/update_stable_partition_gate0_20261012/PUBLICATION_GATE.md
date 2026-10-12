# Publication gate

Publish only the following task-owned files to the existing public GTS-variants
repository, preserving visibility/history and without merging the task branch:

```text
README.md
SEARCH_SCOPE.md
PRIOR_ART_MATRIX.md
EVIDENCE_CARDS.md
NEAREST_WORK.md
NOVELTY_DECISION.md
NEXT_MECHANISM.md
CLAIM_EVIDENCE.md
PUBLICATION_GATE.md
CONTRACT.json
evidence/SOURCES.json
evidence/CARDS.json
evidence/DECISION.json
scripts/validate.py
```

Paths are relative to this Gate0 directory. No private `local/` item, downloaded
PDF, full extraction, source header, HTML, plan attachment, conversation, device
configuration, credential or unrelated old result belongs to this publish set.
Public hashes and primary-source URLs are reproducible bibliographic provenance;
authors' names are legitimate research attribution, not private device identity.

Pre-upload gates: inspect exact whitelist/staged diff; runnable integrity check;
full-history sensitive-content scan; independent read-only adversarial audit and
owner verification of findings. Existing history warnings must be classified,
not silently called a clean scan.

Post-commit gates: clean archived-tree check; no unrelated staged changes;
normal push to the verified owner/repository; independent remote branch/visibility
and public file-byte verification. Publication completion is recorded separately
in a private receipt after that verification; this prepublication document does
not itself assert a push succeeded. No PR or merge is implied.

## Verified local checks (2026-10-12)

- Record validator and all 15 retained primary-source byte hashes passed.
- Whitelist-only clean copy passed; changing the GPU process declaration to 1
  was rejected by the integrity check's negative control.
- Full-history scanner returned 1, **not a literal clean scan**: existing public
  author-email metadata and previously published generic sanitization-pattern
  blob `58e1e7cffbeb42992154abbb9acf8af4c17cb00b` matched. The latter was inspected
  line-by-line: patterns remove private paths, not literal user credentials or
  machine paths. No dangling-history or forbidden-attribution match was found.
  These existing classified matches do not authorize an unrelated history rewrite.
- None of the 14 shipping files contains a private home path, credential,
  conversation or redistributed paper/source file.

Independent audit findings and final remote verification are retained in the
private delivery receipt, not asserted in advance here.
