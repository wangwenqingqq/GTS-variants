# Single source format, version 1

The source consists of a 64-byte little-endian header and four packed layers.
Header: `<8sQII4QQ>` = magic `GTSPPLB1`, N, D, version=1, four absolute offsets,
payload byte count. For N=1,000,000/D=960, layer sizes are 480,000,000;
480,000,000; 960,000,000; 1,920,000,000 bytes. No entropy coding or dictionary.
Total persistent representation: **3,840,000,064 bytes**, including header.

For each row, layer 0 stores key bits 31..28, layer 1 bits 27..24. Adjacent
coordinate nibbles are high/low nibbles in a byte. Odd D has one padding nibble
per row/layer; target D=960 has none. Layer 2 stores bits 23..16 as uint8.
Layer 3 stores bits 15..0 as little-endian uint16. Original coordinate order and
row occurrence IDs are unchanged; IDs are implicit in row position.

Encoding uses original bits once, independent of all queries. Search receives
only layer pointers and a full query. Full raw input and frozen scores are only
available to the separate validator, not the candidate function. Decoding a
survivor completes the same source, never accesses a second raw representation.
The original dataset remains preserved externally for audit; single source means
the candidate's searchable database, not deleting the research oracle.
