"""Record this completed text-review pass against a pinned beta.2 baseline.

This records editorial decisions already made; it does not perform a review.
Keep per-entry hashes so later edits cannot silently inherit review status.
"""
import hashlib
import json
from pathlib import Path
import unicodedata

ROOT=Path(__file__).resolve().parents[1]
digest=lambda text:hashlib.sha256(text.encode('utf-8')).hexdigest()

def write():
    baseline_path=ROOT/'private/reviews/full-review-2026-10-20/baseline-ko-KR.json'
    baseline=json.loads(baseline_path.read_text(encoding='utf-8'))
    old_manifest=json.loads((ROOT/'dist/VernalEdge-Korean-0.1.0-beta.2/manifest.json').read_text(encoding='utf-8'))
    expected=next(f['patched'] for f in old_manifest['files'] if f['path']=='loc/ko-KR.json')
    assert hashlib.sha256(baseline_path.read_bytes()).hexdigest()==expected
    revisions_path=ROOT/'translation/revisions/full-review.json'
    revisions=json.loads(revisions_path.read_text(encoding='utf-8'))
    rows=json.loads((ROOT/'translation/worktable.json').read_text(encoding='utf-8'))
    assert len(rows)==1838 and list(baseline)==[r['english'] for r in rows]
    entries=[]
    changed=[]
    for row in rows:
        index=row['id']
        before=baseline[row['english']]
        revision=revisions.get(str(index))
        after=unicodedata.normalize('NFC',revision['korean']) if revision else before
        assert row['korean']==after, f'Build locale before recording review: {index}'
        if before!=after:
            assert revision
            changed.append(dict(id=index,english=row['english'],before=before,after=after,reason=revision['reason']))
        entries.append(dict(id=index,context=row['context'],source_sha256=digest(row['english']),
            before_sha256=digest(before),korean_sha256=digest(after),
            decision='revised' if before!=after else 'retained',
            reason=revision['reason'] if revision else '원문 의미와 한국어 문장을 대조하고 이번 검토에서 유지',
            text_review='first_pass_complete',runtime_review='pending'))
    assert len(changed)==len(revisions)
    report=dict(date='2026-10-20',base_package=old_manifest['package'],target_package='VernalEdge-Korean-0.1.0-beta.3',
        reviewer='Codex text review; no claim of independent human editing',
        scope='전체 1,838개 영어 키와 한국어의 의미·문체·용어 1차 대조',
        method='문맥 묶음으로 원문과 번역을 읽고 수정; 실제 장면 배치·화자·연출·표시 검수는 사용자 진행',
        baseline_sha256=expected,total=len(rows),changed=len(changed),retained=len(rows)-len(changed),
        runtime_review_complete=False,release_ready=False,entries=entries,changes=changed)
    (ROOT/'docs/full-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    revisions_path.write_text(json.dumps(revisions,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    lines=['# 전체 번역 1차 재검토 — beta.3','',
        f"영어 원문과 한국어 1,838개를 대조해 beta.2 대비 {len(changed)}개를 수정하고 {len(rows)-len(changed)}개는 유지했다. 앞선 beta.2의 초반 대사 교정도 포함된 상태를 기준으로 검토했다.",'',
        'Codex가 수행한 텍스트 검토다. 독립적인 사람의 감수 또는 전 구간 플레이 검수 완료를 의미하지 않는다. 실제 화자·장면 전환·음성 연출·표시 폭은 사용자 확인이 남아 있다.','',
        '## 주요 수정','',
        '- 버널: 관용구 직역, 대명사 혼동, 어색한 문장 연결을 줄이고 짧고 직설적인 구어체로 정리.',
        '- 처빌과 주요 인물: 설명의 주어·대상, 기억 복구의 범위, 과거 행동과 책임에 관한 문장을 명확히 표현.',
        '- NPC·퀘스트: 상인의 말투와 퀘스트 목적지, 물건 교환 관계를 정돈.',
        '- 기술 설명: Poise를 강인도로 통일. 차지·방어·대시의 조건과 동작 연결을 명확히 표현.',
        '- 메뉴·아이템·일지: 원문 의미가 흐려지거나 여러 뜻으로 읽히는 표현을 교정.',
        '- 용어집에서 처빌과 알스트로메리아의 말투를 구별하고 잘못된 인물 설명을 수정.','',
        '## 변경 범위와 기록','',
        '영어 키·치환 변수·제어 코드와 숫자/백분율을 대조했다. 폰트와 data.win은 beta.2와 동일하다. 번역문은 UTF-8·NFC로 생성한다.',
        '개발 작업 폴더의 `docs/full-review.json`에는 1,838개 항목별 원문·번역 해시, 유지/수정 판정 및 수정 이유가 있다. `FULL_REVIEW_CHANGES.md`에는 수정 전후를 기록했다. 검토 해시와 다른 문장은 검토 상태를 자동으로 이어받지 않는다.','',
        '## 사용자 인게임 확인','',
        '- 초반부터 버널의 말이 자연스럽게 이해되는지, 처빌과의 대화가 이어지는지 확인.',
        '- 차지 공격·강인도·방어 관련 설명이 실제 동작과 맞는지 확인.',
        '- 새로 길어진 설명과 긴 대사에서 줄바꿈·잘림·메시지 기록·연출을 확인.',
        '- 저장 지점의 “펄스 절반 회복”은 원문의 모호함을 유지했다. 절반의 기준은 실제 회복량으로 확인해야 한다.',
        '- 설명이 없는 도전 과제 제목은 달성 조건을 번역에 새로 만들어 넣지 않았다.',
        '- 전 구간 스토리·선택 대사·미니게임·엔딩·크레딧 검수는 계속 미완료.',
        '- `2023-04-06` 뒤쪽 표시 깨짐은 사용자 요청에 따라 보류.','',
        '텍스트 작업표는 `text_reviewed` 상태이며 인게임 검수 완료를 뜻하는 `reviewed`로 표시하지 않는다. 배포는 계속 베타이며 `releaseReady=false`다.','']
    (ROOT/'docs/FULL_REVIEW.md').write_text('\n'.join(lines),encoding='utf-8')
    lines=['# beta.3 수정 전후','', '스토리 전체의 스포일러를 포함한다. ID는 최초 원본 영어 키 순서의 0 기반 번호다.','']
    for change in changed:
        lines += [f"## {change['id']} — {rows[change['id']]['context']}",'',
            '**원문:** '+change['english'].replace('\n',' / '),'',
            '**수정 전:** '+change['before'].replace('\n',' / '),'',
            '**수정 후:** '+change['after'].replace('\n',' / '),'',
            '**이유:** '+change['reason'],'']
    (ROOT/'docs/FULL_REVIEW_CHANGES.md').write_text('\n'.join(lines),encoding='utf-8')
    print(f'Text review recorded: {len(rows)} entries; {len(changed)} revised; {len(rows)-len(changed)} retained; runtime QA pending')

if __name__=='__main__':write()
