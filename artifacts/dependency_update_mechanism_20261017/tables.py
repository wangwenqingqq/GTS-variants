"""Presentation tables from fixed observations;pair quantiles use hashed raw CSVs."""
if not __debug__:raise SystemExit('Mandatory checks require ordinary Python.')
import argparse,csv,hashlib,io,json,tarfile
from pathlib import Path
import numpy as np
def load(p):return json.loads(p.read_text())
def main():
    p=argparse.ArgumentParser();p.add_argument('--study',type=Path,required=True);p.add_argument('--pairs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists();a.out.mkdir()
    rr=load(a.study/'results/PROCESSES.json');s=load(a.study/'results/SUMMARY.json');cpu=load(a.study/'evidence/CPU_TRACE_CENSUS.json')['records'];profile=load(a.study/'results/PROFILE.json')['records'];manifest=load(a.study/'evidence/RAW_MANIFEST.json')['files'];wanted={'study/primary/outputs/'+r['label']+'.pairs.csv':r for r in rr};quantiles={}
    assert len(rr)==len(wanted)==252 and s['query_coordinate_visits_invariant']
    with tarfile.open(a.pairs,'r|gz') as tar:
        for member in tar:
            assert member.isfile() and member.name in wanted and member.name not in quantiles
            body=tar.extractfile(member).read();spec=manifest[member.name[6:]];assert member.size==len(body)==spec['bytes'] and hashlib.sha256(body).hexdigest()==spec['sha256']
            rows=list(csv.DictReader(io.StringIO(body.decode())));r=wanted[member.name];values=np.array([float(row['ack_ms']) for row in rows]);assert len(values)==r['metadata']['update_batches']//2 and np.isfinite(values).all() and (values>0).all()
            assert abs(float(values.mean())-r['replacement_mean_ms'])<1e-12 and abs(float(np.quantile(values,.95))-r['replacement_p95_ms'])<1e-12
            quantiles[member.name]=dict(p50_ms=float(np.quantile(values,.5)),input_sha256=spec['sha256'],ACKs=len(rows))
    assert set(quantiles)==set(wanted)
    (a.out/'REPLACEMENT_QUANTILES.json').write_text(json.dumps(dict(scope='Descriptive p50 only;fixed paired estimator unchanged',closed_identity_sha256=load(a.study/'evidence/CLOSED_BINDING.json')['proof_sha256'],records=quantiles),indent=2)+'\n')
    def write(name,rows):
        with (a.out/(name+'.csv')).open('x',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    med=lambda values:float(np.median(values))
    structure=[]
    for r in cpu:
        structure.append({k:r[k] for k in ('N','batch','seed','family','replacements','batches','native_moves','final_assignments','elimination_ratio','RAW','WAW','fresh_occurrence_deletions','generic_tail_plan_mismatches')})
        structure[-1].update(distinct_original_occurrences_deleted=r['replacements']-r['fresh_occurrence_deletions'],total_dependency_levels=sum(int(k)*v for k,v in r['level_distribution'].items()))
    write('structure',structure)
    operators=[];services=[]
    keys=list(dict.fromkeys((r['family'],r['batch'],r['micro'],r['variant']) for r in rr))
    for family,batch,micro,variant in keys:
        cell=[r for r in rr if (r['family'],r['batch'],r['micro'],r['variant'])==(family,batch,micro,variant)];assert len(cell)==6
        common=dict(family=family,batch_limit=batch,micro=micro,variant=variant,N=1000000,D=960,independent_processes=6)
        for kind in ('delete','insert','replacement','query'):
            p50=[quantiles['study/primary/outputs/'+r['label']+'.pairs.csv']['p50_ms'] if kind=='replacement' else r[kind+'_p50_ms'] for r in cell]
            throughput=[1000*160/r['query_total_ms'] if kind=='query' else r[kind+'_points_per_s'] for r in cell]
            operators.append(dict(**common,operation=kind,item_unit='query' if kind=='query' else ('replacement_pair' if kind=='replacement' else 'point'),mean_ACK_ms=med([r[kind+'_mean_ms'] for r in cell]),p50_ACK_ms=med(p50),p95_ACK_ms=med([r[kind+'_p95_ms'] for r in cell]),items_per_s=med(throughput),amortized_ns_per_item=med([1e9/v for v in throughput])))
        services.append(dict(**common,replacement_pairs=cell[0]['metadata']['replacements'],formal_queries=160,service_median_ms=med([r['service_ms'] for r in cell]),service_p10_ms=float(np.quantile([r['service_ms'] for r in cell],.1)),service_p90_ms=float(np.quantile([r['service_ms'] for r in cell],.9)),events_median_ms=med([r['metadata']['events_ms'] for r in cell]),release_median_ms=med([r['metadata']['release_ms'] for r in cell]),CPU_events_median_ms=med([1000*(r['metadata']['cpu_events_user_s']+r['metadata']['cpu_events_system_s']) for r in cell]),CPU_core_equivalents_median=med([1000*(r['metadata']['cpu_events_user_s']+r['metadata']['cpu_events_system_s'])/r['metadata']['events_ms'] for r in cell]),RSS_peak_KiB_max=max(r['metadata']['process_peak_RSS_KiB_including_client_inputs'] for r in cell),known_device_owned_peak_bytes_max=max(r['metadata']['known_device_owned_peak_bytes'] for r in cell),device_observed_after_events_bytes_max=max(r['metadata']['device_observed_after_events_bytes'] for r in cell),standalone_maintenance_ms_max=max(r['metadata']['standalone_maintenance_ms'] for r in cell),plan_isolated_Host_peak_bytes='UNKNOWN',whole_service_DRAM_bytes='UNKNOWN'))
    write('operators',operators);write('service_and_resources',services)
    contrasts=[]
    for r in s['contrasts']:
        for metric,q in r['ratios'].items():
            contrasts.append(dict(family=r['family'],batch=r['batch'],micro=r['micro'],comparator=r['comparator'],candidate=r['candidate'],metric=metric,ratio=q['candidate_over_comparator'],CI_low=q['bootstrap95'][0],CI_high=q['bootstrap95'][1],reduction_percent=100*(1-q['candidate_over_comparator']),reduction_CI_low=100*(1-q['bootstrap95'][1]),reduction_CI_high=100*(1-q['bootstrap95'][0]),process_wins=q['process_wins'],forward_ratio=q['forward_ratio'],reverse_ratio=q['reverse_ratio'],marginal_median_ratio=q['marginal_median_ratio']))
    write('contrasts',contrasts)
    physical=[];counters=[]
    for name,r in profile.items():
        if name.startswith('nsys_'):
            for op,x in r['operators'].items():physical.append(dict(capture=name,operator=op,scopes=x['ranges'],scope='Profiled NVTX function scope,not primary ACK',**x['totals']))
        else:
            for row in r['records']:counters.append(dict(capture=name,metric=row['Metric Name'],unit=row['Metric Unit'],value='UNKNOWN' if row['parsed_value'] is None else row['parsed_value'],scope='First dependency wave' if 'GENERIC_WAVES' in name else 'First complete final-plan kernel',whole_service_DRAM='UNKNOWN'))
    write('physical_activities',physical);write('selected_kernel_counters',counters)
    print('TABLES_PASS',len(operators),'operator rows',len(services),'service cells',len(contrasts),'paired metric rows',len(quantiles),'hashed pair CSVs')
if __name__=='__main__':main()
