"""Apply disclosed output-interface bounds repair before any experiment result."""
from pathlib import Path
import sys
p=Path(sys.argv[1])/'source_p/include/search_v2.cuh';s=p.read_text()
# Leaf kernels consistently consume half-open [ls, le), while qe is inclusive.
assert s.count('int le = qe;')==5
s=s.replace('int le = qe;','int le = qe + 1;')
# Isolated instrumented build only: no timed-build atomic instructions.
s=s.replace('TN node = node_list[nid];\n\n\t\t\tdis_q = 0;', 'TN node = node_list[nid];\n\t\t\tWORK(0,1);\n\t\t\tdis_q = 0;')
s=s.replace('int did = threadIdx.x;', 'int did = threadIdx.x;')
# Exact insertion anchors are audited by the generated diff.
s=s.replace('data_id = id_list[node.lid + did]; // Data idx in dataset.', 'data_id = id_list[node.lid + did]; // Data idx in dataset.\n\t\t\tWORK(0,1); WORK(2,1);')
s=s.replace('for (int did = tid; did < MAX_SIZE; did += THREAD_NUM)', 'if(tid==0) WORK(1,1);\n\tfor (int did = tid; did < MAX_SIZE; did += THREAD_NUM)')
p.write_text(s)
