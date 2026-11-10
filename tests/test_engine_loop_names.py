"""改善の輪（omochae.engine_loop）の名の欄と版の注に、連絡先の形の検査を当てた事を確かめる（セキュリティの点検 2026-11-07）。
名の欄（束の from・current_sets の鍵と値・群の template・sheet_set・paper）と release の sheet_sets の鍵と値・note は、
案の題や版の台帳（data/engine/versions.json。git に入る）に写る。作った人の文と同じ見方で、連絡先の形があれば断る。
誤って止めない事も見る: 今の見本・試験・台帳・雛形の一覧にある名と、サイトの紙の名の形（出典の ID.仮説）と、台帳の今の注は全部通る。
出典の ID（名と注）・commit の番号と Issue の番号（注だけ）は数字が多いので、その決まった形だけを伏せてから見る。伏せる形に番号を隠せない事も見る。"""
import copy
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from omochae import engine_loop as el  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402
from omochae.sheets import READINGS  # noqa: E402

SAMPLE = json.loads((ROOT / "examples/bundles/sample_made_up.json").read_text(encoding="utf-8"))
REAL_LEDGER = json.loads((ROOT / "data/engine/versions.json").read_text(encoding="utf-8"))
tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["OMOCHAE_ENGINE_LOOP"] = str(tmp / "local")
os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions.json")
os.environ["OMOCHAE_REPORTS"] = str(tmp / "no-reports")
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
PII = "連絡先の形（数字の多い所か、@・メール・電話・URL などの語）がある"
# 連絡先の形の見本は、ここで組み立てる（ファイルに番号やアドレスの形を置かない）。どれも名の形（英数字と . - _）に入る物
PHONE = "-".join(("090", "1234", "5678"))
DIGITS = "".join(("090", "1234", "5678"))
DOMAIN = ".".join(("yamada", "example", "jp"))
CONTACTS = (PHONE, DIGITS, DOMAIN, "twitter" + "_yamada", "line" + "_taro_1")
assert all(el.NAME.fullmatch(c) and el.has_contact(c) for c in CONTACTS)


def cli(*args):
    return subprocess.run([sys.executable, "-m", "omochae.engine_loop", *args], cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=60)


def with_name(field, name, base=SAMPLE):
    """その名の欄に name を入れた束。"""
    b = copy.deepcopy(base)
    if field == "from":
        b["from"] = name
    elif field == "current_sets.key":
        b["current_sets"][name] = "goraigo-v10"
    elif field == "current_sets.value":
        b["current_sets"]["slider_fan"] = name
    else:
        gi, key = field.split(".")
        b["groups"][int(gi[7:-1])][key] = name
    return b


FIELDS = ("from", "current_sets.key", "current_sets.value", "groups[0].template", "groups[0].sheet_set", "groups[0].paper", "groups[2].paper")
WHERE = {"current_sets.key": "current_sets", "current_sets.value": "current_sets"}

# 1. 名の欄に連絡先の形があれば、束ごと断る（F13.bundle。take は何も置かない。文の様に落として先へ進むと、名は落とせずに題へ写るため）。
# 知らせの文に、その値を出さない
for field in FIELDS:
    for c in CONTACTS:
        b = with_name(field, c)
        fails = el.check_bundle(b)
        assert [(f.floor, f.where, f.message) for f in fails] == [("F13.bundle", WHERE.get(field, field), PII)], (field, c, [f.line() for f in fails])
        assert not any(c in f.line() for f in fails)
        assert el.take(b)[0] is None, (field, c)
assert not list((tmp / "local").glob("bundles/*.json"))
(tmp / "b.json").write_text(json.dumps(with_name("groups[0].paper", PHONE), ensure_ascii=False), encoding="utf-8")
r = cli("take", str(tmp / "b.json"))
assert r.returncode == 3 and PII in r.stderr and PHONE not in r.stdout + r.stderr, (r.returncode, r.stderr)
assert not list((tmp / "local").glob("bundles/*.json")) and not list((tmp / "local").glob("proposals/*.json"))
# 置いた後に手で名を書き換えた束も、数えない（置き場の束は読むたびに確かめ直す）
assert el.take(SAMPLE)[0] is not None and len(el.bundles()) == 1
placed = next((tmp / "local/bundles").glob("B-*.json"))
placed.write_text(json.dumps(with_name("groups[0].sheet_set", PHONE), ensure_ascii=False), encoding="utf-8")
assert el.bundles() == []

# 2. 版を刻む時の刷った組（鍵と値）と注にも、同じ見方を当てる。落ちた時は台帳に触らない
row = lambda pid: {"id": pid, "target": {"kind": "template", "name": "slider_fan"}, "title": "前の案", "numbers": {}, "adopted_at": "2026-11-06"}
led0 = {"versions": [], "next": [row("EP-0001")]}
(tmp / "versions.json").write_text(json.dumps(led0, ensure_ascii=False), encoding="utf-8")
for sheet_sets, note, where in (({"slider_fan": PHONE}, "", "sheet_sets"), ({"slider_fan." + DIGITS: "goraigo-v11"}, "", "sheet_sets"),
                                ({"slider_fan": "goraigo-v11"}, f"連絡は {PHONE} へ", "note"), ({}, f"{DOMAIN} に聞いた", "note"),
                                ({}, "合体 " + DIGITS, "note")):  # 数字だけの並びは commit の番号の形に入れない（伏せない）
    n, fails = el.release("abc1234", "作る人", sheet_sets, note)
    assert n is None and [(f.floor, f.where, f.message) for f in fails] == [("F13.version", where, PII)], (sheet_sets, note, [f.line() for f in fails])
    assert not any(PHONE in f.line() or DIGITS in f.line() for f in fails)
