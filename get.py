#!/usr/bin/env python
# SPDX-FileCopyrightText: 2026 Intevation GmbH <https://intevation.de>
# SPDX-License-Identifier: Apache-2.0

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from github import ContentFile, Github, Repository


def is_readme(file: ContentFile.ContentFile):
    return file.type == 'file' and file.name in ['README.md', 'README', 'README.txt', 'README.rst']

def get_first_heading(content: str):
    lines = content.split('\n')
    for i in range(1, 4):
        for line in lines:
            s = '#' * i
            s += ' '
            if line.startswith(s):
                return line[i + 1:]
    return ''

def get_all_headings(content: str):
    res = []
    lines = content.split('\n')
    for i in range(1, 6):
        for line in lines:
            s = '#' * i
            s += ' '
            if line.startswith(s):
                res.append((line[i + 1:], i))
    return res

def simple_gen_toc(content: str, skip_first: bool):
    entries = get_all_headings(content)
    toc = []
    linked = set()
    for entry, depth in entries:
        lnk = entry.lower().replace(' ', '-')
        dup = 0
        while lnk in linked:
            dup += 1
            lnk = entry.lower().replace(' ', '-').append(f'-{dup}')
        linked.add(lnk)
        prefix = '  ' * (depth - 1)
        toc.append(f'{prefix}- [{entry}](#{entry.lower().replace(' ', '-').replace('(', '').replace(')', '')})')
    if skip_first:
        return toc[1:]
    return toc

def simple_insert_toc(content: str, has_mapping: bool):
    toc = simple_gen_toc(content, False)
    toc.append('- [Registry Information](#__reg)')
    if has_mapping:
        toc.append('- [Mapping Information](#__map)')
    toc.extend(['', ''])
    lines = [x.strip() for x in content.split('\n')]
    lines[1:1] = toc
    return '\n'.join(lines)

def load_registry(repo: Repository.Repository, path: str):
    res = {}
    has_schema = False
    for entry in repo.get_contents(path):
        if entry.type == 'file' and entry.name in ['mapping.json', 'registry.json']:
            res[Path(entry.name).stem.lower()] = json.loads(entry.decoded_content.decode('utf-8'))
        elif is_readme(entry):
            res[Path(entry.name).stem.lower()] = entry.decoded_content.decode('utf-8')
        elif entry.type == 'dir' and entry.name == 'schema':
            has_schema = True
    if not has_schema:
        return res
    for entry in repo.get_contents(f'{path}/schema'):
        if entry.type == 'file' and entry.name in ['mapping.schema.json', 'registry.schema.json']:
            key = Path(entry.name).stem.lower()
            res[key] = json.loads(entry.decoded_content.decode('utf-8'))
            if not 'last_updated' in res[key]:
                commits = repo.get_commits(path=entry.path)
                res[key]['__last_updated__'] = commits[0].commit.author.date
    return res

def now():
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z')

def create_hugo_data(data: dict):
    gitignore = []
    gi = Path('.gitignore')
    if gi.exists() and gi.is_file():
        with gi.open() as f:
            gitignore = [x.strip() for x in f.readlines()]
    os.makedirs('content', exist_ok=True)
    for name, registry in data.items():
        updated = datetime.fromtimestamp(0, UTC)
        ignore_line = f'/content/{name}/'
        if name == '_index_':
            ignore_line = '/content/_index.md'
        if not ignore_line in gitignore:
            gitignore.append(ignore_line)
        if name == '_index_':
            with open('content/_index.md', 'w') as f:
                lines = [
                    '+++',
                    'title = \'CSAF Registries\'',
                    f'date = {now()}',
                    'type = \'page\'',
                    'layout = \'cust_index\'',
                    '+++',
                    f'{registry.get('readme', '')}'
                ]
                f.write('\n'.join(lines))
                f.write('\n')
            continue
        os.makedirs(f'content/{name}', exist_ok=True)
        for kind in ['registry', 'mapping', 'registry.schema', 'mapping.schema']:
            tmp = registry.get(kind, {}).get('last_updated', None)
            tmp2 = registry.get(kind, {}).get('__last_updated__', None)
            if tmp is not None:
                dt = datetime.fromisoformat(tmp)
                updated = max(dt, updated)
            elif tmp2 is not None:
                updated = max(tmp2, updated)
                del registry[kind]['__last_updated__']
            if kind in registry:
                os.makedirs(f'content/{name}/{kind}', exist_ok=True)
                with open(f'content/{name}/{kind}/index.json', 'w') as f:
                    json.dump(registry.get(kind), f, indent=2)
                    f.write('\n')
                lines = [
                    '+++',
                    f'title = \'{name}::{kind}.json\'',
                    f'date = {registry.get(kind, {}).get("last_updated", now())}',
                    '+++',
                    f'{{{{< highlight_source registry="{name}" src="{kind}" type="json" >}}}}'
                ]
                with open(f'content/{name}/{kind}/render.md', 'w') as f:
                    f.write('\n'.join(lines))
                    f.write('\n')
        if int(updated.timestamp()) == 0:
            updated = datetime.now(UTC)
        title = get_first_heading(registry['readme'])
        if len(title) == 0:
            title = f'Registry {name}'
        lines = [
            '+++',
            f'title = \'{title}\'',
            'type = \'page\'',
            'layout = \'combined\'',
            f'date = {registry.get("last_updated", updated.replace(microsecond=0).isoformat().replace('+00:00', 'Z'))}',
            '[params]',
            f'registry = \'{name}\'',
            '+++'
        ]
        with open(f'content/{name}/_index.md', 'w') as f:
            f.write('\n'.join(lines))
            f.write('\n')
    with gi.open('w') as f:
        f.write('\n'.join(gitignore))
        f.write('\n')

def main():
    gh = Github(lazy=True)
    repo = gh.get_repo('oasis-tcs/csaf')
    registries = {}
    for entry in repo.get_contents('registry'):
        if entry.type == 'dir':
            print(f'Downloading Registry {entry.name} from {repo.owner.login}/{repo.name}')
            key = entry.name.lower()
            registries[key] = load_registry(repo, f'registry/{entry.name}')
            if 'readme' in registries[key]:
                registries[key]['readme'] = simple_insert_toc(registries[key]['readme'], 'mapping' in registries[key])
        elif is_readme(entry):
            registries['_index_'] = {'readme': entry.decoded_content.decode('utf-8')}
    create_hugo_data(registries)
    os.makedirs('data', exist_ok=True)
    with open('data/registries.json', 'w') as f:
        json.dump(registries, f, indent=2)

if __name__ == '__main__':
    main()
