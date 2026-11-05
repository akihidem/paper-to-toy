"""エンジンごとの改善の輪（omochae.engine_loop・#63）を確かめる。束の入口 → 案 → 人の採否 → 次の版 → 版ごとの数の並び。
話した事（考え・工夫・できた後の話。#65）も束で受け、手順の番号つきの工夫から案が起きる事を見る。
前の組の紙の記録から起きた案に、今の刷った組が並ぶ事を見る（#68）。"""
import copy
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from omochae import engine_loop as el  # noqa: E402

SAMPLE = json.loads((ROOT / "examples/bundles/sample_made_up.json").read_text(encoding="utf-8"))
# 連絡先の形の見本は、ここで組み立てる（ファイルに番号やアドレスの形を置かない）
PHONE = "-".join(("090", "1234", "5678"))
MAIL = "yamada" + "@" + "example" + ".jp"
tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["OMOCHAE_ENGINE_LOOP"] = str(tmp / "local")
os.environ["OMOCHAE_ENGINE_LEDGER"] = str(tmp / "versions.json")


def cli(*args):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    return subprocess.run([sys.executable, "-m", "omochae.engine_loop", *args], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)


def variant(change):
    b = copy.deepcopy(SAMPLE)
    change(b)
    return b


def put(name, b):
    path = tmp / name
    path.write_text(json.dumps(b, ensure_ascii=False), encoding="utf-8")
    return str(path)


# 1. 見本の束は通る。見本は束の欄を全部使う（サイトの側の試験が、同じ欄の一覧と照らすため）
assert el.check_bundle(SAMPLE) == [], [f.line() for f in el.check_bundle(SAMPLE)]
assert set(SAMPLE) == el.TOP_KEYS
assert set().union(*(set(g) for g in SAMPLE["groups"])) == el.GROUP_KEYS
assert set().union(*(set(t) for g in SAMPLE["groups"] for t in g["texts"])) == el.TEXT_KEYS
assert cli("check", "examples/bundles/sample_made_up.json").returncode == 0
# 話した事（#65）: 文の種類 3 つと、群の craft_steps。前の形の束（どちらも無い）も、そのまま通る
assert set(el.TEXT_KINDS) >= {"think", "craft", "keep"} and "craft_steps" in el.GROUP_KEYS
assert {"think", "craft", "keep"} <= {t["kind"] for g in SAMPLE["groups"] for t in g["texts"]}
TALK = ("think", "craft", "keep")


def old_shape(b):
    b.pop("current_sets", None)
    for g in b["groups"]:
        g.pop("craft_steps", None)
        g["texts"] = [t for t in g["texts"] if t["kind"] not in TALK]


OLD = variant(old_shape)
assert el.check_bundle(OLD) == [] and not any("craft_steps" in g for g in OLD["groups"])
# 今の刷った組（#68）: 束の上の段の、無くてもよい欄。雛形の id ごとの組の名
assert "current_sets" in el.TOP_KEYS and "current_sets" not in OLD and SAMPLE["current_sets"]["slider_fan"] == "goraigo-v10"

# 2. 決まりの外の欄・形は、束ごと断る（rc 3・F13.bundle）。何も置かない。知らせの文に、束の値を出さない
bads = [variant(lambda b: b.update(name="山田")), variant(lambda b: b["groups"][0].update(who="abc12345")),
        variant(lambda b: b["groups"][0]["texts"][0].update(by="山田")), variant(lambda b: b.update(exported_at="2026-11-05T15:00:30+09:00")),
        variant(lambda b: b["groups"][0]["stuck_steps"].update({"99": {"taps": 1, "people": 1}})),
        variant(lambda b: b["groups"][0].update(reports=9012345678)), variant(lambda b: b["groups"][0]["texts"][0].update(text="あ" * (el.MAX_TEXT + 1))),
        variant(lambda b: b["groups"][0]["texts"][0].update(kind="name")), variant(lambda b: b["groups"][0].update(minutes=[30, 20, 3])),
        variant(lambda b: b["groups"][0]["results"].update({"山田さんの家の電話で聞いた長い長い文をここへ": 1})),
        variant(lambda b: b["groups"].append(copy.deepcopy(b["groups"][0]))), variant(lambda b: b.update(schema="other/1")), ["束でない"],
        variant(lambda b: b["groups"][0]["craft_steps"].update({"3": {"talks": 2, "people": 2, "who": ["abc12345"]}})),
        variant(lambda b: b["groups"][0]["craft_steps"].update({"41": {"talks": 1, "people": 1}})),
        variant(lambda b: b["groups"][0].update(craft_steps=["山田"])), variant(lambda b: b["groups"][0]["texts"][0].update(kind="talk")),
        variant(lambda b: b.update(current_sets={"slider_fan": "山田さんの家で刷った組"})), variant(lambda b: b.update(current_sets=["goraigo-v10"])),
        variant(lambda b: b.update(current_sets={"slider fan": "goraigo-v10"}))]
