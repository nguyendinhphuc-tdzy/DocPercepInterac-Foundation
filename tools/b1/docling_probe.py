"""Run B1.2A, writing failure evidence even if qualification infrastructure fails."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

from foundation.evaluation.perception.docling_probe import run_manifest


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--manifest',type=Path,default=ROOT/'tests/golden/cases/b1/manifest.json')
    parser.add_argument('--report',type=Path,default=ROOT/'tests/golden/reports/b1/docling-qualification.json')
    args=parser.parse_args()
    try:
        report=run_manifest(args.manifest,args.report)
    except Exception as exc:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps({'qualification_status':'INSUFFICIENT_EVIDENCE',
            'infrastructure_error':type(exc).__name__,'message':str(exc),'production_qualified':False},indent=2)+'\n',encoding='utf-8')
        print(f'Qualification infrastructure failed: {type(exc).__name__}')
        return 1
    for case in report['cases']:
        print(case['case_id'],case['behavior_result'],case['repeatability'])
    print(report['qualification_status'],report['reproducible_payload_sha256'])
    return 0 if all(c['behavior_result']=='PASS' for c in report['cases']) else 1


if __name__=='__main__': raise SystemExit(main())
