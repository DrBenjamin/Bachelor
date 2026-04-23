#!/usr/bin/env python3
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIB = ROOT / 'resources' / 'references.bib'
QMD = ROOT / 'Bachelor.qmd'
BACKUP = ROOT / 'Bachelor.qmd.bak'

def normalize_text(s):
    # replace common German chars with ASCII equivalents
    s = s.replace('ä','ae').replace('Ä','Ae')
    s = s.replace('ö','oe').replace('Ö','Oe')
    s = s.replace('ü','ue').replace('Ü','Ue')
    s = s.replace('ß','ss')
    s = s.replace('æ','ae').replace('Æ','Ae')
    s = s.replace('\u2013','-')
    # remove diacritics
    s = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    # remove punctuation
    s = re.sub(r"[^0-9A-Za-z]","",s)
    return s

# Parse bib file entries: key, year, and raw author string
bib = BIB.read_text(encoding='utf-8')
entries = {}
for m in re.finditer(r"@\w+\{([^,]+),", bib):
    key = m.group(1).strip()
    start = m.end()
    # find end of entry (next @ or end)
    nxt = re.search(r"\n@", bib[start:])
    if nxt:
        block = bib[start:start+nxt.start()]
    else:
        block = bib[start:]
    year_m = re.search(r"year\s*=\s*\{(20\d{2})\}", block)
    author_m = re.search(r"author\s*=\s*\{([^}]*)\}", block)
    editor_m = re.search(r"editor\s*=\s*\{([^}]*)\}", block)
    year = year_m.group(1) if year_m else None
    authors_raw = author_m.group(1) if author_m else (editor_m.group(1) if editor_m else '')
    entries[key] = {'year': year, 'authors_raw': authors_raw}

# Build lookup: year -> list of (key, normalized authors)
lookup = {}
for k,v in entries.items():
    y = v['year']
    if y is None: continue
    authors = v['authors_raw']
    # take first author (before ' and ' or ' & ')
    first = authors.split(' and ')[0].split(' & ')[0].strip()
    # sometimes authors are in form Last, First; take last name
    first_last = first.split(',')[0].strip()
    norm = normalize_text(first_last).lower()
    lookup.setdefault(y, []).append((k, first_last, norm))

content = QMD.read_text(encoding='utf-8')
orig = content
replacements = []

# 1) Parenthetical citations like \(Author, 2019\)
pat_paren = re.compile(r"\\\(([^\\)]+?),\s*(20\d{2})\\\)")

def find_key_for(author_text, year):
    # cleanup escaped chars
    a = author_text.replace('\\-','-').replace('\\','').strip()
    # if multiple authors separated by '&' or ' & ' or ' und '
    a_simple = re.split(r'\\s*(?:&|and|und)\\s*', a)[0]
    # if comma-separated list, take first last name
    a_simple = a_simple.split(',')[0].strip()
    norm = normalize_text(a_simple).lower()
    candidates = lookup.get(year, [])
    matches = [c for c in candidates if c[2].startswith(norm) or norm in c[2] or normalize_text(c[1]).lower().startswith(norm)]
    if len(matches) == 1:
        return matches[0][0]
    # fallback: try key contains norm
    for c in candidates:
        if norm in c[0].lower():
            return c[0]
    return None

new_content = content
for m in list(pat_paren.finditer(content)):
    full = m.group(0)
    author_text = m.group(1)
    year = m.group(2)
    key = find_key_for(author_text, year)
    if key:
        new = f'[@{key}]'
        new_content = new_content.replace(full, new)
        replacements.append((full, new))
    else:
        # skip if no key found
        pass

# 2) Narrative citations like 'Author (2012)' -> 'Author [@Key]'
# We try to be conservative: capture a short author phrase before the parenthesized year,
# strip common leading words (e.g., 'Nach', 'Laut'), then pick the first author name
# (handles 'Strotbaum und Reiß (2017)' -> 'Strotbaum und Reiß [@Strotbaum2017]')
pat_narr = re.compile(r"([^\\n\\(]{1,80}?)\\\((20\\d{2})\\\)")
lead_strip = {'nach','laut','vgl.','vgl','siehe','siehe:','in'}
for m in list(pat_narr.finditer(new_content)):
    full = m.group(0)
    author_phrase = m.group(1).strip()
    year = m.group(2)
    # quick guard: must contain at least one uppercase word (likely a name)
    if not re.search(r"[A-ZÄÖÜ][a-zäöüß]", author_phrase):
        continue
    # remove trailing punctuation/spaces
    author_phrase = author_phrase.rstrip(' ,;:.')
    parts = author_phrase.split()
    # remove common leading words
    while parts and parts[0].lower().strip(" ,.:;") in lead_strip:
        parts.pop(0)
    if not parts:
        continue
    # form candidate: take first author segment (before ',', 'und', '&', 'and')
    seg = ' '.join(parts)
    seg = re.split(r",|\s+und\s+|\s+&\s+|\s+and\s+", seg)[0].strip()
    # handle 'von ' prefix
    seg_parts = seg.split()
    if seg_parts[0].lower() == 'von' and len(seg_parts) > 1:
        candidate = ' '.join(seg_parts[:2])
    else:
        candidate = seg_parts[0]
    key = find_key_for(candidate, year)
    if key:
        # replace only the trailing ' (YEAR)'
        replaced = author_phrase + ' [@' + key + ']'
        new_content = new_content.replace(full, replaced)
        replacements.append((full, replaced))

# write backup and new file
if new_content == orig:
    print('No replacements made.')
else:
    BACKUP.write_text(orig, encoding='utf-8')
    QMD.write_text(new_content, encoding='utf-8')
    print(f'Made {len(replacements)} replacements. Backup at {BACKUP}')
    for old,new in replacements:
        print('REPL:', old[:80].replace('\n',' '), '->', new[:80].replace('\n',' '))
