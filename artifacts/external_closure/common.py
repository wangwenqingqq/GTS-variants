"""Reuse the established private-work boundary, not a second path policy."""
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('closure_target_run',Path(__file__).resolve().parent.parent/'unified_target_workflow/run.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
outside_repo=module.outside_repo
