"""Validación previa a la creación y separación de tipos/identidades de recursos."""
import uuid

import pytest

from ckanext.theme_ejemplo import ihpix_resources as R


def payload(kind='dataset', **overrides):
    data = dict(kind=kind, title='Water monitoring', organization='org', description='A report',
                contact_email='author@example.org', visibility='private', license_id='notspecified',
                source_kind='url', source_url='https://example.org/data.csv',
                request_id=str(uuid.uuid4()), start_date='2026-11-06', end_date='2026-11-07',
                event_format='online', dcat_type='dataset', topic='inlandWaters')
    data.update(overrides)
    return data


def test_dataset_uses_data_files_and_explicit_visibility():
    clean = R.validate(payload(source_kind='file'), ['org'], 'measurements.nc', 100)
    assert clean['upload_filename'] == 'measurements.nc'
    assert clean['visibility'] == 'private'
    assert clean['kind'] == 'dataset'


@pytest.mark.parametrize('changes,field', [({'organization':'other'},'organization'),
    ({'title':''},'title'), ({'description':''},'description'),
    ({'contact_email':'invalid'},'contact_email'), ({'visibility':'unexpected'},'visibility'),
    ({'request_id':'bad'},'request_id'), ({'source_url':'javascript:alert(1)'},'source'),
    ({'source_kind':'none'},'source'), ({'license_id':''},'license_id'),
    ({'dcat_type':''},'dcat_type'), ({'topic':''},'topic')])
def test_invalid_dataset_cannot_reach_creation(changes, field):
    with pytest.raises(R.InputError) as error:
        R.validate(payload(**changes), ['org'])
    assert field in error.value.errors


def test_file_type_and_size_are_checked_server_side():
    with pytest.raises(R.InputError):
        R.validate(payload(source_kind='file'), ['org'], 'program.exe', 100)
    with pytest.raises(R.InputError):
        R.validate(payload(source_kind='file'), ['org'], 'data.csv', 51 * 1024 * 1024)
    with pytest.raises(R.InputError):
        R.validate(payload('event', source_kind='file'), ['org'], 'agenda.pdf', 21 * 1024 * 1024)


def test_event_allows_no_file_and_keeps_native_review_workflow():
    clean = R.validate(payload('event', source_kind='none', description='<script>alert(1)</script>\nAgenda'), ['org'])
    values = R.event_payload(clean, 'Institute', 'event-qa')
    assert values['page_type'] == 'water-events'
    assert values['private'] is True and values['submission_action'] == 'submit'
    assert values['publish_date'] == '2026-11-06'
    assert '<script>' not in values['content']
    assert '&lt;script&gt;' in values['content']


@pytest.mark.parametrize('changes,field', [({'start_date':''},'start_date'),
    ({'start_date':'2026-02-30'},'start_date'), ({'end_date':'2026-11-05'},'end_date'),
    ({'registration_url':'javascript:alert(1)'},'registration_url'),
    ({'event_format':'wrong'},'event_format')])
def test_event_fields_validated_before_upload(changes, field):
    with pytest.raises(R.InputError) as error:
        R.validate(payload('event', **changes), ['org'])
    assert field in error.value.errors


def test_retry_identity_does_not_mix_users_or_resource_types():
    request_id = str(uuid.uuid4())
    first = R.content_identity('author', 'dataset', request_id)
    assert first == R.content_identity('author', 'dataset', request_id)
    assert first != R.content_identity('other', 'dataset', request_id)
    assert first != R.content_identity('author', 'event', request_id)


def test_dates_are_compared_after_normalization():
    clean = R.validate(payload('event', start_date='2026-2-1', end_date='2026-11-06'), ['org'])
    assert clean['start_date'] == '2026-02-01'
