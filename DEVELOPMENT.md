# Vernal Edge 한국어 패치 작업 폴더

배포 후보본: `dist/VernalEdge-Korean-0.1.0-beta.3.zip`.

공개 저장소: https://github.com/nemodouble/vernal-edge-korean

- `translation/prototype.json`: 최초 시제품 번역. 세그먼트가 같은 ID를 덮어쓰면 세그먼트가 우선한다.
- `translation/segments/*.json`: 전체 번역 원본. ID는 원본 프랑스어 JSON의 영어 키 순서에 고정되어 있으며 원본 해시를 검사한다.
- `translation/revisions/full-review.json`: 전체 재검토 수정안과 항목별 수정 이유. 시제품·세그먼트보다 우선한다.
- `docs/full-review.json`: 1,838개 텍스트 검토 기록. 원문·번역 해시로 검토 대상을 고정한다. `FULL_REVIEW.md`는 요약이며 `FULL_REVIEW_CHANGES.md`에는 수정 전후가 있다.
- `translation/worktable.json`: 생성된 영어 원문·한국어·문맥·검수 상태 작업표. 직접 수정하지 말고 번역 원본에서 수정한 뒤 재생성한다.
- `tools/`: 재현 가능한 폰트·언어·차분 패키지 빌드 및 검사 도구.
- `installer/`: Python 없이 실행되는 Windows PowerShell 5.1 설치·제거 도구.
- `tests/`: 합성 파일을 이용한 설치·실패 복구 통합 검사.
- `docs/`: 용어집, 수동 검수 목록, 배포 설명서와 고지.
- `private/`: 원본 백업, 개발 도구, 임시 출력. **공개 배포 금지.**

현재 Steam 설치본의 최초 원본은 `private/original`에 있다. 원본 백업을 새 게임 데이터로 덮어쓰지 않는다. 세이브에는 접근하지 않는다.

## 빌드

Python 3.12와 Pillow가 필요하다. 고정 개발 도구는 `tools/bootstrap.py --fetch`로 공식 배포처에서 받는다. 원본이 이미 패치되었으면 `bootstrap.py`의 백업 초기화를 다시 실행하지 않는다.

```powershell
python .\tools\build_locale.py
python .\tools\build_font.py
```

게임 폴더에서 UndertaleModTool CLI를 사용한다.

```powershell
.\KoreanPatch\private\vendor\utmt\UndertaleModCli.exe load .\KoreanPatch\private\original\data.win -s .\KoreanPatch\tools\patch_fonts.csx -o .\KoreanPatch\private\build\data.win -f
.\KoreanPatch\private\vendor\utmt\UndertaleModCli.exe load .\KoreanPatch\private\build\data.win -s .\KoreanPatch\tools\export_fonts.csx
python .\KoreanPatch\tools\validate.py
python .\KoreanPatch\tests\test_installer.py
python .\KoreanPatch\tools\package.py --replace
```

`validate.py --release`는 번역 검수 상태가 완료되지 않은 후보본을 실패 처리한다. 인게임 수동 검수는 `docs/QA.md`에 기록하며, 현재 베타 배포기는 `releaseReady=false`를 강제한다. 정식판으로 자동 승격하지 않는다.

작업표의 `text_reviewed`는 원문과 번역문을 대조한 텍스트 검토 상태다. 인게임 검수 완료 상태인 `reviewed`와 구별한다. 번역이 바뀌면 검토 해시를 갱신하기 전에 해당 항목을 다시 검토한다.

로컬 초기 시제품이 설치된 상태라면 전체 후보본 설치 전에 `tools/prototype.py restore`로 복원한 뒤, 배포 폴더의 `Patch.ps1 -Mode Install -AllowBeta`를 사용한다. 이 시제품 복구 도구는 공개 ZIP에 포함되지 않는다.
