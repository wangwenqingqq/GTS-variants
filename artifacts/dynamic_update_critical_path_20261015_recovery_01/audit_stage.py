"""Exact post-run census; no command execution or CUDA initialization."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python without optimization.')
from common import PARENT, module, load, sha
from campaign import command

exact_directory=module('parent_exact_directory',PARENT/'audit_stage.py').exact_directory
GUARD={'command.json','before.json','after.json','checks.json','receipt.json','stdout.log','stderr.log','gpu.csv'}


def output_names(job):
    if job['kind']=='selftest':return set()
    suffixes={'copy.csv','meta.json'} if job['kind']=='copy' else {
        'queries.csv','ops.csv','ids.i32','dist.f32','squared.f64','authority.f64',
        'physical.i32','reverse.i32','mutations.i32','final.json','stages.csv','output.csv','meta.json'}
    if job['kind']=='micro':suffixes.add('ordering.csv')
    if job['kind']=='service' and job['mode']=='S2_STALE':suffixes|={'means.f32','ordering.csv'}
    return {job['label']+'.'+s for s in suffixes}


def report_names(job):
    return {job['label']+s for s in ('.nsys-rep','.sqlite')} if job.get('tool')=='nsys' else set()


def census(w,stage,jobs,rows,reg):
    root=w/stage;labels=[j['label'] for j in jobs];assert len(set(labels))==len(labels)==len(rows)
    files={'REGISTERED.json','RESULTS.json'}|{label+s for label in labels for s in ('.command.json','.checked.json','.outer.log')}
    exact_directory(root,files,('guards','outputs','reports'));exact_directory(root/'guards',(),labels)
    exact_directory(root/'outputs',set().union(*(output_names(j) for j in jobs)));exact_directory(root/'reports',set().union(*(report_names(j) for j in jobs)))
    commands={}
    for job,row in zip(jobs,rows):
        label=job['label'];guard=root/'guards'/label;exact_directory(guard,GUARD)
        assert set(row['guard_files'])==GUARD and set(row['reports'])==report_names(job)
        assert set(load(root/(label+'.checked.json')).get('raw_outputs',{}))==output_names(job)
        cmd=command(job,w,reg,root/'outputs'/label);assert load(root/(label+'.command.json'))==dict(command=cmd)
        assert load(guard/'command.json')==load(guard/'receipt.json')['command']==['numactl',f"--cpunodebind={reg['numa']}",f"--membind={reg['numa']}",*cmd]
        commands[label]=sha(root/(label+'.command.json'))
    return dict(passed=True,jobs=len(jobs),no_extra_entries_or_symlinks=True,source_derived_commands=commands)
