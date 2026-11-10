"""init.sh が言う Python の版が、README と固定した依存に合い、足りない時に rc 4 で名指しする事を見る。

なぜ本物の Python でなく偽の uv と .venv で回すか: 古い Python を試験の機械に置けないので、版の比べ方と止まる所だけを見る。
"""
import importlib.metadata
import os
import pathlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
INIT = (ROOT / "init.sh").read_text(encoding="utf-8")
MIN_PY = re.search(r'^MIN_PY=(\d+\.\d+)$', INIT, re.M).group(1)


def ver(text):
    return tuple(int(x) for x in text.split("."))


# README と init.sh の言う版が同じ
said = re.findall(r"Python (\d+\.\d+) 以上", (ROOT / "README.md").read_text(encoding="utf-8"))
assert said == [MIN_PY], f"README の版 {said} と init.sh の版 {MIN_PY} が違う"

# 固定した依存の求める版を、init.sh の版が満たす（依存を上げて版がずれたら、ここで落ちる）
# Python の版の印（; python_version >= "3.12" か < "3.12"）の付いた行は、その版の Python にだけ入る（numpy は Python の版ごとに 2 つ
# 固定する。2 つが揃う事は tests/test_requirements_pin.py が見る）。読むのは入っている物の版の決まりなので、今の Python に入らない行は
# 見られない（3.11 で回すと < の行を見る）。>= の行は印の版から上で入るので、下限の代わりに印の版と比べる
pins = re.findall(r"^([\w-]+)==[^;\n]*(?:;(.*))?$", (ROOT / "requirements.txt").read_text(encoding="utf-8"), re.M)
assert pins, "requirements.txt に固定した依存が無い"
for name, marker in pins:
    lowest = MIN_PY
    if marker:
        m = re.fullmatch(r'\s*python_version\s*(>=|<)\s*"(\d+\.\d+)"\s*', marker)
        assert m, f"{name} の印 {marker!r} が読めない（python_version の >= か < だけを使う）"
        if (sys.version_info[:2] >= ver(m.group(2))) != (m.group(1) == ">="):
            continue
        lowest = max(MIN_PY, m.group(2), key=ver) if m.group(1) == ">=" else MIN_PY
    needs = importlib.metadata.metadata(name).get("Requires-Python") or ""
    floor = re.search(r">=\s*(\d+\.\d+)", needs)
    assert not floor or ver(floor.group(1)) <= ver(lowest), f"{name} は {needs} を求めるが、" + (f"この行は Python {lowest} から" if lowest != MIN_PY else f"init.sh は {MIN_PY}")


def stub(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/bash\n" + body + "\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def run_init(venv_python=None, uv_venv_rc=0, new_python="3.12"):
    """偽の道具の置き場で init.sh を回し、(rc, stderr, uv が受けた引数の行) を返す。"""
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        shutil.copy(ROOT / "init.sh", d / "init.sh")
        (d / "requirements.txt").write_text("", encoding="utf-8")
        for tool in ("pdftotext", "pdftoppm", "pdfimages", "fc-match"):
            stub(d / "bin" / tool, "exit 0")
        stub(d / "bin/fc-list", 'echo "Noto Serif CJK JP"')
        fake_python = 'echo "{}"'
        stub(d / "bin/uv", f"""echo "$*" >> "{d}/uv.log"
if [ "$1" = venv ]; then
  [ {uv_venv_rc} -eq 0 ] || exit {uv_venv_rc}
  mkdir -p .venv/bin; printf '#!/bin/bash\\n{fake_python.format(new_python)}\\n' > .venv/bin/python; chmod +x .venv/bin/python
fi""")
        if venv_python:
            stub(d / ".venv/bin/python", fake_python.format(venv_python))
        env = {**os.environ, "PATH": f"{d}/bin:/usr/bin:/bin"}
        r = subprocess.run(["bash", str(d / "init.sh")], cwd=d, env=env, capture_output=True, text=True)
        log = d / "uv.log"
        return r.returncode, r.stderr, log.read_text(encoding="utf-8") if log.exists() else ""


# 版の合う Python が無い: uv が venv を作れず、rc 4 で版を名指しし、依存を入れに進まない
rc, err, uv = run_init(uv_venv_rc=2)
assert rc == 4, rc
assert f"Python {MIN_PY} 以上" in err, err
assert "pip install" not in uv, uv

# 版の合う Python がある: 版の範囲を渡し、黙って Python を落とさない形で作り、依存を入れる
rc, err, uv = run_init()
assert rc == 0, (rc, err)
assert f">={MIN_PY}" in uv and "--no-python-downloads" in uv, uv
assert "pip install" in uv, uv

# 前からある .venv の版を見る（3.9 と 3.11 を字の順で比べると逆になる）
major, minor = ver(MIN_PY)
for old in (f"{major}.{minor - 1}", "3.9"):
    rc, err, uv = run_init(venv_python=old)
    assert rc == 4, (old, rc)
    assert f"Python {MIN_PY} 以上" in err and old in err, err
    assert "pip install" not in uv, uv
for good in (MIN_PY, f"{major}.{minor + 3}"):
    rc, err, uv = run_init(venv_python=good)
    assert rc == 0, (good, rc, err)
    assert not uv.startswith("venv"), uv  # 前からある .venv を作り直さない
