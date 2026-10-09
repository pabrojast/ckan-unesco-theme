"""Despliega sólo CKAN preview con comparación de versión y rollback acotado."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.request

NAMESPACE = 'ckan-preview'
HOST = 'https://preview.dev-wins.com'
IMAGE = re.compile(r'ghcr\.io/pabrojast/ckan-theme-preview@sha256:[0-9a-f]{64}')


def kube(*args):
    return subprocess.check_output(['kubectl', '-n', NAMESPACE, *args], text=True)


def current():
    return json.loads(kube('get', 'deployment', 'ckan', '-o', 'json'))


def container(deployment):
    return next((i, c) for i, c in enumerate(deployment['spec']['template']['spec']['containers']) if c['name'] == 'ckan')


def patch(deployment, image, annotations):
    i, c = container(deployment)
    ops = [
        {'op': 'test', 'path': '/metadata/resourceVersion', 'value': deployment['metadata']['resourceVersion']},
        {'op': 'test', 'path': f'/spec/template/spec/containers/{i}/image', 'value': c['image']},
        {'op': 'replace', 'path': f'/spec/template/spec/containers/{i}/image', 'value': image},
        {'op': 'add', 'path': '/metadata/annotations', 'value': {**deployment['metadata'].get('annotations', {}), **annotations}},
    ]
    kube('patch', 'deployment', 'ckan', '--type=json', '-p', json.dumps(ops))
    kube('rollout', 'status', 'deployment/ckan', '--timeout=900s')


def smoke(sha):
    version = json.load(urllib.request.urlopen(HOST + '/__preview/version', timeout=45))
    if version.get('theme_sha') != sha:
        raise RuntimeError('Live theme SHA differs from the requested commit')
    for path in ['/', '/dataset/', '/organization/', '/group/', '/data-stories/', '/terria/', '/api/3/action/status_show']:
        with urllib.request.urlopen(HOST + path, timeout=90) as r:
            if r.status != 200 or 'noindex' not in r.headers.get('X-Robots-Tag', ''):
                raise RuntimeError('Smoke failed: ' + path)
    pods = json.loads(kube('get', 'pods', '-l', 'app.kubernetes.io/name=ckan', '-o', 'json'))
    for pod in pods['items']:
        if pod['metadata'].get('deletionTimestamp'):
            continue
        if any(c.get('restartCount', 0) for c in pod.get('status', {}).get('containerStatuses', [])):
            raise RuntimeError('New CKAN container restarted')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--image')
    p.add_argument('--sha')
    p.add_argument('--rollback', action='store_true')
    a = p.parse_args()
    identity = json.loads(kube('get', 'configmap', 'preview-identity', '-o', 'json'))['data']
    if identity != {'host': 'preview.dev-wins.com', 'namespace': NAMESPACE, 'clusterUID': '181dc298-2adb-48f5-9d78-8fbe4a340795'}:
        raise SystemExit('Preview identity mismatch')
    deployment = current()
    annotations = deployment['metadata'].get('annotations', {})
    if a.rollback:
        a.image = annotations.get('preview.dev-wins.com/previous-image', '')
        a.sha = annotations.get('preview.dev-wins.com/previous-sha', '')
    if not IMAGE.fullmatch(a.image or '') or not re.fullmatch(r'[0-9a-f]{40}', a.sha or ''):
        raise SystemExit('Only a preview digest and full theme SHA are accepted')
    if not a.rollback:
        head = subprocess.check_output(['git', 'ls-remote', 'https://github.com/pabrojast/ckan-unesco-theme.git', 'refs/heads/preview'], text=True).split()[0]
        if head != a.sha:
            print('Superseded commit; skipped without changing preview')
            return
    previous = container(deployment)[1]['image']
    previous_sha = annotations.get('preview.dev-wins.com/theme-sha', '')
    new_annotations = {'preview.dev-wins.com/theme-sha': a.sha, 'preview.dev-wins.com/previous-image': previous, 'preview.dev-wins.com/previous-sha': previous_sha}
    try:
        patch(deployment, a.image, new_annotations)
        smoke(a.sha)
    except Exception:
        live = current()
        if container(live)[1]['image'] == a.image:
            patch(live, previous, annotations)
        raise
    summary = f'Preview: {HOST}\nTheme: `{a.sha}`\nImage: `{a.image}`\nSmoke checks: passed\n'
    print(summary)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as f:
            f.write(summary)


if __name__ == '__main__':
    main()
