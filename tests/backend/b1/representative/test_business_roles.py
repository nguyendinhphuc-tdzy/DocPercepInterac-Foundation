"""Synthetic v1.2.0 role/scope/privacy regression; no business approval."""
from copy import deepcopy
import json

import pytest
from foundation.evaluation.perception import representative as rep
from tests.backend.b1.representative.test_representative import manifest, result, completed_full

ROLES = {'TARGET_TEMPLATE': 'TARGET', 'HISTORICAL_REFERENCE': 'REFERENCE',
         'GOLDEN_EVALUATION_ONLY': 'REFERENCE', 'CURRENT_SOURCE': 'SOURCE',
         'HISTORICAL_SOURCE': 'SOURCE'}


@pytest.mark.parametrize('business_role,expected', ROLES.items())
@pytest.mark.parametrize('document_role', ['TARGET', 'REFERENCE', 'SOURCE'])
def test_closed_role_combinations(business_role, expected, document_role):
    value = manifest()
    value['evaluation_version'] = '1.2.0'
    value['cases'][0].update(business_role=business_role, document_role=document_role)
    if document_role == expected:
        rep.validate_manifest(value)
    else:
        with pytest.raises(rep.QualificationError):
            rep.validate_manifest(value)


@pytest.mark.parametrize('invalid', [None, 'SECRET_CLIENT_ROLE'])
def test_missing_or_unknown_role_fails_closed(invalid):
    value = manifest()
    if invalid is None:
        value['cases'][0].pop('business_role', None)
    else:
        value['cases'][0]['business_role'] = invalid
    with pytest.raises(rep.QualificationError):
        rep.validate_manifest(value)


def test_business_role_changes_scope_without_document_category_change():
    value = completed_full()['manifest']
    value['cases'][0].update(document_role='REFERENCE', business_role='HISTORICAL_REFERENCE')
    value['coverage_review']['scope_digest'] = rep.coverage_scope_digest(value)
    assert rep.coverage_review_valid(value)
    value['cases'][0]['business_role'] = 'GOLDEN_EVALUATION_ONLY'
    assert not rep.coverage_review_valid(value)


@pytest.mark.parametrize('business_role,category', ROLES.items())
def test_public_roles_are_allowlisted_metadata_only(business_role, category):
    case = result()
    case.update(business_role=business_role, document_role=category)
    value = {'evaluation_version': '1.2.0', 'corpus_status': 'AVAILABLE',
             'cases': [case], 'manifest': manifest()}
    public = rep.sanitize(value)
    assert public['evaluation_version'] == '1.2.0'
    assert public['cases'][0]['business_role_category'] == business_role
    assert public['cases'][0]['document_role_category'] == category
    assert public['production_qualified'] is False
    for secret in ('SECRET', case['input_sha256'], case['observation_digest']):
        assert secret not in json.dumps(public)
    case['business_role'] = 'PRIVATE_CLIENT_ROLE'
    with pytest.raises(rep.QualificationError):
        rep.sanitize(value)


def test_golden_cannot_be_projected_as_target_or_source():
    for category in ('TARGET', 'SOURCE'):
        case = result()
        case.update(business_role='GOLDEN_EVALUATION_ONLY', document_role=category)
        with pytest.raises(rep.QualificationError):
            rep.sanitize({'corpus_status': 'AVAILABLE', 'cases': [case], 'manifest': manifest()})


def test_old_evidence_is_not_silently_migrated():
    value = manifest()
    value['evaluation_version'] = '1.1.0'
    original = deepcopy(value)
    with pytest.raises(rep.QualificationError):
        rep.validate_manifest(value)
    with pytest.raises(rep.QualificationError):
        rep.sanitize({'evaluation_version': '1.1.0', 'corpus_status': 'AVAILABLE',
                      'cases': [result()], 'manifest': value})
    assert value == original
