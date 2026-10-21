"""Independent static checks for a prototype or complete localization."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import struct
import unicodedata
from PIL import Image
from build_locale import ROOT, load

TOKENS = re.compile(r'%[A-Z_]+%|\\(?:g[a-z_]+>?|<advance>?|.)')

def chunks(raw):
    assert raw[:4] == b'FORM' and struct.unpack_from('<I',raw,4)[0] == len(raw)-8
    result, pos = {}, 8
    while pos < len(raw):
        tag, length = struct.unpack_from('<4sI',raw,pos)
        result[tag.decode('ascii')] = (pos+8, length)
        pos += 8+length
    assert pos == len(raw)
    return result

def fonts(raw):
    u32=lambda p:struct.unpack_from('<I',raw,p)[0]
    start,_=chunks(raw)['FONT']
    result=[]
    for i in range(u32(start)):
        p=u32(start+4+i*4); sp=u32(p)
        name=raw[sp:raw.index(b'\0',sp)].decode('utf-8')
        count=u32(p+48)
        glyphs={}
        for j in range(count):
            gp=u32(p+52+j*4)
            cp,x,y,w,h,shift,off=struct.unpack_from('<5H2h',raw,gp)
            assert cp not in glyphs
            kern_count=struct.unpack_from('<H',raw,gp+14)[0]
            glyphs[cp]=(x,y,w,h,shift,off,raw[gp+16:gp+16+4*kern_count].hex())
        # RangeEnd may legitimately grow when adding Korean to the Latin title.
        result.append((name, glyphs, raw[p+8:p+20].hex()+raw[p+22:p+24].hex()+raw[p+32:p+48].hex()))
    return result

def check(release=False):
    build=ROOT/'private/build'
    mode=load(build/'locale-mode.json')
    original=ROOT/'private/original'
    base=json.loads((original/'loc/fr-FR.json').read_text(encoding='utf-8'))
    locale=load(build/'loc'/mode['locale'])
    errors=[]
    if list(locale)!=list(base):errors.append('Locale source keys/order changed')
    for key,value in locale.items():
        if not isinstance(value,str):errors.append('Non-string value: '+key)
        if value != unicodedata.normalize('NFC',value):errors.append('Not NFC: '+key)
        source_tokens,target_tokens=TOKENS.findall(key),TOKENS.findall(value)
        if Counter(source_tokens)!=Counter(target_tokens):errors.append('Token mismatch: '+key)
        controls=lambda ts:[t for t in ts if t.startswith('\\')]
        if controls(source_tokens)!=controls(target_tokens):errors.append('Control sequence order: '+key)
        if key and not value:errors.append('Empty translation: '+key)
    oldraw=(original/'data.win').read_bytes(); newraw=(build/'data.win').read_bytes()
    oldfonts,newfonts=fonts(oldraw),fonts(newraw)
    if [f[0] for f in oldfonts]!=[f[0] for f in newfonts]:errors.append('Font resource IDs changed')
    if list(chunks(oldraw))!=list(chunks(newraw)):errors.append('GameMaker chunk list changed')
    missing=[]
    for old,new in zip(oldfonts,newfonts):
        if old[2]!=new[2]:errors.append('Font metrics changed: '+old[0])
        for cp,glyph in old[1].items():
            if 0xac00<=cp<=0xd7a3 or 0x1100<=cp<=0x11ff or 0x3130<=cp<=0x318f:continue
            if new[1].get(cp)!=glyph:errors.append('Original glyph changed: '+old[0]+' '+hex(cp))
    body=newfonts[1][1]
    if any(cp not in body for cp in range(0xac00,0xd7a4)):errors.append('Incomplete modern Hangul coverage')
    for ch in sorted(set(''.join(locale.values())+'한국어')):
        if ch.isspace():continue
        if ord(ch) not in body:missing.append('U+%04X'%ord(ch))
    # Some untranslated source text contains symbols absent from the shipped font.
    # Prototype checks focus on the authored Korean subset; release checks cover all.
    authored=load(ROOT/'translation/prototype.json')
    for segment in sorted((ROOT/'translation/segments').glob('*.json')):
        authored.update(load(segment))
    revisions=ROOT/'translation/revisions/full-review.json'
    if revisions.exists():
        authored.update({i:r['korean'] for i,r in load(revisions).items()})
    authored_missing=sorted(set('U+%04X'%ord(ch) for text in authored.values() for ch in text if not ch.isspace() and ord(ch) not in body))
    if authored_missing:errors.append('Missing authored glyphs: '+repr(authored_missing))
    if missing:errors.append('Missing full-locale glyphs: '+repr(missing))
    original_atlas=Image.open(original/'font-export/font_3.png').convert('RGBA')
    patched_atlas=Image.open(build/'fonts/font_3.png').convert('RGBA')
    if original_atlas.tobytes()!=patched_atlas.crop((0,0,*original_atlas.size)).tobytes():errors.append('Original atlas pixels changed')
    credit_ids=list(range(1647,1712))+list(range(1741,1786))
    credit_text=''.join(authored.get(str(i),'') for i in credit_ids)
    for name,glyphs,_ in newfonts:
        if name=='font_3':continue
        absent=sorted(set('U+%04X'%ord(ch) for ch in credit_text if not ch.isspace() and ord(ch) not in glyphs))
        if absent:errors.append('Missing credit glyphs: '+name+' '+repr(absent))
        old_image=Image.open(original/'font-export'/(name+'.png')).convert('RGBA')
        new_image=Image.open(build/'fonts'/(name+'.png')).convert('RGBA')
        if old_image.tobytes()!=new_image.crop((0,0,*old_image.size)).tobytes():errors.append('Original credit atlas pixels changed')
    if (build/'font-export').exists():
        for name,_,_ in newfonts:
            actual=Image.open(build/'font-export'/(name+'.png')).convert('RGBA')
            expected=Image.open(build/'fonts'/(name+'.png')).convert('RGBA')
            if actual.size!=expected.size or actual.tobytes()!=expected.tobytes():errors.append('Serialized font atlas mismatch: '+name)
    rows=load(ROOT/'translation/worktable.json')
    untranslated=sum(row['status']=='untranslated' for row in rows)
    text_reviewed=sum(row['status']=='text_reviewed' for row in rows)
    review_path=ROOT/'docs/full-review.json'
    if review_path.exists():
        review=load(review_path)
        if [r['id'] for r in review['entries']]!=list(range(len(rows))):
            errors.append('Text review coverage IDs differ from locale')
        if text_reviewed!=len(rows):errors.append('Text review hashes are stale; re-review changed entries')
    if release and untranslated:errors.append(f'{untranslated} untranslated entries')
    if release and any(row['status']!='reviewed' for row in rows):errors.append('Translation review incomplete')
    report={'phase':mode['phase'], 'locale_mode':mode['mode'], 'unique_keys':len(locale),
       'translated':len(rows)-untranslated, 'draft_translations':sum(row['status']=='draft' for row in rows), 'untranslated':untranslated,
       'text_reviewed':text_reviewed, 'runtime_review_complete':False,
       'hangul_syllables':sum(0xac00<=cp<=0xd7a3 for cp in body),
       'body_glyphs':len(body), 'font_ids_preserved':True,
       'full_locale_missing_glyphs':missing, 'errors':errors,
       'data_sha256':hashlib.sha256(newraw).hexdigest(),
       'release_ready':release and not errors}
    (build/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True,indent=2))
    if errors:raise SystemExit(1)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--release',action='store_true')
    check(parser.parse_args().release)
