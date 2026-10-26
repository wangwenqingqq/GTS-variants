"""Read-only, streaming inventory; never admits a dataset to the campaign."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path



def file_info(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(8<<20),b''):
            h.update(block)
    return dict(path=str(path),bytes=path.stat().st_size,sha256=h.hexdigest())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--tide-root',type=Path,required=True)
    args=parser.parse_args()
    ROOT=args.root
    TIDE=args.tide_root
    snapshots=[]
    for path in sorted((TIDE/'data/prepared/snapshots').iterdir()):
        if not path.is_dir():continue
        files={key:file_info(path/name) for key,name in
               [('fingerprints','fp_u64x4.bin'),('ids','id_i64.bin'),('popcounts','popcnt_u16.bin')]}
        n=files['fingerprints']['bytes']//32
        assert files['fingerprints']['bytes']==n*32
        assert files['ids']['bytes']==n*8 and files['popcounts']['bytes']==n*2
        snapshots.append(dict(release_date=path.name,rows=n,format='headerless fp_u64x4 (256 bits), id_i64, popcnt_u16',
                              all_rows_tree_admissible=False,reason='N exceeds mandatory 10M ceiling',files=files))
        print(json.dumps({'snapshot':snapshots[-1]}),flush=True)
    fps=TIDE/'data/official/chembl_37/chembl_37.fps.gz'
    headers=[]
    rows=0
    widths=set()
    with gzip.open(fps,'rt',encoding='ascii') as stream:
        for line in stream:
            if line.startswith('#'):
                headers.append(line.rstrip())
            elif line.strip():
                widths.add(len(line.split()[0])*4)
                rows+=1
    chembl=dict(file=file_info(fps),rows=rows,fingerprint_bits=sorted(widths),headers=headers,
                int32_expanded_binary_float_max_rows=(2**31-1)//2048-1,
                replacement_authorized=False)
    print(json.dumps({'chembl37':chembl}),flush=True)
    protein=ROOT/'wxr_pro6000-1/GTS/Datasets/dna_barcode/protein_200k.txt'
    count=0
    lengths={}
    with protein.open() as stream:
        header=stream.readline().strip()
        for line in stream:
            values=list(map(int,line.split()))
            assert all(0<v<256 for v in values)
            lengths[len(values)]=lengths.get(len(values),0)+1
            count+=1
    protein_info=dict(file=file_info(protein),header=header,rows=count,
                      format='space-separated integer-encoded sequence bytes, not literal strings',
                      min_length=min(lengths),max_length=max(lengths),length_histogram=lengths,
                      version='not established: no release/accession mapping in this file',
                      replacement_authorized=False)
    print(json.dumps({'protein200k':protein_info}),flush=True)
    prep=TIDE/'scratch/chembl37_static_2048/chembl37_static_20260903_v1/root'
    metadata={}
    for path in sorted(prep.glob('*.json')):
        metadata[str(path)]=dict(file_info(path),content=json.loads(path.read_text()))
    print(json.dumps({'inventory_complete':True,'snapshots':snapshots,'chembl37':chembl,
                      'protein200k':protein_info,'prepared_chembl_metadata':metadata,
                      'recommendation_only':True}),flush=True)

if __name__=='__main__':main()
