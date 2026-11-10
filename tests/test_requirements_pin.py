"""shapely が引く numpy を、Python の版ごとに == で固定している事を見る（セキュリティの点検 2026-11-07）。

なぜ 2 つに分けるか: numpy 2.5 は Python 3.12 以上を求め、init.sh の下限（MIN_PY=3.11）と食い違う。1 つの版で固定すると、下限の
Python では入らない（前に numpy==2.5.4 だけで固定した時、tests/test_init_python.py が落とした）。下限は変えず、Python の版の印で
2 つに固定する。各行の版が、その行の入る Python の版の決まりに合う事は tests/test_init_python.py が見る（入っている物の版の決まりを
読むので、今の Python に当たる行だけ）。ここは、ネットに出ずに見られる形を見る。次を見る:
1. numpy の行は 2 つで、どちらも == で固定し、印は python_version の >= と < が同じ版で分かれる（どの Python にも、ちょうど 1 つが当たる）
2. 分け目の版は init.sh の下限より上（下限の Python には < の行が当たる）
3. 2 つの版とも、shapely の求める numpy の下限を満たす。新しい Python の側の版は、古い側の版より下でない
"""
import importlib.metadata
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
MIN_PY = re.search(r'^MIN_PY=(\d+\.\d+)$', (ROOT / "init.sh").read_text(encoding="utf-8"), re.M).group(1)


def ver(text):
    return tuple(int(x) for x in text.split("."))


lines = [ln.strip() for ln in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines() if ln.strip()]
found = [ln for ln in lines if re.match(r"numpy\b", ln, re.I)]

# 1. numpy の行は 2 つ。== で固定し、印は >= と < が同じ版で分かれる
pins = [re.fullmatch(r'numpy==(\d+(?:\.\d+)+); python_version (>=|<) "(\d+\.\d+)"', ln) for ln in found]
assert len(pins) == 2 and all(pins), f"numpy を Python の版ごとに 2 つ固定していない: {found}"
side = {m.group(2): m for m in pins}
assert set(side) == {">=", "<"} and side[">="].group(3) == side["<"].group(3), f"2 つの印が同じ版で分かれていない: {found}"
cut = side["<"].group(3)

# 2. 分け目は init.sh の下限より上。下でも同じだと、下限の Python に当たる行が無い
assert ver(cut) > ver(MIN_PY), f"分け目 {cut} が init.sh の下限 {MIN_PY} より上でない"

# 3. 2 つの版とも shapely の求める numpy の下限を満たし、新しい Python の側の版は古い側より下でない
need = next(r for r in importlib.metadata.requires("shapely") or [] if re.match(r"numpy\b", r) and "extra" not in r)
floor = re.search(r">=\s*(\d+(?:\.\d+)*)", need).group(1)
for m in pins:
    assert ver(m.group(1)) >= ver(floor), f"{m.group(0)} は shapely の求める {need} を満たさない"
assert ver(side[">="].group(1)) >= ver(side["<"].group(1)), f"新しい Python の側の版が古い側より下: {found}"
