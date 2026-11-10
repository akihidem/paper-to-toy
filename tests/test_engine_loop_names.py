"""改善の輪（omochae.engine_loop）の名の欄と版の注に、連絡先の形の検査を当てた事を確かめる（セキュリティの点検 2026-11-07）。
名の欄（束の from・current_sets の鍵と値・群の template・sheet_set・paper）と release の sheet_sets の鍵と値・note は、
案の題や版の台帳（data/engine/versions.json。git に入る）に写る。作った人の文と同じ見方で、連絡先の形があれば断る。
誤って止めない事も見る: 今の見本・試験・台帳・雛形の一覧にある名と、サイトの紙の名の形（出典の ID.仮説）と、台帳の今の注は全部通る。
出典の頁の ID（名と注）・commit の番号と Issue の番号（注だけ）は数字が多いので、在ると確かめた物だけを伏せてから見る
（data/sources に今ある頁・この repo に在る commit か台帳の版の commit・台帳の注か履歴の「Merge pull request #N」に在る 1 つずつの番号）。
形だけで伏せていた時に通った形（14 桁の頁・英字を足した番号・字を挟んで並べた番号・前の注の 16 進を使う 2 回の release）を断る事と、
release の commit も、この repo に在る物か台帳の版の commit だけを受ける事も見る。
この検査は、うっかり入る連絡先を止める補助で、版の注は刻む人が読む（字で区切って在る番号を並べる・台帳の注の番号を使って 2 回に
またがる形は、式では止め切れない）。git で確かめる所は、この repo の git の履歴が読める時だけ見る（読めない時は 1 行出して飛ばす）。"""
import copy
import json
import os
import pathlib
import re
import shutil
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
# 版を刻む commit は、repo の台帳の版の commit を使う。git の無い写しでも、ここは回る
COMMIT_SHORT, COMMIT_FULL = REAL_LEDGER["versions"][-1]["commit"][:7], REAL_LEDGER["versions"][-2]["commit"]


def git(*a):
    """この repo の git の答え。git が無い・.git が無い時は None（git で確かめる所を飛ばす）。"""
    r = subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, timeout=60) if shutil.which("git") else None
    return r.stdout.strip() if r and r.returncode == 0 and r.stdout.strip() else None


HEAD = git("rev-parse", "HEAD")  # 履歴が読めれば、台帳に書かれていない commit（今の頭）でも在ると確かめられる
if HEAD is None:
    print("確かめられない: この repo の git の履歴が読めないので、git で確かめる所（台帳に無い commit・履歴の Issue の番号）は見ない")


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
                                ({}, "合体 " + DIGITS, "note")):  # 数字だけの並びは、この repo の commit でないので伏せない
    n, fails = el.release(COMMIT_SHORT, "作る人", sheet_sets, note)
    assert n is None and [(f.floor, f.where, f.message) for f in fails] == [("F13.version", where, PII)], (sheet_sets, note, [f.line() for f in fails])
    assert not any(PHONE in f.line() or DIGITS in f.line() for f in fails)
assert json.loads((tmp / "versions.json").read_text(encoding="utf-8")) == led0
r = cli("release", "--commit", COMMIT_SHORT, "--by", "作る人", "--sheet-set", "slider_fan=goraigo-v11", "--note", f"電話 {PHONE}")
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

# 4. 誤って止めない: 台帳の今の注（commit と Issue の番号を書いた物）と刷った組は、版を刻む時に通る。
# 注の中の commit は、この repo の履歴に在る（git で確かめる）。コードは注の中の 16 進を「在る」に数えないので、履歴の無い写し
# （1 本の commit で入れた写し・.git の無い写し）では、ここだけ確かめ方を台帳に書かれた番号の集まりに差し替えて回す
noted = {v["commit"] for v in REAL_LEDGER["versions"]} | {h for v in REAL_LEDGER["versions"] for h in el.HEX.findall(v["note"])}
is_commit = el._is_commit
if not all(is_commit(h) for h in noted):
    print("確かめられない: 台帳の注の commit がこの repo の履歴に無いので、4 は台帳に書かれた番号で確かめる")
    el._is_commit = lambda token: any(c.startswith(token) for c in noted)
