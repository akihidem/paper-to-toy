"""tests/frozen の場面を全部回し、out/RESULT.md に表を出す。

なぜ狙いの検査の名前まで比べるか: exit 3 だけ見ると、別の理由で落ちた負の対照も成功に見えてしまう。
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY = str(ROOT / ".venv/bin/python")
NOT_YET = []


def load_scenarios():
    """場面を全部読み、(場面と期待の組, 読めない物の文) を返す。壊れた物があれば 1 つも回さない（結果の表を半端に残さない）。"""
    found, wrong = [], []
    for sc in sorted((ROOT / "tests/frozen/scenarios").glob("*.json")):
        try:
            expect = json.loads(sc.read_text(encoding="utf-8"))["expect"]
            found.append((sc, {"rc": expect["rc"], "floors": sorted(expect["floors"])}))
        except (OSError, ValueError, KeyError, TypeError) as e:
            wrong.append(f"{sc.relative_to(ROOT)}（{type(e).__name__}: {e}）")
    return found, wrong


def child_env(environ):
    """子へ渡す環境。試験は素の assert で検査するので、assert を消す設定（PYTHONOPTIMIZE）を渡さない。
    呼ぶ側の環境に残っていると、落ちるはずの試験が黙って通る（#36）。子は -O も付けずに起こす。"""
    return {**{k: v for k, v in environ.items() if k != "PYTHONOPTIMIZE"}, "PYTHONPATH": str(ROOT / "src")}


def _rel(path):
    return pathlib.Path(path).relative_to(ROOT).as_posix()


def scenario_command(sc):
    """結果の表に書く命令。repo の頭でそのまま打てる形にする（落ちた行を手で回し直すため）。"""
    return f"PYTHONPATH=src .venv/bin/python -m omochae --scenario {_rel(sc)} --out out/scenarios/{sc.stem}"


def test_command(test):
    return f"PYTHONPATH=src .venv/bin/python {_rel(test)}"


def result_lines(rows, scenario_count):
    """結果の表の行。合計の行は今までの形のまま残し、場面と試験の内訳を別の行に足す。"""
    lines = ["# 床の実行結果", "", "| 段 | 命令 | rc | 期待 | 落ちた検査 | 期待の検査 | 判定 |", "|---|---|---|---|---|---|---|"]
    lines += [f"| {n} | `{cmd}` | {rc} | {erc} | {g} | {e} | {v} |" for n, cmd, rc, erc, g, e, v in rows]
    lines += [f"| {f} | — | — | — | — | — | 未実装 |" for f in NOT_YET]
    good = [r[-1] == "OK" for r in rows]
    lines += ["", f"実行した場面 {len(rows)} 本、期待どおり {sum(good)} 本、未実装の床 {len(NOT_YET)} 本。",
              f"内訳: 凍結の場面 {scenario_count} 本（期待どおり {sum(good[:scenario_count])} 本）、"
              f"試験 {len(rows) - scenario_count} 本（期待どおり {sum(good[scenario_count:])} 本）。"]
    return lines


def main():
    for tool in ("pdftotext", "pdftoppm", "pdfimages", "fc-match"):
        if not shutil.which(tool):
            print(f"検査できない: {tool} が無い", file=sys.stderr)
            return 4
    scenarios, wrong = load_scenarios()
    if wrong:
        for line in wrong:
            print(f"検査できない: 場面が読めない … {line}", file=sys.stderr)
        return 4
    env = child_env(os.environ)
    rows, bad, broken = [], 0, 0
    for sc, expect in scenarios:
        out = ROOT / "out/scenarios" / sc.stem
        cmd = [PY, "-m", "omochae", "--scenario", str(sc), "--out", str(out)]
        r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
        got = sorted(set(re.findall(r"^FAIL (\S+)", r.stderr, re.M)))
        ok = r.returncode == expect["rc"] and got == sorted(expect["floors"])
        broken += r.returncode == 4
        bad += not ok
        rows.append((sc.stem, scenario_command(sc), r.returncode, expect["rc"], ",".join(got) or "—", ",".join(expect["floors"]) or "—", "OK" if ok else "NG"))
        if not ok:
            print(f"NG {sc.stem}: rc={r.returncode} {r.stderr.strip()[:500]}", file=sys.stderr)
    for test in sorted((ROOT / "tests").glob("test_*.py")):
        unit = subprocess.run([PY, str(test)], cwd=ROOT, env=env, capture_output=True, text=True)
        bad += unit.returncode != 0
        rows.append((test.stem, test_command(test), unit.returncode, 0, "—", "—", "OK" if unit.returncode == 0 else "NG"))
        if unit.returncode:
            print(f"NG {test.stem}: {unit.stderr.strip()[:500]}", file=sys.stderr)
    lines = result_lines(rows, len(scenarios))
    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "out/RESULT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[-2:]))
    return 4 if broken and bad == broken else (3 if bad else 0)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # 思わぬ失敗は「通った」にも「落ちた」にも数えない（.venv が無い・結果の表が書けない など）。
        print(f"検査できない: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(4)
