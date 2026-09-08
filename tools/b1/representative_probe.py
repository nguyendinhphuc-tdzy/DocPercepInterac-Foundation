"""Private-only evaluation CLI with an explicit safe public summary boundary."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from foundation.evaluation.perception import representative as rep
from tools.b1.verify_private_corpus_boundary import verify


def run(manifest_path, private_report, public_summary, repo=ROOT):
    repo = Path(repo).resolve()
    verify(repo, os.environ.get(rep.CORPUS_ENV))
    manifest_path = rep.private_path(manifest_path, repo)
    private_report = rep.private_path(private_report, repo)
    # Check actual ignore rules rather than assuming the private name is enough.
    for path in (manifest_path, private_report):
        check = subprocess.run(['git', '-C', str(repo), 'check-ignore', '-q', '--', str(path)], capture_output=True)
        if check.returncode != 0:
            raise rep.QualificationError('PRIVATE_METADATA_NOT_IGNORED')
    public_summary = Path(public_summary).resolve()
    allowed = repo / 'qualification/b1/representative/reports'
    if (allowed.resolve() != allowed or not public_summary.is_relative_to(allowed)
            or public_summary.suffix != '.json' or public_summary.is_symlink()):
        raise rep.QualificationError('PUBLIC_OUTPUT_BOUNDARY')
    root = rep.corpus_root(repo)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if root is not None else None
    full = rep.evaluate(manifest, repo)
    public = rep.sanitize(full)
    if root is not None:
        # New run path required; prior private evidence is never overwritten.
        private_report.parent.mkdir(parents=True, exist_ok=True)
        with private_report.open('x', encoding='utf-8') as stream:
            json.dump(full, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
    public_summary.parent.mkdir(parents=True, exist_ok=True)
    public_summary.write_text(json.dumps(public, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return public


def main():
    parser = argparse.ArgumentParser(description='Private B1.2R evaluation; never prints private input identifiers.')
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--private-report', type=Path, required=True)
    parser.add_argument('--public-summary', type=Path, required=True)
    args = parser.parse_args()
    try:
        public = run(args.manifest, args.private_report, args.public_summary)
    except Exception:
        print('REPRESENTATIVE_EVALUATION_REFUSED: inspect private configuration locally; details withheld', file=sys.stderr)
        return 1
    print(public['corpus_status'], public['decision'], 'cases=' + str(len(public['cases'])))
    return 0  # A lack of evidence is a reported outcome, not a fabricated pass.


if __name__ == '__main__':
    raise SystemExit(main())
