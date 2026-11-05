"""作った人の報告の入口（omochae.intake）を確かめる（Issue #22）。"""
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from omochae import feedback, intake  # noqa: E402

GOOD = {"template": ["spinner"], "form": ["pinwheel"], "built": ["yes"], "moved": ["partly"], "finish": ["3"],
        "motion_notes": ["息で回った"], "finish_notes": ["羽の角がよれた"],
        "p0_kind": ["fit"], "p0_step": ["4"], "p0_note": ["羽が柄に擦れた"], "p1_kind": [""],
        "no_pii": ["yes"], "age": ["yes"]}

with tempfile.TemporaryDirectory() as d:
    base = pathlib.Path(d)
    # 1. 通る報告は受付箱に置かれる。同意の欄は報告に入らない
    rid, msgs = intake.submit(GOOD, base)
    assert rid and msgs == [], msgs
    saved = json.loads((base / "inbox" / f"{rid}.json").read_text(encoding="utf-8"))
    assert feedback.check(saved) == [] and "no_pii" not in saved and saved["problems"] == [
        {"kind": "fit", "note": "羽が柄に擦れた", "step": 4}], saved
    # 2. 同意が無い・検査に落ちる・個人の情報の形がある物は置かれず、知らせに値を出さない
    for bad in ({**GOOD, "age": [""]}, {**GOOD, "moved": ["yes"]}, {**GOOD, "motion_notes": ["電話090-1234-5678"]}):
        before = sorted((base / "inbox").glob("*.json"))
        rid2, msgs = intake.submit(bad, base)
        assert rid2 is None and msgs and sorted((base / "inbox").glob("*.json")) == before, bad
        assert "090-1234-5678" not in " ".join(msgs)
    # 3. 受け入れは、人が打った ID が合わないと断る。合えば accepted へ移り、集計に出る
    assert intake.accept(rid, base, confirm="B-wrong")[0] is False
    assert intake.accept(rid, base, confirm=rid)[0] is True
    assert not (base / "inbox" / f"{rid}.json").exists() and (base / "accepted" / f"{rid}.json").exists()
    s = feedback.summarize([json.loads(p.read_text(encoding="utf-8")) for p in (base / "accepted").glob("*.json")])
    assert s[("spinner", "pinwheel")]["n"] == 1
    # 4. 却下は中身を消し、ID と決まった理由の語だけを記録に残す
    rid3, _ = intake.submit(GOOD, base)
    assert intake.reject(rid3, base, "自由な文")[0] is True
    log = (base / "log" / "review.log").read_text(encoding="utf-8")
    assert rid3 in log and "自由な文" not in log and not (base / "inbox" / f"{rid3}.json").exists()
    # 5. 端末でない入力からの受け入れは断る（CLI）
    rid4, _ = intake.submit(GOOD, base)
    r = subprocess.run([sys.executable, "-m", "omochae.intake", "--base", str(base), "review", "accept", rid4], input=rid4 + "\n",
                       cwd=ROOT, capture_output=True, text=True, env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"})
    assert r.returncode == 3 and (base / "inbox" / f"{rid4}.json").exists(), r.stderr
# 5b. 作る様子の欄（#23）も送れ、空なら報告に入らない
with tempfile.TemporaryDirectory() as d:
    rid, msgs = intake.submit({**GOOD, "stuck_step": ["4"], "gave_up": ["no"], "minutes": ["35"], "p1_kind": ["guide"],
                               "p1_note": ["折る向きの説明が分からない"]}, pathlib.Path(d))
    assert rid, msgs
    rep = json.loads((pathlib.Path(d) / "inbox" / f"{rid}.json").read_text(encoding="utf-8"))
    assert rep["stuck_step"] == 4 and rep["gave_up"] is False and rep["minutes"] == 35 and rep["problems"][1]["kind"] == "guide"
    rid2, _ = intake.submit(GOOD, pathlib.Path(d))
    rep2 = json.loads((pathlib.Path(d) / "inbox" / f"{rid2}.json").read_text(encoding="utf-8"))
    assert "stuck_step" not in rep2 and "minutes" not in rep2 and "gave_up" not in rep2
# 5c. 番号の欄に ² や ① を入れても落ちない（受け付けずに知らせる）。ID の形でない物は review で扱わない
with tempfile.TemporaryDirectory() as d:
    rid, msgs = intake.submit({**GOOD, "p0_step": ["²"], "stuck_step": ["①"]}, pathlib.Path(d))
    assert rid is None and msgs, msgs
    victim = pathlib.Path(d) / "victim.json"
    victim.write_text("{}", encoding="utf-8")
    assert intake.reject("../victim", pathlib.Path(d))[0] is False and victim.exists()
    assert intake.accept("../victim", pathlib.Path(d), confirm="../victim")[0] is False
# 5d. 画面の送り先は、手元の Host・同じ Origin・画面に埋めた合言葉（token）が揃わないと受け付けない。Content-Length の異常も断る
import http.client, threading
from http.server import HTTPServer
with tempfile.TemporaryDirectory() as d:
    intake.Handler.base = pathlib.Path(d)
    srv = intake.make_server(0)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    def post(body, headers):
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        c.request("POST", "/report", body=body, headers=headers)
        r = c.getresponse(); r.read(); c.close()
        return r.status
    from urllib.parse import urlencode
    good = urlencode({k: v[0] for k, v in GOOD.items()} | {"token": intake.Handler.token})
    host = {"Host": f"127.0.0.1:{port}", "Content-Type": "application/x-www-form-urlencoded"}
    assert post(good, host) == 200
    assert post(good, {**host, "Host": "evil.example"}) == 403
    assert post(good, {**host, "Origin": "https://evil.example"}) == 403
    assert post(urlencode({k: v[0] for k, v in GOOD.items()} | {"token": "x"}), host) == 403
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    c.putrequest("POST", "/report", skip_host=True); c.putheader("Host", f"127.0.0.1:{port}"); c.putheader("Content-Length", "-1"); c.endheaders()
    assert c.getresponse().status == 400
    c.close()
    srv.shutdown()
    assert srv.server_address[0] == "127.0.0.1"
# 6. 画面は、全部の雛形を選べ、写真の欄が無く、同意の 2 つを持つ
page = intake.form_page()
from omochae.compose import TEMPLATES
assert all(f'value="{t}"' in page for t in TEMPLATES) and 'type="file"' not in page
assert all(f'name="{k}"' in page for k in intake.CONSENTS)
assert all(f'name="{k}"' in page for k in ("stuck_step", "gave_up", "minutes")) and 'value="guide"' in page
# 7. 置き場は git の外（local/ を .gitignore が持つ）
assert "local/" in (ROOT / ".gitignore").read_text(encoding="utf-8").split()
print("ok")
