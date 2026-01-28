import os
import json

ctx_dir = 'rag_server/indexing/contexts'
files = [f for f in os.listdir(ctx_dir) if f.endswith('.json')]
print(f'Total contexts: {len(files)}\n')

for f in sorted(files):
    with open(os.path.join(ctx_dir, f)) as fp:
        data = json.load(fp)
        tiers = list(data['tiers'].keys())
        total_urls = sum(len(t.get('urls', [])) + len(t.get('items', [])) for t in data['tiers'].values())
        tier_names = ', '.join([t.replace('tier', 'T').replace('_', ' ') for t in tiers])
        ctx_name = data['context']
        print(f'{ctx_name:12} {len(tiers)} Tiers ({total_urls:3} URLs): {tier_names}')
