# Vernal Edge 한국어 패치

Windows Steam판 **App ID 1546710 · Build ID 10939741**용 비공식 한국어 패치입니다.

**현재 버전: 0.1.0-beta.3. 전체 번역의 1차 텍스트 재검토를 마친 검수용 베타이며, 전 구간 플레이 검수는 아직 진행 중입니다.**

## 다운로드

[최신 베타 다운로드](https://github.com/nemodouble/vernal-edge-korean/releases/tag/v0.1.0-beta.3)에서 다음 파일을 받으세요.

- `VernalEdge-Korean-0.1.0-beta.3.zip`: 설치용 패치
- `VernalEdge-Korean-0.1.0-beta.3.zip.sha256`: SHA-256 체크섬

GitHub의 자동 생성 `Source code` ZIP은 개발 소스입니다. 게임에 설치하려면 위 **설치용 패치 ZIP**을 사용하세요.

## 설치

1. 게임을 완전히 종료합니다.
2. 설치용 ZIP을 풀어 `VernalEdge-Korean-0.1.0-beta.3` 폴더를 게임 폴더 안에 둡니다.
3. 해당 패치 폴더에서 PowerShell을 열어 실행합니다.

```powershell
.\Patch.ps1 -Mode Install -AllowBeta
```

4. 게임의 설정 → Language에서 **한국어**를 선택합니다.

이전 베타가 설치되어 있으면 기존 패치의 `-Mode Uninstall`로 먼저 제거하고 새 버전을 설치하세요. 게임 폴더의 `.vernal-edge-ko-backup`은 최초 원본 백업이므로 보존해야 합니다. 세이브 파일은 읽거나 수정하지 않습니다.

```powershell
.\Patch.ps1 -Mode Verify
.\Patch.ps1 -Mode Uninstall
```

Windows PowerShell 5.1 이상에서 동작하며 관리자 권한이나 Python 별도 설치는 필요하지 않습니다. 다른 빌드·다른 원본 해시에는 적용하지 않습니다. 자세한 설치·복구 안내는 [사용 설명서](docs/README.ko.md)를 참고하세요.

## 번역 범위와 현재 상태

- 메뉴·튜토리얼·아이템·기억·주문·주요 대사·NPC·연구 일지·도전 과제·크레딧 직책 등 **고유 메시지 1,838개** 번역
- 독립적인 한국어 언어 항목 추가, 본문 한글 완성형 11,172자 및 크레딧 글리프 보강
- beta.2 대비 **164개 문구 교정**: 버널 말투, 대화 연결, 설명의 주어·대상, 전투 조건과 용어 정리
- 키·변수·제어 코드·글리프 검사와 실제 패키지 설치·제거 검증 통과
- 전 구간 플레이·화자와 연출·긴 대사 잘림·기존 세이브·컨트롤러·배율 확인은 미완료

[변경 기록](docs/CHANGELOG.md) · [텍스트 재검토 요약](docs/FULL_REVIEW.md) · [수동 검수 목록](docs/QA.md)

## 알려진 문제와 제외 범위

- 버전 표시의 `2023-04-06` 뒤쪽 글자 깨짐이 보고되었으며 현재 보류 중입니다.
- 이미지에 포함된 영문, 음성, Steam 클라이언트 자체 도전 과제 화면은 교체하지 않습니다.
- 게임 업데이트로 파일 해시가 바뀌면 재검증 전까지 지원하지 않습니다.
- 제작사·실명·상품명 등 일부 고유명사는 원문을 유지합니다.

오역·어색한 대사·잘림·깨짐은 [Issues](https://github.com/nemodouble/vernal-edge-korean/issues)에 한국어 문구, 장소·상황, 화면 배율, 입력 장치와 함께 알려 주세요. 스토리 내용에는 스포일러를 표시해 주세요.

## 개발 소스

`translation/`은 번역 원본, `installer/`는 설치기, `tools/`는 폰트·언어·차분 생성 도구입니다. 재검토 수정안은 `translation/revisions/full-review.json`이 우선합니다. 개발 방법은 [개발 안내](DEVELOPMENT.md)를 참고하세요.

원본 실행 파일·전체 게임 데이터·개발용 원본 백업·다운로드한 개발 도구는 저장소와 설치용 ZIP에 포함하지 않습니다. 패치는 사용자가 보유한 지원 원본을 이용해 차분을 재구성합니다.

Vernal Edge 및 원본 자산의 권리는 원저작자에게 있습니다. Galmuri11 2.40.4는 SIL Open Font License 1.1을 따릅니다. [구성 요소 고지](docs/THIRD_PARTY_NOTICES.md)와 [폰트 라이선스](licenses/Galmuri-LICENSE.txt)를 참고하세요. 폰트 라이선스는 해당 구성 요소에 적용됩니다.
