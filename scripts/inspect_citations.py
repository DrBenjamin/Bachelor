#!/usr/bin/env python3
import re, unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
bib=ROOT/'resources'/'references.bib'
qmd=ROOT/'Bachelor.qmd'
# parse bib to build lookup like earlier
text=bib.read_text(encoding='utf-8')
entries={}
for m in re.finditer(r'@\w+\{([^,]+),', text):
    key=m.group(1).strip()
    start=m.end()
    nxt=re.search(r'\n@', text[start:])
    block=text[start:start+nxt.start()] if nxt else text[start:]
    year_m=re.search(r"year\s*=\s*\{(20\d{2})\}", block)
    author_m=re.search(r"author\s*=\s*\{([^}]*)\}", block)
    editor_m=re.search(r"editor\s*=\s*\{([^}]*)\}", block)
    year=year_m.group(1) if year_m else None
    authors_raw=author_m.group(1) if author_m else (editor_m.group(1) if editor_m else '')
    entries[key]={'year':year,'authors_raw':authors_raw}
lookup={}
def normalize_text(s):
    s=s.replace('ä','ae').replace('Ä','Ae').replace('ö','oe').replace('ü','ue').replace('ß','ss').replace('æ','ae')
    s=''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    s=re.sub(r'[^0-9A-Za-z]','',s)
    return s
for k,v in entries.items():
    y=v['year']
    if y is None: continue
    authors=v['authors_raw']
    first=authors.split(' and ')[0].split(' & ')[0].strip()
    first_last=first.split(',')[0].strip()
    norm=normalize_text(first_last).lower()
    lookup.setdefault(y,[]).append((k,first_last,norm))

content=qmd.read_text(encoding='utf-8')
pat_narr=re.compile(r'([^\\n\\(]{1,80}?)\\\((20\\d{2})\\\)')
lead_strip={'nach','laut','vgl.','vgl','siehe','siehe:','in'}
count=0
for m in pat_narr.finditer(content):
    full=m.group(0)
    author_phrase=m.group(1).strip()
    year=m.group(2)
    if not re.search(r'[A-ZÄÖÜ][a-zäöüß]', author_phrase): continue
    ap=author_phrase.rstrip(' ,;:.')
    parts=ap.split()
    while parts and parts[0].lower().strip(' ,.:;') in lead_strip:
        parts.pop(0)
    if not parts: continue
    seg=' '.join(parts)
    seg=re.split(r',|\s+und\s+|\s+&\s+|\s+and\s+',seg)[0].strip()
    seg_parts=seg.split()
    if seg_parts[0].lower()=='von' and len(seg_parts)>1:
        candidate=' '.join(seg_parts[:2])
    else:
        candidate=seg_parts[0]
    print('FULL:',repr(full))
    print('AUTHOR_PHRASE:',repr(author_phrase),'YEAR:',year,'CAND:',candidate)
    count+=1
print('TOTAL',count)
