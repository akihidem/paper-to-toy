# paperto3d — 紙で試すための型紙（papercraft）のエンジン

型紙（papercraft）を作るエンジン。江戸の玩具を紙で試すために、寸法から型紙の PDF を作り、刷れる・組めるかを機械で検査する。**Built with Claude: Japan 2026（ハッカソン）で作っている。**

A papercraft template engine: generates printable PDF patterns from dimensions and checks them before and after rendering. Being built at Built with Claude: Japan 2026 (hackathon).

## 提出物との関係

このエンジンは [utsushi](https://github.com/akihidem/utsushi)（ハッカソンの提出物）の一部を、開発期間中（2026-11-02 12:00 JST 以降）に切り出した物です。コードはすべて期間中に utsushi の repo で新しく作りました。提出物は utsushi で、このエンジンは単独の提出物ではありません。元の commit: utsushi `1d17988`（その後の v8 の直しは utsushi `74c354c` から写した）。

## 何をするか

```
寸法（JSON） → 配置 → 描く前の検査 → SVG / PDF → 刷った後の検査 → PNG
```

- **描く前の検査**: 寸法の範囲、部品と文字が印字域に収まるか、部品どうし・文字どうしの重なり（文字の幅はフォントから測る）、部品表の素材、描き直しの絵が折り線と糊代をまたがないか、雛形ごとの物理（扇が筒に収まるか・押し切れるか・重心が軸より下か など）。
- **刷った後の検査**: できた PDF から pdftotext で、所蔵・永続 ID・改変の注記・出典 ID・「仮説」の印が読み直せるか。貼られた画像が 0 枚か（原図を貼らず描き直す）。
- 検査に落ちた紙は正しい名前で残さない（`*.rejected.pdf` にする）。

雛形は 2 つ。

| 雛形 | 玩具 | 仕組み |
|---|---|---|
| `slider_fan` | 御来迎 | 角筒の中で動く台に蛇腹の扇と像を載せ、押し上げると開く。押し方（つまみ・内筒・棒）と扇の中心の置き方（軸・台）を描き分ける |
| `pivot_counterweight` | 張子の首振り虎 | 箱の胴に軸を通し、重りで頭を揺らす。頭の支え方（吊る・首）を描き分ける |

どの寸法も計算と検査で出した値です。検査は「刷れる・形の上で組める」事を見る物で、紙で動く事の保証や、昔の作り方の証明ではありません。

## 使い方

Python のパッケージ名は `omochae`（元の repo と同じ名前のまま）。

要る物: [uv](https://docs.astral.sh/uv/)、poppler-utils（`pdftotext`・`pdfimages`・`pdftoppm`）、fontconfig（`fc-match`）、字 Noto Serif CJK JP。

```bash
./init.sh     # .venv を作り、依存を入れる。足りない物があれば名指しして exit 4
./run.sh      # 凍結した場面と試験を全部回す。結果は out/RESULT.md
```

最小の例（型紙を 1 枚刷る）:

```bash
PYTHONPATH=src .venv/bin/python -m omochae --scenario examples/fan_tab.json --out out/fan_tab
# → out/fan_tab.svg / .pdf / .png
```

`examples/fan_tab.json`:

```json
{
  "template": "slider_fan",
  "source_id": "NDL-1187053-R0000005-L",
  "params": {"push_part": "tab"},
  "inject": {}
}
```

`params` に書かなかった寸法は雛形の既定値（`DEFAULTS`）を使う。変えてよい名前と範囲は雛形の `RANGES`。`source_id` は `data/sources/` の出典の記録の名前で、型紙に刷る所蔵と改変の印をここから取る。

描かずに検査だけを回す時は Python から:

```python
from omochae.compose import check_params
import json
source = json.load(open("data/sources/NDL-1187053-R0000005-L.json", encoding="utf-8"))
print(check_params("slider_fan", {"push_part": "tab", "fold_count": 40}, source))
# {'passed': False, 'errors': ['FAIL F5.fan_clearance [蛇腹の扇] 帯の長さでは 406° 開くが、筒の口の角に当たって 289° までしか開けない',
#                              'FAIL F5.print_area [蛇腹の扇] 印字域の外に出ている (152.0, 36.2, 200.0, 376.2)']}
```

## 終了の番号

| exit | 意味 |
|---|---|
| 0 | 通る |
| 3 | 落ちる（どの検査が・どこで、を `FAIL <床> [<場所>] <理由>` で出す） |
| 4 | 検査できない（道具や字が無い・想定外の故障） |

1 と 2 は使わない。検査の結果と道具の故障を読み分けるため。床の一覧は [tests/frozen/criteria.md](tests/frozen/criteria.md)。

## 置き場

- `src/omochae/` エンジン（`compose.py` 配置と検査の流れ・`floors.py` 描く前の検査・`marks.py` 印と刷った後の検査・`render.py` 描画・`textfit.py` 文字の幅・`fan_model.py` / `pivot_model.py` 扇と振り子の式・`metrics.py` 寸法から出る値）
- `src/omochae/templates/` 雛形
- `data/sources/` 出典の記録（国立国会図書館の書誌の値）
- `tests/frozen/` 凍結した場面と合格の基準 / `tests/test_*.py` 式の試験
- `examples/` 最小の例

## ライセンスと出典

- コード: [MIT](LICENSE)
- 出典: 『江都二色』（国立国会図書館デジタルコレクション info:ndljp/pid/1187053、米山堂・1931 年の複製）。PDM。型紙は図を参照して寸法と形を起こし、色と線を描き直した翻案で、原図は入れていない。
- 依存（同梱しない）: CairoSVG（LGPL-3.0-or-later）・Shapely（BSD-3-Clause）・drawsvg（MIT）・fontTools（MIT）・Pillow（MIT-CMU）。外の命令の poppler-utils（GPL）は呼ぶだけ。字 Noto Serif CJK JP（SIL OFL 1.1）は手元に入っている物を使う。