for bad in bads:
    fails = el.check_bundle(bad)
    assert fails and all(f.floor == "F13.bundle" for f in fails), bad
    assert el.take(bad)[0] is None
    assert not any("山田" in f.line() or "9012345678" in f.line() for f in fails)
assert not list((tmp / "local").glob("bundles/*.json"))
r = cli("take", put("bad.json", bads[0]))
assert r.returncode == 3 and "F13.bundle" in r.stderr and "山田" not in r.stdout + r.stderr
assert cli("take", str(tmp / "no_such.json")).returncode == 4

# 3. 連絡先の形のある文: check は F13.pii で名指しし、take はその文を落として数だけ残す。落とした文は置き場にも画面にも出ない
for text in (f"電話は {PHONE}", MAIL, "０９０１２３４５６７８ まで", "〒" + "123" + "-" + "4567", "メールで知らせて", "https://x.example/a"):
    assert el.has_contact(text), text
for fine in ("折り線の向きが分からなかった", "手順 3 で 20 分かかった", "カットラインが細い", "扇が 90 度まで開いた"):
    assert not el.has_contact(fine), fine
dirty = variant(lambda b: b["groups"][0]["texts"].append({"kind": "impression", "step": None, "text": f"連絡は {PHONE} へ", "count": 1}))
assert [f.floor for f in el.check_bundle(dirty)] == ["F13.pii"]
assert PHONE not in el.check_bundle(dirty)[0].line()
assert cli("check", put("dirty.json", dirty)).returncode == 3
r = cli("take", put("dirty.json", dirty))
assert r.returncode == 0 and "落とした文 1 件" in r.stdout and PHONE not in r.stdout + r.stderr, r.stdout + r.stderr
placed = list((tmp / "local/bundles").glob("B-*.json"))
assert len(placed) == 1 and PHONE not in placed[0].read_text(encoding="utf-8")
kept = json.loads(placed[0].read_text(encoding="utf-8"))
assert kept["dropped_pii"] == 1 and len(kept["groups"][0]["texts"]) == len(SAMPLE["groups"][0]["texts"])
# 話した事（声から字にした物）も同じ床で落ちる。話した数（craft_steps）は数なので残る
spoken = variant(lambda b: b["groups"][0]["texts"].append({"kind": "craft", "step": 3, "text": f"分からなければ {PHONE} に聞いて", "count": 1}))
assert [f.floor for f in el.check_bundle(spoken)] == ["F13.pii"] and PHONE not in el.check_bundle(spoken)[0].line()

# 4. 同じ出し元の束は、新しい物だけを数える（束はその時までの全部なので、2 つ数えると 2 重になる）
newer = variant(lambda b: b.update(exported_at="2026-11-05T16:00+09:00"))
assert el.take(newer)[0] is not None
assert len(el.bundles()) == 1 and el.bundles()[0]["exported_at"] == "2026-11-05T16:00+09:00"
gs = el.groups(el.bundles())
assert gs[("slider_fan", "goraigo-v10")]["reports"] == 5

