#!/usr/bin/env python3
"""Reproduce the paper's calculations and comment experiments offline."""
from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile
ROOT=Path(__file__).resolve().parent
NUMERIC=['stratum_inference.csv','arm_estimates.csv','domain_contrasts.csv','gap_decomposition.csv','two_domain_decomposition.csv','repository_standardization.csv','leave_one_repository_out.csv','rspack_arm_census.csv','report_order_counts.csv','stress_summary.json','legacy_audit.json']
def verify(root):
    manifest=json.loads((root/'SHA256SUMS.json').read_text())
    for name,digest in manifest.items():
        p=root/name
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise SystemExit(f'Integrity failure: {name}')
    return len(manifest)
def main():
    if sys.flags.optimize:raise SystemExit('Run with Python assertions enabled.')
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--output',type=Path,default=ROOT/'build');args=a.parse_args();out=args.output.resolve()
    if out==ROOT or ROOT in out.parents and out.relative_to(ROOT).parts[0] in ('data','reference','code','evidence'):raise SystemExit('Choose a separate output directory.')
    out.mkdir(parents=True,exist_ok=True);n=verify(ROOT);print(f'Integrity: {n} files',flush=True)
    with tempfile.TemporaryDirectory(prefix='claimscope-') as tmp:
        work=Path(tmp)
        for p in (ROOT/'data').iterdir():shutil.copyfile(p,work/p.name)
        for name in ['freeze.py','estimate.py','inference.py','sensitivity.py','published_labels.py']:shutil.copyfile(ROOT/'code'/name,work/name)
        for name in ['inference','sensitivity','published_labels']:
            with (out/f'{name}.log').open('wb') as log:subprocess.run([sys.executable,'-I',str(work/f'{name}.py')],cwd=work,stdout=log,stderr=subprocess.STDOUT,check=True)
        for name in NUMERIC:
            got=(work/name).read_bytes();expected=(ROOT/'reference'/name).read_bytes()
            if got!=expected:raise SystemExit(f'Regenerated output differs: {name}')
            (out/name).write_bytes(got)
        shutil.copyfile(work/'summary.json',out/'population_summary.json')
    for name in ['audit_evidence','audit_channels','replay_detector','test_source_tools']:
        with (out/f'{name}.log').open('wb') as log:subprocess.run([sys.executable,'-I',str(ROOT/'code'/f'{name}.py'),str(out)],stdout=log,stderr=subprocess.STDOUT,check=True)
    # Fresh replay results match the frozen per-PR counts; other source-span and intervention checks execute in replay_detector.
    report={'manifest_files':n,'numerical_outputs_identical':len(NUMERIC),'sample_design_outputs_identical':5,'evidence_inventory':json.loads((out/'evidence_audit.json').read_text()),'channel_inventory':json.loads((out/'channel_audit.json').read_text()),'source_tool_tests':json.loads((out/'source_tool_tests.json').read_text()),'detector':json.loads((out/'detector_summary.json').read_text()),'python':sys.version.split()[0]}
    (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));print(f'Outputs: {out}')
if __name__=='__main__':main()