os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions2.json")
(tmp / "versions2.json").write_text(json.dumps({"versions": [], "next": [row(f"EP-{i:04d}") for i in range(1, 8)]}, ensure_ascii=False), encoding="utf-8")
for i, v in enumerate(REAL_LEDGER["versions"], 1):
    n, fails = el.release(v["commit"], "作る人", v["sheet_sets"], v["note"], [f"EP-{i:04d}"])
    assert n == i and fails == [], (v["version"], [f.line() for f in fails])
    assert el.ledger()["versions"][-1]["note"] == v["note"][:el.MAX_TEXT] and el.ledger()["versions"][-1]["sheet_sets"] == v["sheet_sets"]
assert len(REAL_LEDGER["versions"]) == 7
el._is_commit = is_commit

# 5. 伏せるのは、在ると確かめた物だけ（形だけで伏せると、その形の中に番号を入れて運べた）
# 名の欄: 伏せるのは data/sources に今ある出典の頁の ID だけ。無い頁・桁の違う物・英字を前に付けた番号は伏せずに断る
for name in ("NDL-" + "0901234" + "-R" + "5678000", "NDL-" + "0901234" + "-R" + "5678000" + ".H-A", "NDL-1187053-R0000099-L.H-A",
             "NDL-" + DIGITS + "-R0000014", "NDL-1187053-R" + DIGITS, "a" + DIGITS, "cafe-" + DIGITS):
    assert [f.message for f in el.check_bundle(with_name("groups[0].paper", name))] == [PII], name
assert "NDL-1187053-R0000014" in el._source_pages() and "NDL-1187053-R0000099" not in el._source_pages()
os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions.json")
# 版の注: commit は、在ると確かめた物だけを伏せる（英字を 1 つ足した番号・ドメインの前の 16 進は伏せない）。
# Issue の番号は、台帳の注か履歴の「Merge pull request #N」に在る物の 1 つずつだけを伏せる（字を挟んで並べた作り物の番号は伏せない）。
# 区切りや空白だけを挟んで並べた物も伏せない
for note in ("#" + "#".join(("090", "1234", "5678")), "commit " + DIGITS, "#" + DIGITS, f"連絡は {DIGITS}a へ", "badface1" + ".com", "deadbeef" + ".jp",
             "-".join("#" + x for x in ("090", "1234", "5678")), " ".join("#" + x for x in ("090", "1234", "5678")),
             " ".join("#" + x for x in ("1234", "5678", "9012")), "・".join("#" + x for x in ("1234", "5678")),
             "連絡は 090 へ " + " か ".join("#" + x for x in ("1234", "5678")), "と".join("#" + x for x in ("090", "1234", "5678"))):
    n, fails = el.release(COMMIT_SHORT, "作る人", {}, note)
    assert n is None and [f.where for f in fails] == ["note"], (note, [f.line() for f in fails])
# 台帳の版の commit と、台帳の注の Issue の番号は、git が無くても伏せる（台帳の今の注の書き方。4 で全部を見た）
for note in (f"合体 {COMMIT_FULL}", f"#106・合体 {COMMIT_SHORT}", f"（#117・合体 {COMMIT_SHORT} と #122・合体 {COMMIT_FULL[:8]}）"):
    assert not el._has_contact_outside_ids(note, note=True), note
# 伏せたかを、数字の数で見る: 伏せれば残るのは 4 桁で当たらず、伏せなければ番号の 3 桁と足して 7 桁で当たる
assert not el._has_contact_outside_ids("#106 1234", note=True) and el._has_contact_outside_ids("#999 1234", note=True)
if HEAD:  # 台帳に無い commit（今の頭）と、台帳の注に無い履歴の Issue の番号も伏せる
    assert not el._has_contact_outside_ids(f"合体 {HEAD} 1234", note=True)
    pr = sorted(set(el._merged_prs()) - el._ledger_marks()[1] - {"999"}, key=lambda n: (-len(n), n))
    if pr and len(pr[0]) == 3:  # 履歴に合体の記録が無い写し（1 本の commit で入れた写し）では見ない
        assert not el._has_contact_outside_ids(f"#{pr[0]} 1234", note=True), pr[:3]
assert json.loads((tmp / "versions.json").read_text(encoding="utf-8")) == led0

