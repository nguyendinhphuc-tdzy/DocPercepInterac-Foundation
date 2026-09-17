"""Render an immutable private mapping result into a human review handoff."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from tools.b2.gtps_mapping_probe import private_path
from tools.b1.verify_private_corpus_boundary import verify


def render(result, result_digest):
    concrete=[i for i in result['items'] if i['change_proposal']]
    lines=['# B2.1R — Private mapping evidence review v2', '',
        '**Machine-prepared mapping evidence; no human approval or qualification decision.**', '',
        'B21_BASELINE_SHA: `43945769c77841498af10b13d278740a3c53ad48`',
        f'Result SHA-256: `{result_digest}`',
        f"Configuration digest: `{result['configuration_digest']}`", '',
        '## Review summary', '',
        f'- Mapping intents: {len(result["items"])}.',
        f'- Concrete DRAFT ChangeProposals / exact target projections: {len(concrete)}.',
        f'- Unresolved proposal projections: {len(result["items"])-len(concrete)}.',
        '- Executable proposals: 0. Golden-dependent proposals: 0.',
        '- Golden comparison: NOT_EVALUATED; Golden was not supplied to mapping.',
        '- These are configured mapping candidates. Business correctness still requires mapping evidence review.', '',
        '## Limits the reviewer must retain', '',
        '- UNKNOWN package conformance remains unchanged. Read-only Transitional main-body identities do not qualify Replay.',
        '- Cover year-ended text is a Word field result: UNSUPPORTED. The Section 7 fiscal-year cell is a separate resolved occurrence.',
        '- Historical financial values are image-based and were not inferred. Historical financial/NCP context plus explicit Template metrics and current values make this NON_BLOCKING_FOR_BOUNDED_MAPPING.',
        '- NCP is the exact current decimal ratio; percent display and calculation-cache freshness are not qualified.',
        '- Historical relationships absent from Other RPT rows remain unobserved. Current relationship codes are proposed as observed.',
        '- New Other RPT narrative remains REVIEW_REQUIRED. No contract wording, pricing policy or benchmarking conclusion is invented.',
        '- Removed means absent from the bounded current inventory, not an authorized row deletion.',
        '- RPT and FS interest amounts have distinct source contexts; no global authority/reconciliation conclusion is made.',
        '- Existing unused Template rows are preserved. No row insertion, removal, approval, mutation or document output.',
        '- Period coverage is limited to the explicitly listed occurrences; headers/footers and other Word field occurrences are deferred.',
        '- Definition/RulePack references remain evaluation configuration, not production-registered control-plane records.', '',
        '## Row capacity and configuration evidence', '',
        'Transaction under Review is first; other transactions use descending amount from the bound Template materiality guidance. No discretionary grouping or tie-breaking is inferred.',
        '```json',json.dumps(result.get('row_allocation'),ensure_ascii=False,indent=2),'```','',
        '## Exact Run-003 binding', '', '```json',json.dumps(result['run003_bindings'],indent=2),'```','',
        '## Native identity profile and preflight', '', '```json',
        json.dumps({'preflight':result.get('native_preflight'),'profile':result.get('native_fingerprint_profile')},indent=2),'```','',
        '## Detailed narrative regions', '',
        'These are separate navigation candidates, not narrative ChangeProposals. Summary-container proposals below are independently bound.', '']
    for key,entry in result.get('detailed_regions',{}).items():
        lines.extend([f'### {key}', '', '```json',json.dumps(entry,ensure_ascii=False,indent=2),'```',''])
    lines.extend(['## Per-occurrence evidence chain', ''])
    for item in result['items']:
        status='RESOLVED' if item['change_proposal'] else ('UNSUPPORTED' if 'NATIVE_STRUCTURE_UNSUPPORTED' in item['warnings'] else 'REVIEW_REQUIRED')
        lines.extend([f"### {item['business_target_id']} / {item['target_region']['object_id']}", '',f'**{status} — human mapping review pending**', ''])
        for title,value in [
            ('CURRENT SOURCE FACT',item['source_fact']),('HISTORICAL CONTEXT',item['historical_context']),
            ('BUSINESS TARGET / TEMPLATE REGION',{'business_target_id':item['business_target_id'],'target_region':item['target_region'],'semantic_region':item['projection']['semantic_region']}),
            ('EXACT NATIVE LOCATOR',item['native_locator_candidate']),
            ('PROPOSED CHANGE',{'existing_content':item['existing_target_content'],'proposed_content':item['proposed_content'],
                'changes':item['change_types'],'rationale':item['mapping_rationale'],'warnings':item['warnings'],'change_proposal':item['change_proposal']}),
            ('VIEWER HIGHLIGHT PROJECTION',item['projection'])]:
            lines.extend([f'**{title}**','', '```json',json.dumps(value,ensure_ascii=False,indent=2),'```',''])
    lines.extend(['## Structured exceptions', '', '```json',json.dumps(result['exceptions'],ensure_ascii=False,indent=2),'```','',
        '## Next gate', '', 'Review aliases, row allocation, numeric lineage, target occurrences and proposal payloads. No proposals are approved. B2.2, ApprovedChangeSet, DOCX Replay and First Draft output remain unauthorized.', ''])
    return '\n'.join(lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--result',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();verify(Path(__file__).resolve().parents[2])
    data=private_path(args.result).read_bytes();result=json.loads(data)
    output=private_path(args.output,output=True)
    with output.open('x',encoding='utf-8') as f:f.write(render(result,sha256(data).hexdigest()))
    print('Private mapping review handoff created; no approval or qualification promotion.')


if __name__=='__main__':
    try:main()
    except Exception:
        print('PRIVATE_REVIEW_RENDER_REFUSED: no private details published.')
        raise SystemExit(1)
