# Search scope and evidentiary limits

Checked on 2026-10-12. This is a cheap, bounded falsification search, not an exhaustive survey or a priority claim. Only primary papers, institution/author copies, pinned official source, and versioned official documentation support decisions. Search snippets and missing keyword hits do not establish absence.

## Families and representative queries

| Family | Queries / objects checked | Decisive locations |
|---|---|---|
| A: metric builds | M-tree bulk loading distance reuse / covering radius; Slim-tree MST split; PM-tree hyper-ring build; VP/MVP construction min/max bounds; GNAT construction | M-tree §§4–5.2; Slim §§3–4,6; PM §§3.1–3.3; VP/MVP §§3.3,4.2; GNAT §4.1 |
| B: integrated spatial bounds | GPU BVH build/refit; bottom-up bounding during construction; GPU kd-tree bounds; STR R-tree packing | Karras §4; Zhou §§3.1–3.3,5.1; STR §§2.1–2.2 |
| C: actual producer/consumer reuse | pivot distance reuse; distance reuse bulk loading; reuse distance computations during index construction | Pinned OMPL matrix producer, split assignment, radius/range updates, and query consumers |
| D: numerical controls | certified metric index construction; safe pruning certificate build; interval bound during construction; conservative distance bound generation; directed rounding tree bounds; nominal + directed-rounding tree construction | Ize error analysis/construction-padding comparison; CGAL fixed-release filtering; CUDA 13.1 double intrinsics |

The manifest records exact read locations and byte hashes. VP construction is checked in the primary MVP paper's explicit algorithm/discussion; this does **not** assert first historical priority for VP trees. PM-tree's selected 2004 DATESO paper is an insertion/split source, not an undocumented bulk-loader implementation. The Slim source is its 16-page author version. STR is the NASA report version, retained from an archive of the primary report.

## Retrieval and unknowns

- Twelve byte-identifiable source payloads are retained privately. The Microsoft kd-tree primary PDF was read through the web PDF reader (10 pages); direct retrieval returned HTTP 403, including a second download attempt. Its byte hash remains null, never fabricated.
- The NASA API report endpoint failed; the archival primary report was successfully retrieved (34 PDF pages including front matter and blank pages).
- Unretrieved original VP leads are not independent evidence. Generic search hits about unrelated refit systems or secondary explanations are excluded.
- Checked metric papers define mathematical distance bounds but do not specify the candidate's exact directed-FP64 expression/order. This remains UNKNOWN, not proof of unsafe code.
- No checked source proves the complete native-FP32-topology/bit-identical-FP64/one-level-GPU joint contract. This finite negative finding cannot justify PASS.
- No published system was implemented, benchmarked, or compared on the target GPU in this round.

## Cheap kill test

The generic claim fails from explicit published construction algorithms, reinforced by a pinned implementation that consumes the same matrix for allocation and bounds. The narrowly proposed composition remains a high-risk differentiation question, not an admitted contribution. Its next check must compare against **classical reuse plus generic directed arithmetic**, not just the redundant GTSPP baseline.
