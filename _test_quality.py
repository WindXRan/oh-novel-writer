"""Quality check on ch1-3"""
import json, sys
sys.path.insert(0, '.agents/skills/story-engine/tools')
from pathlib import Path
from lib.text_metrics import count_metrics
from lib.plagiarism import find_plagiarism
from lib.source_locator import get_source_text

cfg = json.loads(open('configs/config_rewrite_豪门小娇妻.json', encoding='utf-8').read())
base = Path(cfg['rewrites_dir'])

for ch in [1, 2, 3]:
    chf = base / 'chapters' / f'ch_{ch:03d}.txt'
    if not chf.exists():
        print(f'ch{ch}: MISSING')
        continue
    text = chf.read_text(encoding='utf-8')
    metrics = count_metrics(text)
    print(f'=== ch{ch} ===')
    print(f'  总字数: {metrics["chars"]}')
    print(f'  ai_markers: {metrics["ai_markers"]}')
    from lib.constants import AI_MARKERS
    import re
    traces = []
    for m in AI_MARKERS:
        pat = r'(?:^|[\n。！？])\s*' + re.escape(m)
        f = re.findall(pat, text)
        if f:
            traces.append(f'{m}x{len(f)}')
    print(f'  ai_traces: {traces}')
    print(f'  metaphore: {metrics["metaphor"]}')
    print(f'  emotion: {metrics["direct_emotion"]}')

    # Check plagiarism
    try:
        src = get_source_text(cfg, ch)
        if src:
            plags = find_plagiarism(text, src)
            print(f'  plagiarism: {len(plags)}')
            for p in plags[:3]:
                print(f'    -> \"{p["text"]}\"')
    except Exception as e:
        print(f'   plagiarism check failed: {e}')
    
    # Show first 200 chars
    print(f'  开头: {text[:100]}...')
    print()

# Also check the plot_guides for abstraction quality
print('\\n=== Plot Guide Abstraction Check ===')
for ch in [1, 2, 3]:
    gf = base / 'guides' / f'plot_{ch}.md'
    if gf.exists():
        content = gf.read_text(encoding='utf-8')
        # Check if it has concrete details (bad) or abstract (good)
        print(f'plot_{ch}.md: {len(content)} chars')
        # Sample
        lines = content.strip().split('\\n')
        for L in lines[:5]:
            print(f'  {L}')
        print()
