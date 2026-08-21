# -*- coding: utf-8 -*-
r"""릴리스 빌드를 GitHub Pages 배포본으로 바꾼다.

    python deploy.py ..\jp-work\JellyPangPang-660-release.html

게임 소스에 없어서 배포할 때마다 다시 해 줘야 하는 일이 셋 있다.
손으로 하면 매번 하나씩 빠뜨리므로 스크립트로 굳힌다.

  ① 정적 manifest 로 교체  ★ 이것이 이 파일이 존재하는 진짜 이유다
      게임 소스는 <link rel="manifest" id="pwaManifest" href='data:application/manifest+json,…'>
      를 걸고, 부팅 후 자기 젤리로 아이콘을 그려 **blob: URL** manifest 로 바꿔 끼운다.
      보기에는 좋은데 **앱 설치가 안 된다** — data:/blob: URL 은 상대경로의 기준이 될 수 없어
      start_url·scope·icons 가 전부 깨지고, 크롬이 WebAPK 를 포기하고 '북마크 바로가기'로
      만들어 아이콘에 브라우저 배지가 붙는다. (커밋 470e9c5 에서 실제로 겪고 고친 문제다.)
      → 여기서 진짜 파일 manifest.webmanifest + 정적 아이콘 링크로 갈아끼운다.
        id 를 떼므로 런타임 교체 코드는 `if(link)` 가드에 걸려 조용히 건너뛴다.
        런타임이 따로 붙이는 apple-touch-icon 은 그대로 둔다 — iOS 전용이고 설치를 안 막으며,
        홈 화면에 '내 젤리'가 뜨는 원래 의도가 살아 있다.

  ② 서비스워커 등록 스니펫 — 게임 소스(src/)에 없다. 없으면 오프라인이 안 되고 앱 설치도 약해진다.

  ③ sw.js 의 CACHE 버전 — 안 올리면 이미 설치한 폰이 옛 파일을 계속 쓴다.
"""
import io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))

PWA_HEAD = """<!-- [배포] 정적 manifest·아이콘 — deploy.py 가 넣는다.
     data:/blob: manifest 는 앱 설치를 깨뜨린다(커밋 470e9c5). 반드시 진짜 파일이어야 한다. -->
<link rel="manifest" href="./manifest.webmanifest">
<link rel="icon" type="image/png" sizes="192x192" href="./icon-192.png">
<link rel="icon" type="image/png" sizes="512x512" href="./icon-512.png">
<link rel="apple-touch-icon" href="./icon-180.png">"""

SW_SNIPPET = """<!-- [배포] 오프라인 캐시 서비스워커 등록 — deploy.py 가 넣는다(게임 소스에 없다). -->
<script>
  if ('serviceWorker' in navigator) {
    addEventListener('load', () => {
      navigator.serviceWorker.register('./sw.js').catch(() => {});
    });
  }
</script>
</body>"""


def fail(msg):
    print("  ✗ " + msg)
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    src = sys.argv[1]
    h = io.open(src, encoding="utf-8").read()
    ver = re.search(r"JellyPangPang-(\d+)-release", os.path.basename(src))
    ver = ver.group(1) if ver else None
    if not ver:
        fail("파일 이름에서 버전을 못 읽었다 — JellyPangPang-{N}-release.html 형태여야 한다")
    print(f"입력  : {os.path.basename(src)}  ({len(h):,}자)")

    # 릴리스 빌드가 맞는지 — dev 빌드를 실수로 배포하면 치트 패널이 공개된다
    for tok in ("@DEV-ONLY", "__CAMPDBG", "@TOOLKIT", "@STATE"):
        if tok in h:
            fail(f"dev 흔적이 있다: {tok} — release 빌드를 넘겨라")
    print("  ✓ 릴리스 빌드 확인 (dev 흔적 0)")

    # ① 정적 manifest 로 교체
    m = re.search(r"<link rel=\"manifest\"[^>]*?>", h, re.S)
    if not m:
        fail("manifest link 를 못 찾았다 — 게임 소스 구조가 바뀌었는지 확인하라")
    if "data:" not in m.group(0) and "manifest.webmanifest" in m.group(0):
        print("  · 이미 정적 manifest 다 — 그대로 둔다")
    else:
        h = h[:m.start()] + PWA_HEAD + h[m.end():]
        print(f"  ✓ manifest 를 정적 파일로 교체 (data: {len(m.group(0)):,}자 → 진짜 파일)")

    # ② 서비스워커 등록
    if "serviceWorker" in h:
        fail("이미 serviceWorker 코드가 있다 — 중복 주입을 막는다")
    if h.count("</body>") != 1:
        fail(f"</body> 가 {h.count('</body>')}개 — 1개여야 한다")
    h = h.replace("</body>", SW_SNIPPET, 1)
    print("  ✓ 서비스워커 등록 스니펫 주입")

    # 쓰기 (원자적)
    dst = os.path.join(HERE, "index.html")
    tmp = dst + ".tmp"
    io.open(tmp, "w", encoding="utf-8", newline="").write(h)
    os.replace(tmp, dst)
    print(f"  ✓ index.html  ({os.path.getsize(dst):,} bytes)")

    # ③ sw.js CACHE 버전
    sw_path = os.path.join(HERE, "sw.js")
    s = io.open(sw_path, encoding="utf-8").read()
    mc = re.search(r"const CACHE = '([^']+)';", s)
    if not mc:
        fail("sw.js 에서 CACHE 를 못 찾았다")
    new_cache = f"jelly-pangpang-v{ver}"
    if mc.group(1) == new_cache:
        print(f"  · sw.js CACHE 이미 {new_cache}")
    else:
        s = s[:mc.start(1)] + new_cache + s[mc.end(1):]
        io.open(sw_path, "w", encoding="utf-8", newline="").write(s)
        print(f"  ✓ sw.js CACHE {mc.group(1)} → {new_cache}")

    # 배포에 필요한 파일이 다 있는가
    need = ["manifest.webmanifest", "icon-192.png", "icon-512.png",
            "icon-180.png", "icon-maskable-512.png", "sw.js"]
    miss = [f for f in need if not os.path.exists(os.path.join(HERE, f))]
    if miss:
        fail("배포 파일 누락: " + ", ".join(miss))
    print("  ✓ 배포 파일 " + str(len(need)) + "종 전부 존재")
    print("\n다음: 브라우저로 확인한 뒤 git add -A && git commit && git push")
    return 0


sys.exit(main())
