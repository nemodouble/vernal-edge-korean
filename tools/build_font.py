"""Extend the original atlas using exact (unscaled) Galmuri11 BDF pixels."""
import json
import math
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

def read_bdf(path):
    result = {}
    for block in path.read_text(encoding='utf-8').split('STARTCHAR ')[1:]:
        lines = block.splitlines()
        fields = {line.split(' ', 1)[0]: line.split(' ', 1)[1] for line in lines if ' ' in line}
        cp = int(fields['ENCODING'])
        w, h, xoff, yoff = map(int, fields['BBX'].split())
        rows = lines[lines.index('BITMAP')+1:lines.index('ENDCHAR')]
        pixels = Image.new('RGBA', (max(w, 1), max(h, 1)))
        for y, row in enumerate(rows):
            value = int(row, 16)
            for x in range(w):
                if value & (1 << (len(row)*4-1-x)):
                    pixels.putpixel((x, y), (255, 255, 255, 255))
        result[cp] = (pixels, w, h, xoff, yoff, int(fields['DWIDTH'].split()[0]))
    return result

def build():
    source = ROOT/'private/original/font-export'
    dest = ROOT/'private/build/fonts'
    dest.mkdir(parents=True, exist_ok=True)
    bdf = read_bdf(ROOT/'private/vendor/galmuri/Galmuri11.bdf')
    korean = sorted(cp for cp in bdf if (0xac00 <= cp <= 0xd7a3 or 0x1100 <= cp <= 0x11ff or 0x3130 <= cp <= 0x318f))
    assert all(cp in korean for cp in range(0xac00, 0xd7a4))
    translations=json.loads((ROOT/'translation/prototype.json').read_text(encoding='utf-8'))
    for segment in sorted((ROOT/'translation/segments').glob('*.json')):
        translations.update(json.loads(segment.read_text(encoding='utf-8')))
    revisions=ROOT/'translation/revisions/full-review.json'
    if revisions.exists():
        translations.update({i:r['korean'] for i,r in json.loads(revisions.read_text(encoding='utf-8')).items()})
    corpus=set(map(ord,''.join(translations.values())+'한국어'))
    credit_ids=list(range(1647,1712))+list(range(1741,1786))
    credit_corpus=set(map(ord,''.join(translations.get(str(i),'') for i in credit_ids)))
    for name in ('font_3','font_credit_title_CJK','font_credit_title_latin'):
        data=json.loads((source/(name+'.json')).read_text(encoding='utf-8-sig'))
        original=Image.open(source/(name+'.png')).convert('RGBA')
        existing={g['character'] for g in data['glyphs']}
        needed=corpus if name=='font_3' else credit_corpus
        wanted=set(korean) if name=='font_3' else set()
        wanted.update(cp for cp in needed if cp not in existing and not chr(cp).isspace())
        absent=wanted-set(bdf)
        if absent:raise ValueError(f'Galmuri is missing {sorted(absent)}')
        scale=1 if name=='font_3' else 2
        glyph_h=26 if scale==1 else 33
        baseline=18 if scale==1 else 23
        width,cell_w,cell_h=2048,16 if scale==1 else 28,glyph_h+2
        cols=width//cell_w
        needed_h=original.height+math.ceil(len(wanted)/cols)*cell_h
        height=2**math.ceil(math.log2(needed_h))
        atlas=Image.new('RGBA',(width,height));atlas.paste(original,(0,0))
        additions=[]
        for index,cp in enumerate(sorted(wanted)):
            bitmap,w,h,xoff,yoff,advance=bdf[cp]
            if scale!=1:bitmap=bitmap.resize((bitmap.width*scale,bitmap.height*scale),Image.Resampling.NEAREST)
            w,h,xoff,yoff,advance=[n*scale for n in (w,h,xoff,yoff,advance)]
            x,y=(index%cols)*cell_w+1,original.height+(index//cols)*cell_h+1
            top=baseline-h-yoff
            if top<0 or top+h>glyph_h or w>cell_w-2:
                raise ValueError(f'Glyph outside original cell: {name} U+{cp:04X}')
            atlas.paste(bitmap,(x,y+top))
            additions.append(dict(character=cp,x=x,y=y,w=w,h=glyph_h,shift=advance,offset=xoff))
        atlas.save(dest/(name+'.png'),optimize=True)
        (dest/(name+'.json')).write_text(json.dumps({'name':name,'width':width,'height':height,
            'glyphs':additions},indent=2),encoding='utf-8')
        print(f'{name}: {len(wanted)} added/replaced glyphs; {width}x{height}; original non-Korean pixels preserved')

if __name__ == '__main__':
    build()
