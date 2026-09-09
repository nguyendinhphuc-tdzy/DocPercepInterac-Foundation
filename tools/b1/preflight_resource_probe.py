"""Synthetic-only resource observations; never accepts a private input path.

Each engine/case runs in a fresh process. Measurements are diagnostic, not a
memory pass threshold or production qualification. The old engine is test-only.
"""
import argparse
import gc
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from foundation.adapters.preflight import OoxmlPreflight, PreflightConfig
from tests.backend.b1.preflight import accepted_v1
from tests.backend.b1.preflight.test_ooxml import document, Resolver, started
from tools.b1.build_corpus import large_xlsx_parts, package

CASES = {'dominant':(10000,5), 'distributed':(2000,)*5, 'over-default-elements':(20000,5)}


def deflate_package(parts):
    stream = BytesIO()
    with ZipFile(stream, 'w') as archive:
        for name, content in sorted(parts.items()):
            info = ZipInfo(name, date_time=(2026, 9, 8, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.create_system = 0
            archive.writestr(info, content.encode() if isinstance(content, str) else content)
    return stream.getvalue()


def memory():
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)] + [(n,ctypes.c_size_t) for n in (
                'PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage',
                'QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
        kernel = ctypes.WinDLL('kernel32',use_last_error=True)
        api = ctypes.WinDLL('psapi',use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        api.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        api.GetProcessMemoryInfo.restype = wintypes.BOOL
        m=Counters(); m.cb=ctypes.sizeof(m)
        if not api.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(m),m.cb):
            return {'available':False}
        return {'available':True,'measurement':'Windows process working set',
            'current_bytes':m.WorkingSetSize,'lifetime_peak_bytes':m.PeakWorkingSetSize}
    try:
        import resource
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return {'available':True,'measurement':'getrusage process lifetime maximum RSS',
            'lifetime_peak_bytes':int(peak if sys.platform=='darwin' else peak*1024)}
    except (ImportError,AttributeError):
        return {'available':False}


def worker(case, engine):
    parts=large_xlsx_parts(CASES[case],cells=10,formulas=True)
    data=deflate_package(parts) if engine=='resource-safe-deflate' else package(parts)
    doc=document(data)
    adapter=(accepted_v1.OoxmlPreflight if engine=='accepted-v1' else OoxmlPreflight)(Resolver(data))
    request=started(doc,adapter); gc.collect()
    before=memory(); begin=perf_counter()
    result=adapter.assess(doc,request,'2026-09-08T00:00:02Z')
    elapsed=perf_counter()-begin; after=memory()
    expected='FAILED' if case=='over-default-elements' else 'COMPLETED'
    reasons=[json.loads(a.data).get('reason') for a in result.artifacts if json.loads(a.data).get('observation_type')=='inspection_failure']
    return {'case':case,'engine':engine,'engine_version':adapter.version,'package_bytes':len(data),
        'compression':'DEFLATE' if engine=='resource-safe-deflate' else 'STORED',
        'rows_per_sheet':CASES[case],'cells_per_row':10,'status':result.assessment.status.value,
        'error_codes':[e.value for e in result.assessment.error_codes],'refusal_reasons':reasons,
        'behavior_matches_expected':result.assessment.status.value==expected,
        'elapsed_seconds':elapsed,'memory_before':before,'memory_after':after}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path)
    parser.add_argument('--worker',choices=CASES)
    parser.add_argument('--engine',choices=('accepted-v1','resource-safe','resource-safe-deflate'))
    args=parser.parse_args()
    if args.worker:
        if not args.engine: parser.error('--engine required with --worker')
        print(json.dumps(worker(args.worker,args.engine))); return
    if args.report is None: parser.error('--report is required')
    if args.report.exists(): parser.error('Report exists; choose a new observation path')
    rows=[]
    for case in CASES:
        for engine in ('accepted-v1','resource-safe','resource-safe-deflate'):
            result=subprocess.run([sys.executable,__file__,'--worker',case,'--engine',engine],
                check=True,capture_output=True,text=True,timeout=60)
            rows.append(json.loads(result.stdout))
            print(case,engine,rows[-1]['status'],flush=True)
    from dataclasses import asdict
    report={'evidence_kind':'SYNTHETIC_RESOURCE_OBSERVATION','production_qualified':False,
        'numeric_defaults':asdict(PreflightConfig()),'cases':rows,
        'limitations':['Single local observations, not memory test thresholds.',
            'Lifetime peak includes imports and synthetic input construction; baseline is recorded.',
            'No private corpus or Docling execution.']}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    with args.report.open('x',encoding='utf-8') as stream:
        json.dump(report,stream,indent=2,allow_nan=False); stream.write('\n')
    if not all(r['behavior_matches_expected'] for r in rows): raise SystemExit(1)


if __name__=='__main__': main()
