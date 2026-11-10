"""外の命令を時間切れつきで呼ぶ所と、回ごとの一時の置き場（#29）。

なぜ 1 か所か: poppler や fontconfig が返らないと、命令も関門も止めるまで固まる。呼ぶ所ごとに書くと、足した所で付け忘れる。
切れた時は ToolMissing（exit 4・検査できない）にする。紙を見ていないので、落ちた（3）とは言わない。
"""
import math
import os
import pathlib
import re
import shutil
import subprocess
import tempfile

from .model import ToolMissing

DEFAULT_TIMEOUT = 120.0  # 秒。ふだんは 1 秒もかからない。ほかの作業で混んだ機械でも、正常な命令を切らない長さにする
MARK = ".omochae-work-dir"  # work_dir が自分の置き場の中に置く印の名（_sweep が、自分の作った物だけを消すため）


def tool_timeout():
    raw = os.environ.get("OMOCHAE_TOOL_TIMEOUT")
    if raw is None:
        return DEFAULT_TIMEOUT
    try:
        value = float(raw)
    except ValueError:
        value = math.nan
    if not (value > 0 and math.isfinite(value)):  # 読めない値を、黙って時間切れ無しにしない
        raise ToolMissing(f"OMOCHAE_TOOL_TIMEOUT の値が読めない: {raw[:40]!r}")
    return value


def run_tool(cmd, fail, **kwargs):
    """外の命令を呼ぶ。無い・落ちた時は「fail: 理由」、返らない時は命令の名前と秒数を言って ToolMissing。"""
    limit = tool_timeout()
    try:
        return subprocess.run(cmd, capture_output=True, check=True, timeout=limit, **kwargs)
    except subprocess.TimeoutExpired:
        raise ToolMissing(f"{cmd[0]} が {limit:g} 秒で返らない")
    except (OSError, subprocess.CalledProcessError) as e:
        raise ToolMissing(f"{fail}: {e}")


def _alive(pid):
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, OverflowError):
        return False
    except PermissionError:
        return True
    return True


def _sweep(parent, prefix):
    """止められた回の置き場を片づける。後始末の finally は、外から止められた時は走らないので、次の回が見る。

    同じ所へ別の回が同時に書く事があるので、動いている回の物は消さない。名前に主の pid を入れて、生きているかで見る。
    消すのは、work_dir が作った置き場と確かに分かる物だけ（セキュリティの点検 2026-11-07）: 名が work_dir の作る形（頭の字・pid・-・
    mkdtemp の 8 字）で、中に work_dir の置く印（MARK）が普通のファイルとして在る物。--out の親の所は人の置き場でもあり、
    頭の字と名の形と時刻だけで見ると、人の付けた名（.omochae-20261107・.omochae-backup01・.omochae-20261107-snapshot など）が当たって消えた。
    印の無い物は、名の形が合っても消さない（印を置く前に止められた回と、印を置く前の版が残した物は片づかないが、人の物を消さない側に倒す）。
    pid の無い前の形（11-04〜11-05 の版だけが作った）も同じ理由で、もう片づけない。
    """
    ours = re.compile(rf"{re.escape(prefix)}([0-9]+)-[a-z0-9_]{{8}}")
    for path in parent.glob(f"{prefix}*"):
        owner = ours.fullmatch(path.name)
        mark = path / MARK
        try:
            if not owner or path.is_symlink() or not path.is_dir() or mark.is_symlink() or not mark.is_file():
                continue
            stale = not _alive(int(owner.group(1)))
        except OSError:
            continue
        if stale:
            shutil.rmtree(path, ignore_errors=True)


def work_dir(parent, prefix):
    """この回だけの一時の置き場を parent の中に作る。消すのは呼ぶ側（finally）。
    作ってすぐ中に印（MARK）を置く。止められた回の置き場を次の回が片づける時（_sweep）、印で自分の作った物と見分けるため。"""
    parent = pathlib.Path(parent)
    _sweep(parent, prefix)
    path = pathlib.Path(tempfile.mkdtemp(prefix=f"{prefix}{os.getpid()}-", dir=parent))
    (path / MARK).write_bytes(b"")
    return path
