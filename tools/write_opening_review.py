"""Write the dialogue review in UTF-8 independently of the shell code page."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'docs/opening-review.json'
report=json.loads(path.read_text(encoding='utf-8'))
report.update(reason='버널의 대사가 어색하고 이해하기 어렵다는 사용자 피드백',
    scope='도입부 및 초반 선상 대화', language_review='문맥 및 구어체 재검토')
path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
vernal={1102,1103,1110,1113,1115,1117,1119,1121,1123,1124,1129,1131,1134,1137,1146,
    1148,1151,1154,1283,1288,1290,1292,1296,1299,1301,1303,1304,1306,1308,1309,
    1312,1315,1317,1319,1618,1620,1623}
lines=['# 초반 대사 재검토 — beta.2','',f"사용자 피드백: {report['reason']}.",'',
    f"총 {report['changed']}개 대사를 수정했다. 버널 대사 {report['vernal_changed']}개와 대화 연결에 필요한 주변 인물 대사를 포함한다.",
    '', '## 교정 기준','',
    '- 말로 읽었을 때 자연스러운 짧은 반말을 사용한다.',
    '- 원문 관용구의 뜻과 인물의 의도를 우선하고, 문장 구조를 그대로 따라가지 않는다.',
    '- 무엇을 가리키는지 혼란스러우면 인물·물건을 명시한다.',
    '- 버널의 도발과 무뚝뚝함을 살리고 사건·관계·정보는 새로 추가하지 않는다.',
    '- 영어 키, 버튼·연출 제어 코드, 치환 변수는 보존한다.','', '## 변경 내역','']
for change in report['changes']:
    lines += [f"### {change['id']} — "+('버널' if change['id'] in vernal else '주변 인물'),'',
        '**원문:** '+change['english'].replace('\n',' / '),'',
        '**수정 전:** '+change['before'].replace('\n',' / '),'',
        '**수정 후:** '+change['after'].replace('\n',' / '),'']
lines += ['## 확인 상태','',
    '키·변수·제어 코드·한글 글리프 자동 검사 통과. 인게임 대화 흐름과 표시 확인은 사용자가 진행한다. 릴리즈 날짜 뒤쪽 표시 깨짐은 이번 수정 범위에서 제외했다.','']
(ROOT/'docs/OPENING_REVIEW.md').write_text('\n'.join(lines),encoding='utf-8')
