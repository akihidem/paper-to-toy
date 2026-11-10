"""shapely が引く numpy を、Python の版ごとに == で固定している事を見る（セキュリティの点検 2026-11-07）。

なぜ 2 つに分けるか: numpy 2.5 は Python 3.12 以上を求め、init.sh の下限（MIN_PY=3.11）と食い違う。1 つの版で固定すると、下限の
Python では入らない（前に numpy==2.5.4 だけで固定した時、tests/test_init_python.py が落とした）。下限は変えず、Python の版の印で
2 つに固定する。各行の版が、その行の入る Python の版の決まりに合う事は tests/test_init_python.py も見る（入っている物の版の決まりを
読むので、今の Python に当たる行だけ）。次を見る:
1. Python の版の印の付いた名は、どれも同じ分け目の >= と < の 2 行で、== で固定する（どの Python にも、ちょうど 1 つが当たる。
   片方だけだと、当たらない Python にはその名が入らないのに、ほかの試験は当たる行だけを見て通る）。numpy はこの形で 2 つ
2. 分け目の版は init.sh の下限より上（下限の Python には < の行が当たる）
3. numpy の 2 つの版とも、shapely の求める numpy の下限を満たす。新しい Python の側の版は、古い側の版より下でない
4. uv が在る時、init.sh の下限と分け目の版の Python で requirements.txt を解き、印の付いた名が、その Python に当たる行の版に解ける事
   （< の行に 3.11 で入らない版を書くと、ここで落ちる）。uv が無い・返らない・ネットなどで解けたかを言えない時は「確かめられない」と
   1 行出して、この検査だけ飛ばす。落とすのは、uv が「No solution found」と言い、その原因の文が印を付けた名を名指しした時と、解けた版が
   違う時だけ。ネットを使わない設定（UV_OFFLINE など）でキャッシュに無い物がある時も uv は「No solution found」と言うので、それは飛ばす
"""
import importlib.metadata
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQ = ROOT / "requirements.txt"
MIN_PY = re.search(r'^MIN_PY=(\d+\.\d+)$', (ROOT / "init.sh").read_text(encoding="utf-8"), re.M).group(1)
sys.path.insert(0, str(ROOT / "src"))
from omochae.tools import tool_timeout  # noqa: E402  外の命令の時間の上限は、ほかの道具と同じ所の値（OMOCHAE_TOOL_TIMEOUT）


def ver(text):
    return tuple(int(x) for x in text.split("."))


lines = [ln.strip() for ln in REQ.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]

# 1. 印の付いた名は、同じ分け目の >= と < の 2 行で、== で固定する
marked, plain = {}, set()
for ln in lines:
    m = re.fullmatch(r'([A-Za-z0-9_.-]+)==([0-9][0-9A-Za-z.]*); python_version (>=|<) "(\d+\.\d+)"', ln)
    if m:
        marked.setdefault(m.group(1).lower(), []).append((m.group(3), m.group(2), m.group(4)))
    else:
        assert ";" not in ln, f"読めない印: {ln}"
        plain.add(ln.split("==")[0].lower())
assert not plain & set(marked), f"印の無い行と印の付いた行の両方に在る名: {sorted(plain & set(marked))}"
pins = {}
for name, rows in marked.items():
    side = {op: (v, cut) for op, v, cut in rows}
    assert len(rows) == 2 and set(side) == {">=", "<"} and side[">="][1] == side["<"][1], f"{name} の印が同じ分け目の >= と < の 2 行でない: {rows}"
    pins[name] = {"new": side[">="][0], "old": side["<"][0], "cut": side["<"][1]}
assert "numpy" in pins, f"numpy を Python の版ごとに 2 つ固定していない: {[ln for ln in lines if ln.lower().startswith('numpy')]}"

# 2. 分け目は init.sh の下限より上。下でも同じだと、下限の Python に当たる < の行が無い
for name, p in pins.items():
    assert ver(p["cut"]) > ver(MIN_PY), f"{name} の分け目 {p['cut']} が init.sh の下限 {MIN_PY} より上でない"

# 3. numpy の 2 つの版とも shapely の求める numpy の下限を満たし、新しい Python の側の版は古い側より下でない
need = next(r for r in importlib.metadata.requires("shapely") or [] if re.match(r"numpy\b", r) and "extra" not in r)
floor = re.search(r">=\s*(\d+(?:\.\d+)*)", need).group(1)
for side in ("new", "old"):
    assert ver(pins["numpy"][side]) >= ver(floor), f"numpy=={pins['numpy'][side]} は shapely の求める {need} を満たさない"
assert ver(pins["numpy"]["new"]) >= ver(pins["numpy"]["old"]), f"新しい Python の側の版が古い側より下: {pins['numpy']}"

# 4. uv が在る時、下限と分け目の Python で解き、印の付いた名がその Python に当たる行の版に解ける
# 解けたかどうかの読みは verdict に分けて、uv の言い方の写し（2026-11-10 に uv 0.13.0 が出した文）でも見る（ネットに出ずに見られる）
NETWORK_OFF = ("network was disabled", "not found in the cache")