# 5. 案: 雛形・部品（共有の所）・生成の決まり の 3 種が出る。案は数と文だけで、新しい寸法の値を持たない。2 度起こさない
made = el.propose()
kinds = {p["target"]["kind"] for p in made}
assert kinds == {"template", "part", "rule"}, kinds
by_key = {p["key"]: p for p in made}
stuck = by_key["stuck:slider_fan:goraigo-v10:3"]
assert stuck["numbers"] == {"stuck_taps": 4, "stuck_people": 2, "quit_people": 1, "craft_talks": 2, "craft_people": 2, "reports": 5}
# 止まった段の案には、その段で話された工夫も付く（止まった所を、別の人がどう越えたかが並ぶ）
assert {t["kind"] for t in stuck["evidence"]} == {"stuck", "question", "craft"} and all(t["step"] == 3 for t in stuck["evidence"])
assert "stuck:slider_fan:goraigo-v10:5" not in by_key  # 1 人だけの段は案にしない
assert "stuck:pivot_counterweight:tora-v3:2" in by_key  # 印の無い記録だけの時は、札 3 回から
assert by_key["craft:slider_fan:goraigo-v10"]["numbers"] == {"fixes": 1, "ideas": 0, "craft_talks": 5, "keeps": 1, "reports": 5}
assert {t["kind"] for t in by_key["craft:slider_fan:goraigo-v10"]["evidence"]} == {"fix", "craft", "keep"}
assert by_key["craft:pivot_counterweight:tora-v3"]["numbers"] == {"fixes": 0, "ideas": 1, "craft_talks": 3, "keeps": 0, "reports": 2}  # 思いつきだけでも、工夫の言葉として案にする
assert by_key["motion:slider_fan:goraigo-v10"]["numbers"] == {"not_moved": 2, "moved": 2, "reports": 5}
# 作る前の考えは、動かない側の札が重なった時の案に付く。考えだけでは案にならない
assert {"explain", "think"} <= {t["kind"] for t in by_key["motion:slider_fan:goraigo-v10"]["evidence"]}
only_think = variant(lambda b: b.update(groups=[{"template": "slider_fan", "sheet_set": "goraigo-v10", "reports": 0,
                                                 "texts": [{"kind": "think", "step": None, "text": "扇は糸で引くと開くと思う", "count": 3}]}]))
assert el.check_bundle(only_think) == [] and el.drafts(el.groups([only_think])) == []
# 手順の番号つきの工夫: 止まったの札が重なっていない段でも、話した人が 2 人から案になる。1 人の段は案にしない。
# 止まった段の案が起きる段では、工夫はその案に付けるので、別の案を起こさない。印の無い記録だけの時は 3 件から
talk6 = by_key["talk:slider_fan:goraigo-v10:6"]
assert talk6["target"] == {"kind": "template", "name": "slider_fan"} and talk6["step"] == 6
assert talk6["numbers"] == {"craft_talks": 2, "craft_people": 2, "stuck_taps": 0, "stuck_people": 0, "reports": 5}
assert [(t["kind"], t["step"]) for t in talk6["evidence"]] == [("craft", 6)]
assert "talk:slider_fan:goraigo-v10:5" not in by_key and "talk:slider_fan:goraigo-v10:3" not in by_key
assert by_key["talk:pivot_counterweight:tora-v3:4"]["numbers"]["craft_talks"] == 3
few = el.groups([variant(lambda b: b["groups"][1]["craft_steps"].update({"4": {"talks": 2, "people": 0}}))])
assert not any(d["key"].startswith("talk:pivot_counterweight") for d in el.drafts(few))
# 前の形の束からは、前と同じ鍵の案だけが起きる（話した事の案は起きない）
assert {d["key"] for d in el.drafts(el.groups([OLD]))} == {k for k in by_key if not k.startswith("talk:")}
assert "motion:pivot_counterweight:tora-v3" not in by_key
fold = by_key["shared:fold:pivot_counterweight+slider_fan"]
assert fold["target"]["kind"] == "part" and fold["numbers"]["templates"] == 2
# 今の組と同じ組の群から起きた案には、組の並びを足さない。雛形の id が要る案は、今の組を持つ
assert stuck["current_set"] == "goraigo-v10" and all("今の組" not in p["why"] for p in made)
allowed = {"id", "status", "key", "target", "template", "sheet_set", "current_set", "step", "title", "numbers", "why", "evidence", "record_ids", "in_engine", "made_at"}
for p in made:
    assert set(p) == allowed and p["status"] == "draft", set(p) ^ allowed
    assert all(isinstance(v, int) and not isinstance(v, bool) for v in p["numbers"].values())  # 数は件数だけ（寸法の値でない）
    assert not {"params", "to", "value", "from"} & set(p["target"])
assert el.propose() == []
# 前の組の紙の記録（#68）: 案は今までどおり起きる（機械が「もう直った」と決めない）。「なぜか」に、今の組と、前の組の紙の物である事が並ぶ。
# 組の分からない記録には、分からない事が並ぶ。束が今の組を持たない時は、何も足さない
def add_old(b):
    fix = {"kind": "fix", "step": None, "text": "柄 / 先に土台を足した / 台が載せやすくなった", "count": 1}
    b["groups"].append({"template": "slider_fan", "sheet_set": "goraigo-v7", "reports": 2, "texts": [fix]})
    b["groups"].append({"template": "slider_fan", "sheet_set": "", "reports": 1, "texts": [fix]})


