# Handoff — Editor-Accept experiments rounds 1 & 2 complete (2026-04-21)

## Status
v0.3.10 live but every editor rejects our output with "couldn't access file."
Two rounds of scientific experiments narrow the problem down dramatically.
Next round takes us to a fix.

## Rules (guardrail 6 in CLAUDE.md — enforced)
- Never claim a translated file opens in an editor without user-visual or
  pywinauto proof.
- Byte-identity, fidelity, HTTP 200s, parse gates = internal metrics only.
- Stated guesses have been wrong 3 times.

## What we know about the TF file format now

Every test below is against `samples/DOM CASMURRO 2.tff` (known editor-accepted).
TF Editor rejection wording is always "couldn't access file" regardless of the
actual cause.

### Round 1 results (`tools/tf_editor_experiment.py`)
| # | Modification | Editor result |
|---|---|---|
| 01 | exact copy | PASS |
| 02 | UUID at 0x38 replaced with fresh random 16 bytes | **PASS** |
| 03 | first zlib blob decompressed + recompressed at level 1 (content unchanged) | **FAIL** |
| 04 | byte-patch channel 1 name inside inner blob (forces recompress) | FAIL |
| 05 | our current writer's output (starts from `tf_empty.tff`, recompresses) | FAIL |

### Round 2 results (`tools/tf_editor_experiment_round2.py`)
| # | Modification | Editor result |
|---|---|---|
| 11 | exact copy (sanity) | PASS |
| 12 | recompress + zero outer bytes 0x80–0x8f | **FAIL** |
| 13 | recompress at zlib level 9 | **FAIL** |
| 14 | recompress with memLevel=9 | **FAIL** |
| 15 | flip one byte DEEP in compressed stream (no recompress, length preserved) | **PASS** |
| 16 | truncate last 8 bytes of file | **FAIL** |

### What this proves

1. **UUID at 0x38 is not content-bound.** #2 passing confirms our v0.3.10 approach of regenerating UUIDs is safe. It's just not sufficient.
2. **Editor does NOT run zlib integrity checking.** #15 passes — we flipped a byte deep in the zlib stream and the editor opened it anyway. So there is no CRC/adler32 check on the blob content.
3. **Editor REJECTS ANY recompression.** Every recompress (03, 12, 13, 14) fails even when the decompressed content is byte-identical. This is independent of zlib level, memLevel, or header mutations after the blob. Conclusion: either (a) the editor validates the *exact compressed byte stream* against a checksum stored elsewhere in the file, or (b) it validates the *file length* against a stored field, and any recompression changes the length (true for all our recompress attempts).
4. **File trailer matters.** #16 fails — trimming the last 8 bytes breaks the file. So there IS data at the end of the file the editor reads.
5. **Length-preserving in-place mods work.** #15 works because it doesn't change the file length or position of anything.

### The fix strategy this implies

**Don't decompress/recompress the blob.** Instead, patch bytes directly inside
the compressed zlib stream using byte-level substitution.

This is feasible for fixed-length fields (channel names are 64-byte slots
so replacing "KICK" with "SNRE" is a length-preserving substitution inside
the decompressed content AND the compressed stream, as long as we can locate
the right bytes). Finding where a specific decompressed byte maps into the
compressed stream is the core problem.

Two approaches:

**A. "Swap-in / swap-out" via dictionary-preserving recompression.**
Decompress the blob, patch the byte, recompress using the *original zlib
compressor's exact parameters*. If we can match the editor's compressor
output byte-for-byte on UNCHANGED content, we can also match it on patched
content (since DEFLATE is deterministic given the same compressor state).
The problem: we don't know the editor's compressor settings, and all the
common zlib parameter combinations fail (levels 1, 9, memLevel 9, etc.).

**B. Dictionary-search byte substitution.**
Since DEFLATE compresses by replacing matches with back-references, a
specific decompressed byte often appears LITERALLY in the compressed stream
(if the byte is not part of a matched run). We could search the compressed
stream for a unique byte pattern (e.g. the target channel name) and replace
it directly. Works when the channel name is stored as a literal — fails when
the name is deduped via back-reference.

**C. File-length preservation.**
If the editor validates only file length (not content), we could pad our
recompressed blob to match the original's length. Test: recompress the blob
and pad with trailing zeros to match the original file size. Include in
round 3.

## What the user needs to know

- Round 1 and 2 took ~2 minutes of user testing each (open 5-6 files in TF Editor).
- Round 3 should be the last round before a working fix, IF my working hypothesis is right.
- Log files from TF Editor would help isolate the exact failure cause. User asked: **is there a log we can check?** This is the next action to investigate — if TF Editor writes a log somewhere in `%APPDATA%` or `%LOCALAPPDATA%` we may get the exact rejection reason instead of the generic "couldn't access file."

## Next round to produce (but wait for user)

Round 3 experiments to resolve "content checksum vs length check":

- 21: recompress at level 1, PAD trailing bytes to match original file length exactly. If PASS = editor checks length only, we pad.
- 22: take the ORIGINAL file, REPLACE channel 1 name bytes inside the compressed stream IF we can find them as a literal. If PASS = approach B works for simple cases.
- 23: take #03 (failed recompressed) and append 8 bytes of zeros to the end to see if file-end-validation is tied to a specific offset rather than content.
- 24: take the ORIGINAL file, flip exactly one byte OUTSIDE the zlib blob (e.g. at offset 0x100). If FAIL = editor validates the entire file structure. If PASS = only blob area matters.
- 25: TF Editor logs. Before 21-24, check if `%APPDATA%\YAMAHA\TF Editor\` or similar has a log that shows the real error.

## Files
- `tools/tf_editor_experiment.py` — Round 1 producer
- `tools/tf_editor_experiment_round2.py` — Round 2 producer
- `.tmp/tf_experiments/` — all produced files
- `samples/DOM CASMURRO 2.tff` — reference editor-accepted file
- `samples/tf_edited_from_dcm2.tff` — editor's re-saved version (99% byte-different due to editor's normalization pass — not useful for diff-based format discovery)
- `engine/writers/yamaha_tf.py` — current writer (regenerates UUID, otherwise same)

## Current code state
- branch: `feature/cross-brand-fix` (worktree at `.worktrees/cross-brand-fix/`)
- main has v0.3.10 with UUID regen in DM7/TF/RIVAGE writers
- No changes to writers in this worktree yet — all work has been experiment tools

## For next session

Start with: "Read `docs/handover/2026-04-21-editor-accept-experiments-round1-2.md`."

Then:
1. Check for TF Editor log file location.
2. Run experiments 21–24.
3. If any PASS with length-preserved recompression, rewrite writers to pad.
4. If byte-substitution (approach B) works, rewrite writers to do direct compressed-stream patching.
5. Once TF is solved, apply same methodology to CL binary, DM7, RIVAGE.
