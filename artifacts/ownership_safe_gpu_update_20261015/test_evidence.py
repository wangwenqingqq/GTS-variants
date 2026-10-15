"""Small CPU regressions for accounting and diagnostic parsers;no CUDA imports."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python without optimization.')
import csv,tempfile
from pathlib import Path
from common import jobs
import timeline,verify
import postcheck
from curate import ncu,names,reports,portable_build

def main():
    timeline.test();verify.test();postcheck.test()
    job=jobs('profile')[-1]
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/'report.csv'
        fields=['ID','Kernel Name','Metric Name','Metric Unit','Metric Value']
        metrics={'dram__bytes_read.sum':('byte','4096'),'dram__bytes_write.sum':('Kbyte','1.024'),
            'lts__t_sectors_op_read.sum':('sector','128'),'lts__t_sectors_op_write.sum':('sector','32')}
        def write(count):
            with path.open('w') as f:
                writer=csv.writer(f,quoting=csv.QUOTE_ALL);writer.writerow(fields)
                for index in range(count):
                    for metric,(unit,value) in metrics.items():writer.writerow([index,'void materialize_final(...)',metric,unit,value])
        write(16);result=ncu(path,job)
        assert result['totals']['dram__bytes_read.sum']==65536 and result['per_update_ACK']['dram__bytes_write.sum']==1024
        write(15)
        try:ncu(path,job)
        except AssertionError:pass
        else:raise AssertionError('Missing NCU launch admitted')
        metrics['dram__bytes_read.sum']=('','n/a');write(16)
        result=ncu(path,job);assert result['totals']['dram__bytes_read.sum'] is None and result['per_update_ACK']['dram__bytes_read.sum'] is None
        prefix=Path(folder)/'query'
        with Path(str(prefix)+'.stages.csv').open('w') as f:
            writer=csv.writer(f);writer.writerow(['invocation','stage','input'])
            for i in range(160):
                for stage,count in enumerate((160,156,149,129),1):writer.writerow([i+8,stage,int(i<count)])
        with Path(str(prefix)+'.queries.csv').open('w') as f:
            writer=csv.writer(f);writer.writerow(['phase','count']);writer.writerows((0,int(i<113)) for i in range(160))
        with path.open('w') as f:
            writer=csv.writer(f,quoting=csv.QUOTE_ALL);writer.writerow(fields);index=0
            for name,count in (('progressive_stage<0, 128>',160),('progressive_stage<128, 256>',156),('progressive_stage<256, 512>',149),('progressive_stage<512, 960>',129),('progressive_fields',113)):
                for _ in range(count):
                    for metric,(unit,value) in metrics.items():writer.writerow([index,name,metric,unit,value])
                    index+=1
        result=ncu(path,dict(kind='service'),prefix);assert result['launches']==707 and result['totals']['dram__bytes_read.sum'] is None
        folder=Path(folder);include=folder/'include';(include/'dlpack').mkdir(parents=True);(include/'dlpack/dlpack.h').write_text('test header\n')
        work=folder/'work';parent=folder/'parent';lib=folder/'libcuvs'
        reg=dict(commands={'test':[str(folder/'cuda/bin/nvcc'),'-I'+str(include),'-I'+str(work/'build'),'-L'+str(lib/'lib64'),'-lcuvs_c']},
            environment=dict(LD_LIBRARY_PATH=str(lib/'lib64'),PDX_MEANS=str(parent/'inputs/means.f32'),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1'))
        build=portable_build(reg,work,parent)
        assert 'DLPACK_INCLUDE' in build['variables'] and 'dlpack/dlpack.h' in build['external_include_hashes']['DLPACK_INCLUDE']
        assert not build['additional_include_searches']
    assert all(not names(j) for j in jobs('qualification')[:12])
    assert all(len(names(j))==2 for j in jobs('shapes'))
    assert len(reports(job))==1 and len(reports(jobs('profile')[0]))==2
    print('PASS:NCU units,n/a-not-zero,nonempty-stage census,missing-launch rejection,DLPack build export and output census;0 GPU starts')

if __name__=='__main__':main()
