"""Check genre info available to prompts"""
import json

cfg = json.loads(open('configs/config_rewrite_豪门小娇妻.json', encoding='utf-8').read())
bd_path = cfg['rewrites_dir'] + '/book_data.json'
bd = json.loads(open(bd_path, encoding='utf-8').read())

# Check book_info.md for genre info
import os
info_path = cfg['rewrites_dir'] + '/settings/book_info.md'
if os.path.exists(info_path):
    content = open(info_path, encoding='utf-8').read()
    for line in content.split('\n'):
        if '品类' in line or '题材' in line or 'genre' in line.lower():
            print(line.strip())

# Check what config provides
print()
for k in ['source_book_name', 'new_book_name', 'author']:
    print(f'config.{k} = {cfg.get(k, "N/A")}')

# Look at source_analysis for genre description
sa_path = cfg['rewrites_dir'] + '/settings/source_analysis.md'
if os.path.exists(sa_path):
    content = open(sa_path, encoding='utf-8').read()[:500]
    print(f'\nsource_analysis.md (first 500 chars):\n{content}')