def verdict(rc, stderr, names):
    """uv pip compile の終わりを ("ok" | "fail" | "skip", 理由) にする。

    落とす（fail）のは、uv が「No solution found」と言い、解けない原因の文が印を付けた名（names）を名指しした時だけ。
    ネットを使わない設定（UV_OFFLINE や uv.toml の offline）でキャッシュに無い物がある時も、uv は「No solution found」と言う
    （原因は「… was not found in the cache」、hint は「network was disabled」）ので、それは解けないと言い切れない（skip）。
    ほかの名が原因の時も、印の確かめの外なので skip にする（落とすと、この試験が別の事で落ちる）。"""
    if rc == 0:
        return "ok", ""
    if any(s in stderr for s in NETWORK_OFF):
        return "skip", "ネットを使わない設定で、キャッシュに無い物がある"
    if "No solution found" in stderr:
        named = [n for n in names if re.search(rf"(?<![\w.-]){re.escape(n)}(?![\w.-])", stderr, re.I)]
        if named:
            return "fail", stderr.strip()[:800]
        return "skip", "解けない原因が、印を付けた名でない"
    return "skip", (stderr.strip().splitlines() or [f"rc={rc}"])[0][:200]


def compile_at(py, env):
    """requirements.txt を Python py で解く。(verdict の種類, 理由, 解けた {名: 版}) を返す。"""
    cmd = [uv, "pip", "compile", "--python-version", py, "--no-header", "--no-annotate", str(REQ)]
    try:
        r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=limit)
    except subprocess.TimeoutExpired:
        return "skip", f"{limit:g} 秒で返らない", {}
    kind, why = verdict(r.returncode, r.stderr, list(pins))
    got = {k.lower(): v for k, v in re.findall(r"^([A-Za-z0-9_.-]+)==(\S+)$", r.stdout, re.M)} if kind == "ok" else {}
    return kind, why, got


# uv の言い方の写しで、読み分けを見る（ネットに出ない）
COLD = ("error: No solution found when resolving dependencies\n  cause: Because cairosvg was not found in the cache and you require "
        "cairosvg==2.9.1, we can conclude that your requirements are unsatisfiable.\n\nhint: Packages were unavailable because the network "
        "was disabled. When the network is disabled, registry packages may only be read from the cache.\n")
UNSAT = ("error: No solution found when resolving dependencies\n  cause: Because the requested Python version (>=3.11) does not satisfy "
         "Python>=3.12 and you require numpy{python_full_version < '3.12'}==2.5.4, we can conclude that your requirements are unsatisfiable.\n")
assert verdict(1, COLD, ["numpy"])[0] == "skip"
assert verdict(1, COLD.replace("cairosvg", "numpy"), ["numpy"])[0] == "skip"  # キャッシュに無いのが numpy でも、言い切れない
assert verdict(1, UNSAT, ["numpy"])[0] == "fail"
assert verdict(1, UNSAT.replace("numpy", "shapely"), ["numpy"])[0] == "skip"
assert verdict(2, "error: Request failed after 3 retries\n  cause: tcp connect error\n", ["numpy"])[0] == "skip"
assert verdict(0, "", ["numpy"]) == ("ok", "")

uv = shutil.which("uv")
if uv is None:
    print("確かめられない: uv が無いので、Python の版ごとに requirements.txt が解けるかを見ない（この検査だけ飛ばす）")
else:
    limit = tool_timeout()
    for py in sorted({MIN_PY, *(p["cut"] for p in pins.values())}, key=ver):
        kind, why, got = compile_at(py, os.environ)
        assert kind != "fail", f"Python {py} で requirements.txt が解けない: {why}"
        if kind == "skip":
            print(f"確かめられない: uv pip compile が Python {py} で解けたかを言えない（{why}）。この検査だけ飛ばす")
            continue
        for name, p in pins.items():
            want = p["new"] if ver(py) >= ver(p["cut"]) else p["old"]
            assert got.get(name) == want, f"Python {py} で {name} が {got.get(name)} に解けた（固定は {want}）"
    # ネットを使わない設定で、キャッシュが空の時は、落とさずに飛ばす（空の置き場を UV_CACHE_DIR にするので、ネットにもキャッシュにも出ない）。
    # 使う人の uv の設定（UV_ で始まる値・uv.toml の find-links や index）からは切り離して回す。手元の wheel の置き場がある機械では、
    # 置き場の中身しだいで、解けたり、numpy を名指しして解けないと言ったりして、この確かめの答えが機械で揺れたため
    with tempfile.TemporaryDirectory() as cold:
        clean = {k: v for k, v in os.environ.items() if not k.startswith("UV_")}
        kind, why, _ = compile_at(MIN_PY, {**clean, "UV_OFFLINE": "1", "UV_CACHE_DIR": cold, "UV_NO_CONFIG": "1"})
        assert kind == "skip", (kind, why)