with_old = variant(add_old)
assert el.check_bundle(with_old) == []
old = {d["key"]: d for d in el.drafts(el.groups([with_old]))}
v7, unknown = old["craft:slider_fan:goraigo-v7"], old["craft:slider_fan:"]
assert v7["current_set"] == "goraigo-v10" and "今の組は goraigo-v10" in v7["why"] and "前の組の紙の物" in v7["why"] and "先に見る" in v7["why"]
assert "今の組は goraigo-v10" in unknown["why"] and "どの組の紙の物か分からない" in unknown["why"] and "前の組" not in unknown["why"]
assert "今の組" not in old["craft:slider_fan:goraigo-v10"]["why"]
assert "今の組は goraigo-v10" in el.issue_draft({**v7, "id": "EP-0000"}).split("---")[0]
no_cur = {d["key"]: d for d in el.drafts(el.groups([variant(lambda b: (add_old(b), b.pop("current_sets")))]))}
assert set(no_cur) == set(old) and all(no_cur[k]["numbers"] == old[k]["numbers"] for k in old)  # 鍵と数は変わらない
assert all("今の組" not in d["why"] and not d["current_set"] for d in no_cur.values())
# この repo に無い雛形の群も数える（サイトの側の雛形）。案には、無い事を書く。出し元が違う束の同じ群は、足して数える
only_site = variant(lambda b: (b.update({"from": "other-site", "groups": [b["groups"][2]]}), b["groups"][0]["stuck_steps"].update({"4": {"taps": 2, "people": 2}})))
assert el.take(only_site)[0] is not None
assert el.groups(el.bundles())[("den_den", "den_den-v1")]["reports"] == 2
extra = {p["key"]: p for p in el.propose()}
assert extra["stuck:den_den:den_den-v1:4"]["in_engine"] is False
assert "今の組は den_den-v2" in extra["stuck:den_den:den_den-v1:4"]["why"]
assert "一覧に無い" in el.issue_draft(extra["stuck:den_den:den_den-v1:4"])

# 6. 採否は人が決める。名前が無いと rc 3。採った案だけが次の版の予定に入り、Issue の下書き（4 つの見出し）が出る
sid, fid, mid = stuck["id"], by_key["craft:slider_fan:goraigo-v10"]["id"], by_key["motion:slider_fan:goraigo-v10"]["id"]
r = cli("adopt", sid)
assert r.returncode == 3 and "F13.human" in r.stderr
assert cli("adopt", "EP-9999", "--by", "作る人").returncode == 3
assert cli("adopt", "../x", "--by", "作る人").returncode == 3
assert cli("adopt", sid, "--by", "作る人").returncode == 0
assert cli("reject", fid, "--by", "作る人", "--note", "次の試行を待つ").returncode == 0
led = el.ledger()
assert [p["id"] for p in led["next"]] == [sid] and led["versions"] == []
ledger_text = (tmp / "versions.json").read_text(encoding="utf-8")
# 台帳は git に入る物。作った人の文も、決めた人の名前も入れない
assert "折り線の向きが分からなかった" not in ledger_text and "作る人" not in ledger_text and "evidence" not in ledger_text
draft = (tmp / "local/issues" / f"{sid}.md").read_text(encoding="utf-8")
assert all(h in draft for h in ("## 目的", "## なぜか（根拠）", "## どうしたらいいか", "## ゴールの要件")) and "足は山折りですか" in draft
assert "止まったの札 4" in draft and "stuck_taps" not in draft  # 数は呼び方を付けて出す
assert "話した工夫（手順 3）: 「折る前に、定規で折り線をなぞった」" in draft and "craft_talks" not in draft
assert "話した工夫（手順 6）" in el.issue_draft(talk6) and "組み方の文" in el.issue_draft(talk6)
# 作った人の言葉は、4 つの見出しの外の「手元の材料」にだけ出る（Issue にそのまま写さない物として分ける）
head, _, material = draft.partition("---")
assert el.MATERIAL in material and "写さない" in material and "## " not in material
assert all(t["text"] in material and t["text"] not in head for t in stuck["evidence"]) and len(stuck["evidence"]) >= 4
assert set(el.NUMBER_JA) >= {k for p in made for k in p["numbers"]}
assert not (tmp / "local/issues" / f"{fid}.md").exists()
assert cli("adopt", sid, "--by", "作る人").returncode == 3  # 決め直しはしない
assert cli("adopt", fid, "--by", "作る人").returncode == 3

