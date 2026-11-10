"""改善の輪（omochae.engine_loop）の束の大きさの上限と、記録の番号の重なりの除き方を確かめる（セキュリティの点検 2026-11-07）。
1. 上限（8 MB）より大きい束は断る: CLI の check と take は 3（F13.bundle）で、何も置かない。ファイルは上限の先まで読まない。
   take に渡す束（辞書）も、置き場に置く形の大きさで断る。置き場に手で置いた大きな束は、案作りに数えない。
2. 群の記録の番号の重なりを除くのは、件数に比例する時間（前は件数の 2 乗で、出し元の違う束が同じ群を持つと止まった）。
   並びと中身は前と同じ（入れる前の番号に無い物を、束の並びのまま足す。同じ束の中の重なりは前と同じく残る）。
3. ふだんの束は、今までと同じ結果（見本の束は通り、置いた束も上限の中）。
4. 案は記録の番号の list を持たず、群の番号の数（record_count）だけを持つ（番号を案ごとに写すと、上限の中の束 1 つで置き場が膨らんだ）。
   前の形のまだ決まっていない案は、新しくする時に番号を落とす。決めた案は書き換えない。Issue の下書きと台帳に番号は出ない。
5. take は置く形の大きさで測り直す（dropped_pii の欄を足すと、確かめた束より大きくなる事がある）。
6. 受け入れた報告も、上限（100 KB）より大きい物は読まずに数えない。
7. JSON にできない値（set・bytes・輪になった物・深すぎる入れ子）を持つ束は、トレースバックでなく F13.bundle で断る。"""
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

# 3. ふだんの束は今までどおり: 見本の束は通り、受けた束と案が置き場に出る。案は群の番号の数を持つ
os.environ["OMOCHAE_ENGINE_LOOP"] = str(tmp / "local2")
assert el.check_bundle(SAMPLE) == [] and cli("check", "examples/bundles/sample_made_up.json").returncode == 0
r = cli("take", "examples/bundles/sample_made_up.json")
assert r.returncode == 0 and "受けた" in r.stdout, r.stderr
kept = list((tmp / "local2/bundles").glob("B-*.json"))
assert len(kept) == 1 and kept[0].stat().st_size < LIMIT and len(el.bundles()) == 1
made = el.proposals()
assert made and all(p["record_count"] == {"slider_fan": 2, "pivot_counterweight": 1}.get(p["template"], 0) for p in made), \
    [(p["key"], p.get("record_count")) for p in made]

# 4. 案は番号の list を持たない。群 1 つに番号が 10 万件あり、手順ごとの案が 40 起きる束でも、案のファイルは小さいまま
assert not any("record_ids" in p for p in made)
os.environ["OMOCHAE_ENGINE_LOOP"] = str(tmp / "local3")
many = copy.deepcopy(SAMPLE)
many["groups"][0]["record_ids"] = [f"R-{k:08d}" for k in range(el.MAX_COUNT)]
many["groups"][0]["stuck_steps"] = {str(n): {"taps": 3, "people": 2} for n in range(1, 41)}
assert el.check_bundle(many) == [] and el.take(many)[0] is not None
assert len(el.propose()[0]) >= 40
props = sorted((tmp / "local3/proposals").glob("EP-*.json"))
size = sum(p.stat().st_size for p in props)
assert len(props) >= 40 and size < 1_000_000, (len(props), size)  # 前の形は、この束で 40 を越える案に 10 万件ずつを写し、60 MB を越えた
assert {json.loads(p.read_text(encoding="utf-8"))["record_count"] for p in props} >= {el.MAX_COUNT}
# 前の形の案（record_ids を持つ）: まだ決まっていない案は、新しくする時に番号を落とす。決めた案は、決めた時のまま
first, second = props[0], props[1]
counts = {}
for path, status in ((first, "draft"), (second, "adopted")):
    rec = json.loads(path.read_text(encoding="utf-8"))
    counts[path.stem] = rec.pop("record_count")
    rec.update(status=status, record_ids=["R-0001", "R-0002"])
    path.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
kept_adopted = second.read_text(encoding="utf-8")
made_now, renewed = el.propose()
assert made_now == [] and [p["id"] for p in renewed] == [first.stem], [p["id"] for p in renewed]
renewed_rec = json.loads(first.read_text(encoding="utf-8"))
assert "record_ids" not in renewed_rec and renewed_rec["record_count"] == counts[first.stem] and renewed_rec["renewed_at"]
assert second.read_text(encoding="utf-8") == kept_adopted
# Issue の下書きと台帳には、記録の番号を出さない（前と同じ）
os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions3.json")
assert cli("adopt", first.stem, "--by", "作る人").returncode == 0
issues = " ".join(p.read_text(encoding="utf-8") for p in (tmp / "local3/issues").glob("*.md"))
assert "R-00000001" not in issues and "R-0001" not in issues
ledger_text = (tmp / "versions3.json").read_text(encoding="utf-8")
assert "R-0" not in ledger_text and "record" not in ledger_text, ledger_text[:300]

