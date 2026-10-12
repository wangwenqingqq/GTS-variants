# Complete-output throughput

Median of six fresh process means; p10/p90 across process means, not a confidence interval. Query H2D, native distance, per-row complete compaction/fields/observer/D2H and completion are charged. Setup/build are outside ACK. B64/128 use the separately registered128 pool; no GTSPP or repeated-single speedup claim.

| B | Invocation ms | p10 / p90 ms | ms/query | Queries/s | 32-invocation pass ms | vs repeated-single |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 3.264684 | 3.248860 / 3.291409 | 3.264684 | 306.311 | 104.473606 | N/A |
| 2 | 3.317065 | 3.294166 / 3.328600 | 1.658532 | 602.944 | 106.152050 | N/A |
| 4 | 3.428618 | 3.399597 / 3.455918 | 0.857154 | 1166.651 | 109.721781 | N/A |
| 8 | 3.654076 | 3.627553 / 3.687828 | 0.456760 | 2189.336 | 116.937507 | N/A |
| 16 | 4.104561 | 4.057077 / 4.153814 | 0.256535 | 3898.152 | 131.360836 | N/A |
| 32 | 5.016530 | 4.978631 / 5.036908 | 0.156767 | 6378.913 | 160.564599 | N/A |
| 64 | 6.977129 | 6.927148 / 7.007660 | 0.109018 | 9172.828 | 223.340716 | N/A |
| 128 | 13.725235 | 13.680553 / 13.797419 | 0.107228 | 9325.896 | 439.349781 | N/A |
