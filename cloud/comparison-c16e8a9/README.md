# 저장된 실험을 함께 읽기 / Saved experiment comparison

[2쪽 PDF 열기](ChainBench_saved_comparison_review.pdf) · [첫 페이지](review-page-1.png) · [둘째 페이지](review-page-2.png)

이 묶음은 PR #80의 `compare` 기능으로 실제 생성한 결과입니다. 기록 A/B는 같은
4차원 이차 문제에서 GD와 CG의 반복 예산만 8회/12회로 바꿉니다. 기록 C는
조건수를 10에서 100으로 바꾸고, D는 별도의 diagonal LASSO 문제입니다.
입력·설정·환경 차이를 먼저 보고 저장된 곡선을 읽도록 구성했습니다.

- `matched.html`: 같은 문제를 저장한 두 기록. 방법별 공통 축을 제공합니다.
- `mixed.html`: 서로 다른 문제가 포함된 네 기록. 여섯 기록 쌍의 차이와 개별 그래프를 표시합니다.
- `input-a.json`–`input-d.json`: 실제 CLI가 생성한 입력 보고서입니다.
- `browser-verification.json`: 생성 출처와 원본 출력 해시, 브라우저 확인 결과입니다.

HTML 파일은 GitHub의 Raw/Download로 저장한 뒤 브라우저에서 여세요. 외부
서버·폰트·스크립트를 가져오지 않으며, 한국어/영어 전환과 전체 JSON 저장을
지원합니다. 좁은 화면의 표·그래프는 안내에 따라 가로로 스크롤할 수 있습니다.

비교는 저장된 관측만 읽습니다. 알고리즘 재실행, 입력 배열·작성자 인증,
독립적인 외부 재현, 정리 증명 또는 성능 순위를 뜻하지 않습니다. 두 해시가
같아도 입력 배열의 진위를 확인한 것이 아닙니다. 사례들은 선언된 결정론적
예시이며 대표 표본이나 원 논문 그림의 재현이 아닙니다.

## Source and verification

This is the fully tested PR snapshot, head
`c16e8a904591e6f0168ce48e5567c3f6bb571609`, rendered at PR merge
`f81913ce6e27777227384af340dd9cac1f77edf9`. Its tree
`fb47ed6fd80c56d20eb2c4d887dae02929ae04bd` is exactly the tree merged into
[main f8fdc61502426a0f60c99274e4960bf568812b45](https://github.com/chocoemong17/chainbench/tree/f8fdc61502426a0f60c99274e4960bf568812b45)
by [PR #80](https://github.com/chocoemong17/chainbench/pull/80).
The packet is not relabelled as a fresh main rendering.

[All eight PR checks passed](https://github.com/chocoemong17/chainbench/actions/runs/36915684161):
1,394 tests in each of six compatibility configurations, both clean distribution
installs and the complete offline browser checks. The new comparison was checked
at 1440px and 390px, including keyboard horizontal scrolling, native details,
no-script reading, language switching and exact JSON downloads. Both PDF pages
and selected mobile left/right views were opened and inspected; the artifact,
output hashes and archived Git blobs matched.

[PR cloud generation](https://github.com/chocoemong17/chainbench/actions/runs/36915684398)
passed 25 HTML pages, 24 numerical record audits and the FISTA PDF after retrying
only an Ubuntu setup job cancelled at its time limit. Earlier superseded runs and
the corrected CSP scroll-wait failure remain in [verification.json](verification.json).

The separate [main cloud run](https://github.com/chocoemong17/chainbench/actions/runs/36919253985)
also passed. The [main push tests](https://github.com/chocoemong17/chainbench/actions/runs/36919253999)
were still running when this PR review packet was archived on 2026-10-01.
Their live status and later verification are separate from the completed PR gate.
Independent generation runs retain their own manifests and output hashes; no
byte identity between separate numerical generations is claimed.

The browser packet contains selected outputs only. Its browser-verification.json
records hashes for the complete CI artifact, including additional screenshots and
download copies not duplicated here. The separate archive manifest lists exactly
which files are retained in this directory.
