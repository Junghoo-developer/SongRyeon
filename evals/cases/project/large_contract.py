"""Long deterministic source fixture used to exercise retention boundaries.

This module is intentionally longer than a short retained excerpt.  Its text is
stable and contains several unrelated sections so an evidence-selection node
has to preserve the section relevant to the user's question.

Section 01 describes an imaginary queue.  Items enter in arrival order and are
identified by an opaque key.  The queue description is only filler.

Section 02 describes an imaginary cache.  Entries expire after a fixed window
and are replaced atomically.  The cache description is only filler.

Section 03 describes an imaginary parser.  It accepts UTF-8 input and rejects
unknown fields.  The parser description is only filler.

Section 04 describes an imaginary renderer.  It creates plain text without
terminal colour codes.  The renderer description is only filler.

Section 05 describes an imaginary scheduler.  Jobs are sorted by a stable
priority and then by insertion order.  The scheduler description is filler.

Section 06 describes an imaginary index.  Keys are normalized before lookup
and no fuzzy matching is performed.  The index description is only filler.

Section 07 describes an imaginary recorder.  Records are append-only and each
record has an independent identifier.  The recorder description is filler.

Section 08 describes an imaginary validator.  Values are checked before any
state transition occurs.  The validator description is only filler.

Section 09 describes an imaginary router.  A route is selected from a closed
set and unknown routes are rejected.  The router description is only filler.

Section 10 describes an imaginary counter.  It starts at zero and increments
after a successful operation.  The counter description is only filler.

Section 11 describes an imaginary reader.  It never changes the source it
opens.  The reader description is only filler.

Section 12 describes an imaginary writer.  It writes to a temporary location
before replacing a destination.  The writer description is only filler.

Section 13 describes an imaginary timer.  Durations are recorded in
milliseconds and are never inferred from timestamps.  This is only filler.

Section 14 describes an imaginary result object.  It carries a success flag,
content and an optional error.  The result description is only filler.

Section 15 describes an imaginary boundary.  A selected excerpt includes its
start offset and excludes its end offset.  The boundary description is filler.

Section 16 describes an imaginary audit.  Machine-observed values are retained
separately from model judgments.  The audit description is only filler.

Section 17 describes an imaginary fixture.  It is synthetic, contains no user
memory and is safe to commit with a benchmark.  This is only filler.

Section 18 describes an imaginary report.  It must label synthetic results as
fixtures rather than measured model performance.  This is only filler.
"""

LONG_FILE_SENTINEL = "retention-boundary"
