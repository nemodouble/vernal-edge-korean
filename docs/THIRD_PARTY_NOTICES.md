# 구성 요소 및 출처

## Galmuri11 2.40.4

Copyright (c) 2019–2025 Lee Minseo (quiple@quiple.dev).

- 공식 배포: https://github.com/quiple/galmuri/releases/tag/v2.40.4
- 제작자: https://quiple.dev/font/galmuri
- 라이선스: SIL Open Font License 1.1. 배포물의 `Galmuri-LICENSE.txt`에 원문을 포함합니다.
- 원본 BDF의 픽셀을 사용합니다. 본문은 원래 픽셀 크기, 크레딧 한글은 정수 2배 최근접 확대입니다.
- 기존 게임 폰트의 비한글 글리프·커닝·자산 번호는 보존합니다. Galmuri 폰트 자체의 이름을 바꿔 재배포하는 폰트 제품이 아닙니다.

## UndertaleModTool / UndertaleModLib 0.9.2.0

- 공식 저장소: https://github.com/UnderminersTeam/UndertaleModTool
- 라이선스: GPL-3.0. 원본 도구의 라이선스와 고지는 개발용 다운로드에 포함됩니다.
- GameMaker 자산을 읽고 폰트 메타데이터·텍스처를 갱신하는 개발 도구로 사용했습니다.
- 설치용 ZIP에는 도구의 실행 파일이나 라이브러리를 포함하지 않습니다.
- 독자 작성한 `export_fonts.csx`와 `patch_fonts.csx`는 개발 폴더에 있습니다. 포함된 가져오기 스크립트는 API 확인용으로만 사용했습니다.

## Vernal Edge 및 기존 폰트

Vernal Edge 및 원본 자산의 권리는 원저작자에게 있습니다. 원본은 배포하지 않으며 사용자 설치본을 대상으로 차분만 적용합니다. 게임의 기존 Silver 및 Noto Serif 자산은 비한글 부분을 보존합니다.

## Python / Pillow

Python과 Pillow는 개발 중 BDF 픽셀 읽기·텍스처 구성·번역 검증에 사용했습니다. 설치용 ZIP에 Python이나 Pillow를 포함하지 않습니다.