assert json.loads((tmp / "versions.json").read_text(encoding="utf-8")) == led0
r = cli("release", "--commit", "abc1234", "--by", "作る人", "--sheet-set", "slider_fan=goraigo-v11", "--note", f"電話 {PHONE}")
assert r.returncode == 3 and "F13.version" in r.stderr and PHONE not in r.stdout + r.stderr, (r.returncode, r.stderr)
assert json.loads((tmp / "versions.json").read_text(encoding="utf-8")) == led0

# 3. 誤って止めない: 今ある名を全部集め、どの名の欄に入れても束が通る事を見る
names = set()
for p in (ROOT / "examples/bundles").glob("*.json"):
    b = json.loads(p.read_text(encoding="utf-8"))
    names |= {b["from"], *b.get("current_sets", {}), *b.get("current_sets", {}).values()}
    names |= {g.get(k) for g in b["groups"] for k in ("template", "sheet_set", "paper")} - {None, ""}
entries = [e for v in REAL_LEDGER["versions"] for e in v["proposals"]] + REAL_LEDGER["next"]
papers = {m.group(1) for e in entries for m in [re.search(r"（紙 ([^）]+)）", e["title"])] if m}
assert {"NDL-1187053-R0000014-R.H-A", "NDL-1187053-R0000005-L.H-A"} <= papers, papers  # 台帳の題に入っている、サイトの紙の名
names |= papers | {s for v in REAL_LEDGER["versions"] for kv in v["sheet_sets"].items() for s in kv}
names |= {e["target"]["name"] for e in entries if el.NAME.fullmatch(e["target"]["name"])}
for tid, tpl in TEMPLATES.items():
    forms = [str(f) for f in getattr(tpl, "FORMS", ())]
    names |= {tid, *forms, *(f"{tid}.{f}" for f in forms), tpl.SOURCE, *getattr(tpl, "SOURCES", {}).values()}
names |= {f for m in READINGS.values() for kv in m.items() for f in kv}
sources = {p.stem for p in (ROOT / "data/sources").glob("*.json")}
names |= sources
# サイトの紙の名は「出典の ID.仮説」（版 2 からは .v版 を足す）。サイトの出典の ID は、頁と左右の後に番号が付く物もある（-L-4）
site_sources = sources | {f"NDL-1187053-R{n:07d}-{side}-{k}" for n in (4, 5, 8, 20) for side in "LR" for k in (2, 3, 4, 5)}
names |= {f"{s}.{h}{v}" for s in site_sources for h in ("H-A", "H-B", "H-C", "H-D", "H-E") for v in ("", ".v2", ".v12")}
# 試験の束と、サイトの束の試験で使う名（出し元・刷った組・雛形）
names |= {el.REPORTS_FROM, "made-up-sample", "other-site", "utsushi", "busy", "goraigo-v7", "goraigo-v9", "goraigo-v11", "goraigo-v12", "goraigo-v13",
          "goraigo-v14", "tora-v2", "tora-v3", "tora-v9", "spin-v1", "den_den", "den_den-v1", "den_den-v2", "sample-toy.H-A", "saru_take",
          "x-v1", "y-v1", "z-v1", "balance_toy", "spin_toy", "string_pull", "stick_prop", "no_such"}
names = sorted(n for n in names if isinstance(n, str) and el.NAME.fullmatch(n))
assert len(names) > 500, len(names)
# 名の欄だけを見るので、文の無い小さな束で回す（見本の束の文を毎回確かめ直すと、名の数 × 欄の数で遅い）
mini = {**{k: SAMPLE[k] for k in ("schema", "exported_at", "from", "current_sets")},
        "groups": [{k: g[k] for k in ("template", "sheet_set") if k in g} | ({"paper": g["paper"]} if "paper" in g else {}) for g in SAMPLE["groups"]]}
assert el.check_bundle(mini) == []
for name in names:
    for field in FIELDS:
        fails = [f for f in el.check_bundle(with_name(field, name, mini)) if f.message == PII]
        assert not fails, (field, name, [f.line() for f in fails])
assert el.check_bundle(SAMPLE) == []

# 4. 誤って止めない: 台帳の今の注（commit と Issue の番号を書いた物）と刷った組は、版を刻む時に通る
os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions2.json")
(tmp / "versions2.json").write_text(json.dumps({"versions": [], "next": [row(f"EP-{i:04d}") for i in range(1, 8)]}, ensure_ascii=False), encoding="utf-8")
for i, v in enumerate(REAL_LEDGER["versions"], 1):
    n, fails = el.release(v["commit"], "作る人", v["sheet_sets"], v["note"], [f"EP-{i:04d}"])
    assert n == i and fails == [], (v["version"], [f.line() for f in fails])
    assert el.ledger()["versions"][-1]["note"] == v["note"][:el.MAX_TEXT] and el.ledger()["versions"][-1]["sheet_sets"] == v["sheet_sets"]
assert len(REAL_LEDGER["versions"]) == 7

# 5. 伏せる形は狭い: 出典の ID の桁が違う物・続けて並べた Issue の番号・英字の無い数字の並びは伏せず、番号を隠せない
# 名の欄で伏せるのは出典の ID だけ（commit の形は伏せないので、英字を前に付けた番号も断る）
for name in ("NDL-" + DIGITS + "-R0000014", "NDL-1187053-R" + DIGITS, "a" + DIGITS, "cafe-" + DIGITS):
    assert [f.message for f in el.check_bundle(with_name("groups[0].paper", name))] == [PII], name
for note in ("#" + "#".join(("090", "1234", "5678")), "commit " + DIGITS, "#" + DIGITS):
    os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions.json")
    n, fails = el.release("abc1234", "作る人", {}, note)
    assert n is None and [f.where for f in fails] == ["note"], note

print("OK test_engine_loop_names")
