# Pre-GPU cost gate

Fixed32-query Gate1 survivor counts give1.014828776GB coordinate payload/query.
The explicit all-input producer/CUB-read and survivor-write accounting adds
20.99362525MB owner traffic and41.9872505MB FP64 state traffic. The required
model is1.07780965175GB/query, below1.25GB. Including16-byte tuple counter
bytes and flag read/write yields1.1024273771875GB/query. CUB scratch, query
loads, numerical rereads, output and sectors remain separately charged by
profiling; this is not measured DRAM. A CPU ordered-prefix screen will bound
replay demand before any CUDA launch. No survivor IDs are loaded by P1.
