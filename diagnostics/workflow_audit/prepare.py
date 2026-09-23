#!/usr/bin/env python3
"""Instrument a native copy, including mutation boundaries and an external oracle."""
import argparse,importlib.util,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('base',HERE.parent/'cpu_io/prepare.py');base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
def prepare(out):
 base.prepare(out)
 p=out/'include/gts_cpu_io_profile.hpp';p.write_text(p.read_text()+'\nvoid audit_begin(int flag,int id,int step);\nvoid audit_result(int count);\n')
 p=out/'include/update.cuh';t=p.read_text();t=base.replace_once(t,'\tfor (int i = 0; i < update_num; i++)\n\t{','\tfor (int i = 0; i < update_num; i++)\n\t{\n\t\taudit_begin(update_list[i].update_flag, update_list[i].update_id, i);\n\t\tGTS_DIAG_SCOPE(update_list[i].update_flag==0?"op.insert":update_list[i].update_flag==1?"op.delete":"op.query");')
 t=base.replace_once(t,'\t\t\tfprintf(fcost, "%d ", total_result_num);','\t\t\taudit_result(total_result_num);\n\t\t\tfprintf(fcost, "%d ", total_result_num);')
 for n,label in [('findTreeIdxByLogicalId','delete.cpu_lookup'),('ensureTotalResultWorkspace','query.result_workspace'),('ensureRebuildInsertWorkspace','rebuild.workspace'),('ensureUpdateSearchWorkspace','query.workspace')]:t=base.function_scope(t,n,label)
 p.write_text(t)
 p=out/'include/search_naive.cuh';t=base.function_scope(p.read_text(),'searchNaiveRnn','query.buffer_scan');p.write_text(t)
 p=out/'src/main.cu';t=p.read_text().replace('int main(int argc, char **argv)','\n#include "workflow.hpp"\nint main(int argc, char **argv)',1);t=base.replace_once(t,'\tload(file, data_info, data_d, data_s, size_s);','\tload(file, data_info, data_d, data_s, size_s);\n\tif (atoi(argv[3])==2) audit_init(data_info,data_d,std::stof(argv[4]));');p.write_text(t)
 (out/'include/workflow.hpp').write_bytes((HERE/'workflow.hpp').read_bytes())
 (out/'INSTRUMENTED_SHA256.json').unlink()
 h={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()};(out/'MANIFEST.json').write_text(json.dumps(h,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);prepare(p.parse_args().out)