# 7. 次の版: commit と人が要る。刻むと、版の番号・採った案・commit が台帳に残り、予定は空になる。同じ案を 2 度刻めない
assert cli("release", "--by", "作る人").returncode == 3
assert cli("release", "--commit", "abc1234").returncode == 3
assert cli("release", "--commit", "abc1234", "--by", "作る人", "--sheet-set", "slider_fan").returncode == 3
r = cli("release", "--commit", "abc1234", "--by", "作る人", "--sheet-set", "slider_fan=goraigo-v11")
assert r.returncode == 0 and "版 1" in r.stdout, r.stdout + r.stderr
led = el.ledger()
assert led["next"] == [] and [(v["version"], v["commit"], [p["id"] for p in v["proposals"]]) for v in led["versions"]] == [(1, "abc1234", [sid])]
assert led["versions"][0]["sheet_sets"] == {"slider_fan": "goraigo-v11"}
assert json.loads((tmp / "local/proposals" / f"{sid}.json").read_text(encoding="utf-8"))["status"] == "released"
assert cli("release", "--commit", "abc1234", "--by", "作る人").returncode == 3  # 採った案が無いまま刻まない
assert cli("adopt", mid, "--by", "作る人").returncode == 0 and cli("release", "--commit", "def5678", "--by", "作る人").returncode == 0
assert [v["version"] for v in el.ledger()["versions"]] == [1, 2]
broken = el.ledger()
broken["next"].append({"id": sid, "target": {}, "title": "", "numbers": {}})
(tmp / "versions.json").write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
assert cli("version").returncode == 4  # 同じ案が 2 度ある台帳は、読めない物として止める
broken["next"].pop()
(tmp / "versions.json").write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")

# 8. 並べる: 次の版の紙の束が来たら、刷った組ごとに数が並ぶ。判定の語も割合も出さない。組は名の数の順（v9 → v10 → v11）
after = variant(lambda b: (b.update(exported_at="2026-11-06T10:00+09:00"), b["current_sets"].update(slider_fan="goraigo-v11"),
                           b["groups"].append({**copy.deepcopy(b["groups"][0]), "sheet_set": "goraigo-v9", "reports": 1}),
                           b["groups"].append({"template": "slider_fan", "sheet_set": "goraigo-v11", "reports": 3, "results": {"動いた": 3},
                                               "moved_word": "動いた", "not_moved_word": "動かない", "stuck_steps": {"3": {"taps": 1, "people": 1}},
                                               "quit_steps": {}, "minutes": [10, 25, 3], "measures": {}, "record_ids": [],
                                               "texts": [{"kind": "craft", "step": 3, "text": "足の向きは、絵を見て合わせた", "count": 1}]})))
assert el.take(after)[0] is not None
r = cli("compare")
assert r.returncode == 0, r.stderr
out = r.stdout
rows = [ln for ln in out.splitlines() if ln.startswith("| goraigo-")]
# 今の組の行に印が付く。今の組は、新しい束の値で読む（前の束では v10 が今の組だった）
assert [ln.split("|")[1].strip() for ln in rows] == ["goraigo-v9", "goraigo-v10", "goraigo-v11（今の組）"], rows
assert "| goraigo-v10 | — | 5 件 | 動いた 2・動かない 2・わからない 1 | 手順 3: 4 回・2 人、手順 5: 1 回・1 人 | 手順 3: 1 | 20〜40（3 件） | 考え 1・工夫 5・できた後 1 |" in out, out
assert f"| goraigo-v11（今の組） | 版 1（{sid}） | 3 件 | 動いた 3 | 手順 3: 1 回・1 人 | — | 10〜25（3 件） | 工夫 1 |" in out, out
assert "| tora-v3（今の組） |" in out
assert "| den_den-v1 | — | 2 件 | 鳴った 2 | 手順 4: 2 回・2 人 | — | — | — |" in out, out
assert "判定はしない" in out and "den_den（この repo の雛形の一覧に無い）" in out
for word in ("効いた", "改善し", "良くな", "悪くな", "増えた", "減った", "上がっ", "下がっ", "%", "％", "↑", "↓", "平均"):
    assert word not in out, word

# 9. repo の台帳（git に入る物）は読めて、作った人の文の欄を持たない
os.environ.pop("OMOCHAE_ENGINE_LEDGER")
real = el.ledger()
assert real["versions"] and real["versions"][0]["version"] == 1
assert all(set(p) <= {"id", "target", "title", "numbers", "adopted_at"} for v in real["versions"] for p in v["proposals"])
assert all(set(p) <= {"id", "target", "title", "numbers", "adopted_at"} for p in real["next"])

print("OK test_engine_loop")
