"""改善の輪（omochae.engine_loop）の束の大きさの上限と、記録の番号の重なりの除き方を確かめる（セキュリティの点検 2026-11-07）。
1. 上限（8 MB）より大きい束は断る: CLI の check と take は 3（F13.bundle）で、何も置かない。ファイルは上限の先まで読まない。
   take に渡す束（辞書）も、置き場に置く形の大きさで断る。置き場に手で置いた大きな束は、案作りに数えない。
2. 群の記録の番号の重なりを除くのは、件数に比例する時間（前は件数の 2 乗で、出し元の違う束が同じ群を持つと止まった）。
   並びと中身は前と同じ（入れる前の番号に無い物を、束の並びのまま足す。同じ束の中の重なりは前と同じく残る）。
3. ふだんの束は、今までと同じ結果（見本の束は通り、置いた束も上限の中）。案の形（record_ids の欄）は変えない。"""
import copy
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from omochae import engine_loop as el  # noqa: E402

SAMPLE = json.loads((ROOT / "examples/bundles/sample_made_up.json").read_text(encoding="utf-8"))
tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["OMOCHAE_ENGINE_LOOP"] = str(tmp / "local")
os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions.json")
os.environ["OMOCHAE_REPORTS"] = str(tmp / "no-reports")
LIMIT = 8_000_000  # 束の大きさの上限（バイト。engine_loop.MAX_BUNDLE_BYTES と同じ値を、ここで決まりとして書く）
BIG = "束は 8 MB まで"


def cli(*args):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}  # 置き場の向け先を途中で替えるので、呼ぶ時の環境で
    return subprocess.run([sys.executable, "-m", "omochae.engine_loop", *args], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)


def placed():
    return sorted((tmp / "local").glob("bundles/*.json"))


# 1. 上限の外の束は断る。ファイルの大きさで見る所（CLI）: 中身は正しい束でも、前に空白を詰めて上限を越えた物は 3。何も置かない
padded = tmp / "padded.json"
padded.write_text(" " * LIMIT + json.dumps(SAMPLE, ensure_ascii=False), encoding="utf-8")
for cmd in ("check", "take"):
    r = cli(cmd, str(padded))
    assert r.returncode == 3 and "F13.bundle" in r.stderr and BIG in r.stderr, (cmd, r.returncode, r.stderr[-300:])
assert placed() == []
# 上限ちょうどまでの空白なら、今までどおり読める（上限は大きさだけを見る）
fits = tmp / "fits.json"
body = json.dumps(SAMPLE, ensure_ascii=False)
fits.write_text(" " * (LIMIT - len(body.encode("utf-8"))) + body, encoding="utf-8")
assert fits.stat().st_size == LIMIT and cli("check", str(fits)).returncode == 0
# 置き場に置く形の大きさで見る所（check_bundle。take に渡す辞書）: 記録の番号を詰めて上限を越えた束は、文を確かめる前に断る
huge = copy.deepcopy(SAMPLE)
huge["groups"] += [{**copy.deepcopy(SAMPLE["groups"][0]), "sheet_set": f"goraigo-v{n}"} for n in (8, 9)]  # 群 1 つの番号は MAX_COUNT までなので、群を足す
for i, g in enumerate(huge["groups"]):
    g["record_ids"] = [f"R-{i * el.MAX_COUNT + k:08d}" for k in range(el.MAX_COUNT)]
assert len(json.dumps(huge, ensure_ascii=False, indent=1).encode("utf-8")) > LIMIT
assert [(f.floor, f.where, f.message) for f in el.check_bundle(huge)] == [("F13.bundle", "束", BIG)]
assert el.take(huge)[0] is None and placed() == []
# 置き場に手で置いた上限の外の束は、読めない束と同じく数えない（案作りと並べが、その束で止まらない）
(tmp / "local/bundles").mkdir(parents=True)
(tmp / "local/bundles/B-20261105-1500-aaaaaaaa.json").write_text(padded.read_text(encoding="utf-8"), encoding="utf-8")
assert el.bundles() == [] and el.propose() == ([], [])
assert cli("compare").returncode == 0
assert el.MAX_BUNDLE_BYTES == LIMIT

# 2. 記録の番号の重なりは、件数に比例する時間で除く。出し元の違う 2 つの束が、同じ群に 4 万件ずつ（半分が重なる）を持つ形。
# 前の除き方（入れた番号の list を 1 つずつ探す）は、この形で 40 秒を越えた。並びは前と同じ
N = 40000
a = copy.deepcopy(SAMPLE)
a["groups"][0]["record_ids"] = [f"R-{k:08d}" for k in range(N)]
b = copy.deepcopy(SAMPLE)
b["from"] = "other-site"
b["groups"][0]["record_ids"] = [f"R-{k:08d}" for k in range(N // 2, N // 2 + N)]
assert el.check_bundle(a) == [] and el.check_bundle(b) == []
t0 = time.monotonic()
gs = el.groups([a, b])
took = time.monotonic() - t0
assert took < 2, took
assert gs[("slider_fan", "goraigo-v10", "")]["record_ids"] == [f"R-{k:08d}" for k in range(N // 2 + N)]


def before(bs):
    """前の除き方（入れる前の番号の list に無い物を、束の並びのまま足す）。小さな束で、並びと中身が同じかを比べるための物。"""
    out = {}
    for x in bs:
        for g in x["groups"]:
            key = (g["template"], g.get("sheet_set", ""), g.get("paper", ""))
            ids = out.setdefault(key, [])
            ids += [r for r in g.get("record_ids", []) if r not in ids]
    return out


c = copy.deepcopy(SAMPLE)
c["from"] = "third-site"
c["groups"][0]["record_ids"] = ["R-0002", "R-0009", "R-0009", "R-0001", "R-0005"]  # 同じ束の中の重なり（R-0009）も前と同じく残る
c["groups"][1]["record_ids"] = ["R-0004", "R-0003"]
for order in ([SAMPLE, c], [c, SAMPLE], [SAMPLE, c, b]):
    want = before(order)
    got = el.groups(order)
    assert {k: g["record_ids"] for k, g in got.items()} == want, order
assert el.groups([SAMPLE, c])[("slider_fan", "goraigo-v10", "")]["record_ids"] == ["R-0001", "R-0002", "R-0009", "R-0009", "R-0005"]

# 3. ふだんの束は今までどおり: 見本の束は通り、受けた束と案が置き場に出る。案の record_ids は群の番号のまま（形を変えない）
os.environ["OMOCHAE_ENGINE_LOOP"] = str(tmp / "local2")
assert el.check_bundle(SAMPLE) == [] and cli("check", "examples/bundles/sample_made_up.json").returncode == 0
r = cli("take", "examples/bundles/sample_made_up.json")
assert r.returncode == 0 and "受けた" in r.stdout, r.stderr
kept = list((tmp / "local2/bundles").glob("B-*.json"))
assert len(kept) == 1 and kept[0].stat().st_size < LIMIT and len(el.bundles()) == 1
made = el.proposals()
assert made and all(p["record_ids"] == {"slider_fan": ["R-0001", "R-0002"], "pivot_counterweight": ["R-0003"]}.get(p["template"], [])
                    for p in made if p["template"]), [(p["key"], p["record_ids"]) for p in made]

print("OK test_engine_loop_size")
