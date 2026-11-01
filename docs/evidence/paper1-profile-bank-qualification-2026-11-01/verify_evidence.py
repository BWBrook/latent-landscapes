from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path.cwd()
ARCHIVE = Path(__file__).resolve().parent
CACHE = {}


def sha(path):
    resolved = path.resolve()
    if resolved not in CACHE:
        digest = hashlib.sha256()
        with resolved.open('rb') as handle:
            for chunk in iter(lambda:handle.read(1024*1024),b''):
                digest.update(chunk)
        CACHE[resolved] = digest.hexdigest()
    return CACHE[resolved]


def bindings(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {'source_input_sha256','source_sha256','input_sha256','verified_provenance_sha256'} and isinstance(child,dict):
                for path,digest in child.items():
                    if isinstance(digest,str) and len(digest)==64:
                        yield path,digest
            else:
                yield from bindings(child)
        for path_key,hash_key in [('path','sha256'),('raw_path','raw_sha256'),
                                  ('compressed_path','compressed_sha256'),
                                  ('manifest_path','manifest_sha256')]:
            if isinstance(value.get(path_key),str) and isinstance(value.get(hash_key),str):
                yield value[path_key],value[hash_key]
    elif isinstance(value,list):
        for child in value:
            yield from bindings(child)


def main():
    snapshots = {sha(p):p for p in (ARCHIVE/'source').glob('*.py')}
    checked = []
    scopes = []
    for path in sorted(ARCHIVE.rglob('*.json')):
        if path.name=='verification.json':
            continue
        data=json.loads(path.read_text())
        for name,digest in sorted(set(bindings(data))):
            target=Path(name)
            if not target.is_absolute():
                target=ROOT/target
            current=target.is_file() and sha(target)==digest
            snapshot=None if current else snapshots.get(digest)
            checked.append({'receipt':str(path.relative_to(ARCHIVE)), 'path':name,
                            'expected_sha256':digest,'verified':bool(current or snapshot is not None),
                            'historical_snapshot':None if snapshot is None else str(snapshot.relative_to(ARCHIVE))})
        if data.get('schema')=='spatial-profile-qualification-v1':
            scopes.append({'receipt':str(path.relative_to(ARCHIVE)),'status':data['status'],
                           'scope_valid':data['profile_certified'] is False and data['calibration_claim'] is False
                            and data['data_identity']['training_site_count']==120,
                           'role':data['bank_identity']['role']})
    payload={str(p.relative_to(ARCHIVE)):sha(p) for p in sorted(ARCHIVE.rglob('*'))
             if p.is_file() and p.name!='verification.json' and '__pycache__' not in p.parts}
    result={'schema':'profile-bank-evidence-verification-v1',
            'generated_utc':datetime.now(UTC).isoformat(),
            'bindings':checked,'profile_scope_checks':scopes,
            'all_bindings_verified':all(row['verified'] for row in checked),
            'all_profile_scopes_valid':all(row['scope_valid'] for row in scopes),
            'payload_sha256':payload}
    (ARCHIVE/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'bindings':len(checked),'profiles':len(scopes),
                      'all_bindings_verified':result['all_bindings_verified'],
                      'all_profile_scopes_valid':result['all_profile_scopes_valid']}))
    if not result['all_bindings_verified'] or not result['all_profile_scopes_valid']:
        raise SystemExit(1)


if __name__=='__main__':
    main()
