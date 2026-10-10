#!/usr/bin/env python3
"""Import-only dependency gate; no data, index build, query or CUDA allocation."""
import argparse,json,os,subprocess
from pathlib import Path
from common import outside_repo

TREE="""
import sklearn,threadpoolctl
from sklearn.neighbors import KDTree,BallTree
assert sklearn.__version__=='1.6.1'
modules=[sklearn,threadpoolctl];versions={'sklearn':sklearn.__version__,'threadpoolctl':threadpoolctl.__version__}
"""
FAISS="""
import faiss,sys
assert faiss.__version__=='1.15.1' and 'GPU' in faiss.get_compile_options()
assert all(hasattr(faiss,n) for n in ('IndexFlatL2','GpuIndexFlatL2','StandardGpuResources'))
faiss.omp_set_num_threads(1);assert faiss.omp_get_max_threads()==1
modules=[faiss]+[m for n,m in sys.modules.items() if n.startswith('faiss.') and getattr(m,'__file__','') and str(m.__file__).endswith('.so')]
assert len(modules)>1
versions={'faiss':faiss.__version__,'native_omp_threads':faiss.omp_get_max_threads()}
"""

def inspect(python,probe):
    env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    code="import hashlib,json,numpy as np\nfrom pathlib import Path\n"+probe+"""
modules.append(np);versions['numpy']=np.__version__
print(json.dumps(dict(versions=versions,modules={m.__name__:dict(path=m.__file__,sha256=hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()) for m in modules})))
"""
    run=subprocess.run([str(python),'-c',code],env=env,text=True,capture_output=True,check=True)
    return json.loads(run.stdout)

def main(a):
    output=outside_repo(a.output);assert not output.exists()
    results=dict(tree=inspect(a.tree_python,TREE),faiss=inspect(a.faiss_python,FAISS))
    output.write_text(json.dumps(dict(passed=True,roles=results,scope='imports only; not native correctness, timing or recovery admission'),indent=2)+'\n')
    print('PASS existing tree/Faiss dependencies; no benchmark or GPU allocation')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('tree-python','faiss-python','output'):p.add_argument('--'+k,type=Path,required=True)
    main(p.parse_args())