# 6. release の commit も、この repo に在る物か台帳の版の commit だけを受ける（形だけだと、数字だけの番号が commit として台帳に入った）。
# 短い番号は数字だけの事もあるので、形では分けない（この repo の、数字だけの短い番号は通る）
for commit in (DIGITS, "abc1234", "0" * 40):
    n, fails = el.release(commit, "作る人", {"slider_fan": "goraigo-v11"}, "")
    assert n is None and [(f.floor, f.where) for f in fails] == [("F13.version", "commit")], (commit, [f.line() for f in fails])
    assert DIGITS not in " ".join(f.line() for f in fails)
r = cli("release", "--commit", DIGITS, "--by", "作る人")
assert r.returncode == 3 and "F13.version" in r.stderr and DIGITS not in r.stdout + r.stderr, (r.returncode, r.stderr)
assert json.loads((tmp / "versions.json").read_text(encoding="utf-8")) == led0
# 前の注に書いた 16 進は「在る」に数えない: 6 桁の数字を持つ 16 進を 1 度注に書いて刻み、次の注で続けて書いても伏せない。
# release の commit としても受けない（前は、台帳の注の 16 進を数えていたので、2 回の release で番号を運べた）
hexed = "a" + "090123" + "f"
assert not el.has_contact("合体 " + hexed)  # 6 桁なので、1 回目の注は通る
os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions5.json")
(tmp / "versions5.json").write_text(json.dumps({"versions": [], "next": [row("EP-0001"), row("EP-0002")]}, ensure_ascii=False), encoding="utf-8")
assert el.release(COMMIT_SHORT, "作る人", {}, "合体 " + hexed, ["EP-0001"]) == (1, [])
n, fails = el.release(COMMIT_SHORT, "作る人", {}, f"合体 {hexed} の続き 4567", ["EP-0002"])
assert n is None and [f.where for f in fails] == ["note"], [f.line() for f in fails]
n, fails = el.release(hexed, "作る人", {}, "", ["EP-0002"])
assert n is None and [(f.floor, f.where) for f in fails] == [("F13.version", "commit")], [f.line() for f in fails]
assert "台帳の版の commit" in fails[0].message  # 断る時の字は、受ける物（この repo の commit か、台帳の版の commit）と合う
os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions.json")
if HEAD:
    digit_only = next((c for c in git("log", "--format=%h", "--abbrev=7", "-n", "2000").split() if re.fullmatch(r"[0-9]{7}", c)), None)
    if digit_only:  # 浅い複製で見つからない時は見ない
        os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions3.json")
        (tmp / "versions3.json").write_text(json.dumps(led0, ensure_ascii=False), encoding="utf-8")
        assert el.release(digit_only, "作る人", {}, "") == (1, []), digit_only
        assert el.ledger()["versions"][0]["commit"] == digit_only
        os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions.json")
# git が無い（確かめられない）時: 台帳の版の commit と注の番号は今までどおり伏せ、版も刻める（台帳は写しと一緒に動く）。
# 台帳に無い commit は、在ると言わない（伏せず、版も刻まない）
path = os.environ.get("PATH", "")
os.environ["PATH"] = str(tmp / "no-bin")
el._is_commit.cache_clear()
el._merged_prs.cache_clear()
try:
    assert not el._has_contact_outside_ids(f"（#117・合体 {COMMIT_SHORT} と #122・合体 {COMMIT_FULL}）", note=True)
    os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions4.json")
    (tmp / "versions4.json").write_text(json.dumps(led0, ensure_ascii=False), encoding="utf-8")
    assert el.release(COMMIT_SHORT, "作る人", {}, REAL_LEDGER["versions"][-1]["note"]) == (1, [])
    os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions.json")
    if HEAD:
        assert el._has_contact_outside_ids(f"合体 {HEAD}", note=True)
        n, fails = el.release(HEAD, "作る人", {}, "")
        assert n is None and [f.where for f in fails] == ["commit"], [f.line() for f in fails]
finally:
    os.environ["PATH"] = path
    os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions.json")
    el._is_commit.cache_clear()
    el._merged_prs.cache_clear()
assert json.loads((tmp / "versions.json").read_text(encoding="utf-8")) == led0

print("OK test_engine_loop_names")
