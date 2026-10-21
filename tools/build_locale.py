"""Build exact-key locale and an auditable JSON translation worktable."""
import argparse
import hashlib
import json
from pathlib import Path
import unicodedata

ROOT = Path(__file__).resolve().parents[1]

def strict_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: '+key)
        result[key] = value
    return result

def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=strict_object)

def context_for(index):
    groups=[(37,'메뉴·설정'),(43,'벌목 NPC'),(56,'튜토리얼'),(102,'아이템'),(122,'조작 설정'),
      (148,'지역 이름'),(165,'상점'),(235,'능력·기억'),(365,'주요 스토리·경기장'),(485,'마을 NPC'),
      (511,'전투 조언'),(548,'모험담 NPC'),(580,'센 교환 퀘스트'),(595,'야구 미니게임'),(625,'낚시 미니게임'),
      (671,'아이템 감정·NPC'),(675,'엄마의 편지'),(754,'결전·엔딩'),(778,'탐험·나침반'),(827,'셸 연구자'),
      (839,'꽃 돌보기'),(884,'시스템·비현실'),(1020,'주요 스토리'),(1039,'상점'),(1075,'마을 NPC'),
      (1154,'도입부·비행선'),(1282,'주문·메뉴·튜토리얼'),(1446,'처빌과 선상 대화'),(1466,'경기장·NPC'),
      (1486,'탐험·아이템'),(1502,'연구 일지'),(1627,'스토리·탐험 대화'),(1646,'시스템·게임 설명'),
      (1711,'크레딧·성우 배역'),(1723,'능력·기억'),(1740,'탐험 도움말·NPC'),(1785,'크레딧 직책'),
      (1814,'도전 과제'),(1823,'메뉴·조작'),(1831,'최종 결전'),(1832,'튜토리얼'),(1836,'주요 스토리'),(1837,'기억 설명')]
    return next(label for end,label in groups if index<=end)

def build(mode):
    source_path = ROOT/'private/original/loc/fr-FR.json'
    # Shipped files repeat "Vicious". Preserve the engine/standard JSON parser's
    # last-value behavior, but emit unique keys in the generated Korean locale.
    source_pairs = json.loads(source_path.read_text(encoding='utf-8-sig'), object_pairs_hook=list)
    base = dict(source_pairs)
    duplicates = sorted({key for key, _ in source_pairs if sum(k==key for k,_ in source_pairs)>1})
    if duplicates != ['Vicious']:
        raise ValueError('Unexpected original duplicates: '+repr(duplicates))
    assert hashlib.sha256(source_path.read_bytes()).hexdigest() == load(ROOT/'private/original/manifest.json')['files']['loc/fr-FR.json']['sha256']
    translations = load(ROOT/'translation/prototype.json')
    segment_ids = set()
    for segment in sorted((ROOT/'translation/segments').glob('*.json')):
        values = load(segment)
        if segment_ids.intersection(values):
            raise ValueError('Overlapping translation segments: '+str(segment))
        segment_ids.update(values)
        translations.update(values)
    revisions=ROOT/'translation/revisions/full-review.json'
    if revisions.exists():
        for index,revision in load(revisions).items():
            if index not in translations:raise ValueError('Unknown review ID: '+index)
            if not revision.get('reason'):raise ValueError('Missing review rationale: '+index)
            translations[index]=revision['korean']
    dest = ROOT/'private/build/loc'
    dest.mkdir(parents=True, exist_ok=True)
    (dest.parent/'source-audit.json').write_text(json.dumps({'raw_entries':len(source_pairs),
        'unique_entries':len(base), 'duplicate_keys':duplicates, 'resolution':'last value; first key position'},indent=2),encoding='utf-8')
    review_path=ROOT/'docs/full-review.json'
    review_rows={r['id']:r for r in load(review_path)['entries']} if review_path.exists() else {}
    digest=lambda text:hashlib.sha256(text.encode('utf-8')).hexdigest()
    locale, rows = {}, []
    for index, english in enumerate(base):
        translated = str(index) in translations
        korean = unicodedata.normalize('NFC', translations.get(str(index), english))
        locale[english] = korean
        reviewed=review_rows.get(index,{})
        text_reviewed=(translated and reviewed.get('source_sha256')==digest(english)
            and reviewed.get('korean_sha256')==digest(korean))
        rows.append(dict(id=index, english=english, korean=korean if translated else '',
            context=context_for(index),
            status='text_reviewed' if text_reviewed else ('draft' if translated else 'untranslated')))
    if len(translations) != sum(row['status']!='untranslated' for row in rows):
        raise ValueError('Unknown translation ID')
    available = load(ROOT/'private/original/loc/available.json')
    entry = dict(display_name='한국어', code='ko-KR', numeric_separator=',', decimal_separator='.', regions='*', line_height=16)
    if mode == 'native':
        available.append(entry)
        filename = 'ko-KR.json'
    else:
        target = next(a for a in available if a['code']=='ja-JP')
        target.update(entry)
        target['code']='ja-JP'
        filename = 'ja-JP.json'
    for name, data in [('available.json', available), (filename, locale)]:
        (dest/name).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (ROOT/'translation/worktable.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    phase='beta' if len(translations)==len(base) else 'prototype'
    (ROOT/'private/build/locale-mode.json').write_text(json.dumps({'mode':mode, 'locale':filename, 'phase':phase, 'translated':len(translations), 'total':len(base)},indent=2),encoding='utf-8')
    print(f'{mode} {phase}: {len(translations)}/{len(base)} translated; {filename}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['native','japanese-slot'], default='native')
    build(parser.parse_args().mode)
