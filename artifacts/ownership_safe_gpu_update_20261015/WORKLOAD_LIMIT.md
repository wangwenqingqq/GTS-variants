# W2 dependency limitation — observed before GPU execution

The immutable prior W2 witnesses contain977 delete batches,500000 native row moves and500000 distinct final changed rows,with0 RAW/WAW/WAR edges. Thus safe ordinary batching can in principle cover all current W2 deletion copies without movement elimination.

Victims span the original1M IDs(min0,max999999),not just an initial physical prefix. However W2 replaces original occurrences and does not delete newly inserted occurrences. After a replacement,its fresh tail population cannot be a later original-ID victim. Do not portray this W2 as a high-dependency repeated-live-churn workload.

W2 remains unchanged for reproducible end-to-end engineering attribution. Random/localized/chain synthetic shapes test dependencies separately,with explicit scope. A W2 speedup alone establishes neither necessity nor novelty of provenance composition. A future repeated-live-occurrence mixed-query trace needs its own input/oracle/registration and is not silently substituted here.
