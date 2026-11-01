"""Add omitted reporting metadata without modifying the execution manifest."""

import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent


def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def producer(spec):
    path = Path(spec['path'])
    if digest(path) != spec['sha256']:
        raise ValueError(f'preparation receipt drift: {path}')
    return json.loads(path.read_text())


source = BASE / 'jobs-profiles.json'
original = json.loads(source.read_text())
value = json.loads(source.read_text())
prepared = value['prepared_inputs']
metadata = {row['dataset_id']: row for row in producer(prepared['archived'])['datasets']}
metadata.update({key: producer(spec) for key, spec in prepared['C'].items()})
for job in value['jobs']:
    record = metadata[job['dataset_id']]
    fields = ['site_count', 'observations_sha256']
    if job['arm'] != 'C':
        fields.append('source_observations_sha256')
    for field in fields:
        if field in job and job[field] != record[field]:
            raise ValueError(f'conflicting reporting metadata: {job["job_id"]} {field}')
        job[field] = record[field]
    if job['input_sha256'][job['observations']] != job['observations_sha256']:
        raise ValueError('prepared observation differs from execution binding')
    prior = next(row for row in original['jobs'] if row['job_id'] == job['job_id'])
    if any(job[key] != entry for key, entry in prior.items()):
        raise ValueError('original execution field changed')
value['execution_manifest'] = {'path': str(source), 'sha256': digest(source)}
target = BASE / 'jobs-summary.json'
with target.open('x') as handle:
    json.dump(value, handle, indent=2)
    handle.write('\n')
print(json.dumps({'path': str(target), 'sha256': digest(target), 'jobs': len(value['jobs'])}))