# 5. take は置く形で測り直す: dropped_pii の欄を持たない束は、置く時にその欄が足されて大きくなる。確かめた束が上限の中でも、
# 置く形が上限を越えれば断り、何も置かない（前は置いてしまい、bundles が上限で読まずに数えなかった）
os.environ["OMOCHAE_ENGINE_LOOP"] = str(tmp / "local4")
edge = copy.deepcopy(SAMPLE)
edge.pop("dropped_pii")
edge["groups"] += [{**copy.deepcopy(SAMPLE["groups"][0]), "sheet_set": f"goraigo-v{n}"} for n in (8, 9)]
for i, g in enumerate(edge["groups"]):
    g["record_ids"] = [f"R-{i * el.MAX_COUNT + k:08d}" for k in range(el.MAX_COUNT)]
size_of = lambda b: len(json.dumps(b, ensure_ascii=False, indent=1).encode("utf-8")) + 1
pad = edge["groups"][0]["texts"][0]
pad["text"] = ""  # 字で 1 バイトずつ合わせる（ASCII の字は 1 字 1 バイト）
# 番号 1 つの大きさ（同じ桁なので、どれも同じ）から、上限の 300 バイト手前まで一度に減らす（1 つずつ測ると遅い）
whole = size_of(edge)
ids = edge["groups"][-1]["record_ids"]
ids.pop()
per = whole - size_of(edge)
drop = -(-(size_of(edge) - (LIMIT - 300)) // per)  # 切り上げ
del ids[len(ids) - drop:]
assert LIMIT - 300 - per < size_of(edge) <= LIMIT - 300, size_of(edge)
pad["text"] = "a" * (LIMIT - 3 - size_of(edge))  # 確かめる形で、上限の 3 バイト手前
assert 1 <= len(pad["text"]) <= el.MAX_TEXT and size_of(edge) == LIMIT - 3
assert size_of({**edge, "dropped_pii": 0}) > LIMIT
assert el.check_bundle(edge) == []
path, fails, _ = el.take(edge)
assert path is None and [(f.floor, f.where, f.message) for f in fails] == [("F13.bundle", "束", BIG)], [f.line() for f in fails]
assert not list((tmp / "local4").glob("bundles/*.json"))

# 6. 受け入れた報告: 上限より大きい物は読まずに数えない。ふだんの報告は今までどおり数える
os.environ["OMOCHAE_REPORTS"] = str(tmp / "reports")
(tmp / "reports/accepted").mkdir(parents=True)
report = {"template": "slider_fan", "form": "tab", "built": True, "moved": "not", "finish": 3, "reported_at": "2026-11-05T10:00:00+09:00",
          "reviewed_at": "2026-11-05T11:00+09:00", "stuck_step": 3}
(tmp / "reports/accepted/a.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
assert el.report_source()["groups"][0]["reports"] == 1
(tmp / "reports/accepted/b.json").write_text(" " * 100_000 + json.dumps(report, ensure_ascii=False), encoding="utf-8")
assert el.report_source()["groups"][0]["reports"] == 1
(tmp / "reports/accepted/b.json").write_text(" " * (100_000 - len(json.dumps(report, ensure_ascii=False))) + json.dumps(report, ensure_ascii=False), encoding="utf-8")
assert (tmp / "reports/accepted/b.json").stat().st_size == 100_000 and el.report_source()["groups"][0]["reports"] == 2  # 上限ちょうどは読む
assert el.MAX_REPORT_BYTES == 100_000

# 7. JSON にできない値を持つ束は、決まった誤り（F13.bundle）で断る（道具として直に呼ばれた時も、トレースバックにしない）
loop = []
loop.append(loop)
deep = []
for _ in range(100000):
    deep = [deep]
for change in (lambda b: b["groups"][0].update(record_ids={"R-0001"}), lambda b: b.update({"from": b"made-up-sample"}),
               lambda b: b["groups"][0].update(texts=loop), lambda b: b["groups"][0].update(measures=deep)):
    b = copy.deepcopy(SAMPLE)
    change(b)
    try:
        fails = el.check_bundle(b)
    except Exception as e:
        raise AssertionError(f"check_bundle が {type(e).__name__} で落ちた") from e
    assert [(f.floor, f.where) for f in fails] == [("F13.bundle", "束")], [f.line() for f in fails]
    assert el.take(b)[0] is None

print("OK test_engine_loop_size")
