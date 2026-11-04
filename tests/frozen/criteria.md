# 凍結した合格の基準（床の一覧）

utsushi（このエンジンを切り出した元の repo）で凍結した基準のうち、エンジンに入る床だけを写した。
床の名前と期待は元と同じにしてある（元の repo の場面とこの repo の場面を、同じ物差しで読めるようにするため）。
一度 commit したら変えない。変える時は理由を commit に残す。
exit code: 0 = 通る / 3 = 落ちる（検査の名前を出す）/ 4 = 検査できない。
入口は `run.sh`。結果は `out/RESULT.md`。

| ID | 見る事 | 負の対照（場面） | 期待 |
|---|---|---|---|
| F1.marks | 型紙の PDF から pdftotext で、所蔵（国立国会図書館デジタルコレクションと永続 ID）・改変・出典 ID・「仮説」が取り出せる | `neg_marks_all`・`neg_marks_source_id` | 3・F1.marks |
| F2.bom | 部品表の素材が空でない。置き換えには元の素材（推定）と理由がある | `neg_bom_material`・`neg_bom_original` | 3・F2.bom |
| F5.range | 寸法が雛形の範囲の中で、知らない名前が無い | `neg_range` | 3・F5.range |
| F5.print_area | 全部品と全文字が印字域に収まる | `neg_print_area` | 3・F5.print_area |
| F5.overlap | 部品どうしが重ならない | `neg_overlap` | 3・F5.overlap |
| F5.text_overlap | 文字どうしが重ならず、文字が部品の枠をまたがない。幅はフォントから測る | `neg_text_overlap` | 3・F5.text_overlap |
| F5.fan_length | 折り数 × 折り幅 ＝ 扇の長さ | `neg_fan_length` | 3・F5.fan_length |
| F5.fan_height | 畳んだ扇の高さ（軸の形は中心の高さ＋扇の高さ）≦ 押し上げる量（静かな時の台から口まで）。口の台の形も軸の形と同じ見方 | `neg_fan_height`・`neg_fan_height_rim` | 3・F5.fan_height |
| F5.fan_thickness | 畳んだ扇の厚さ ≦ 内筒の一辺 − 2 | `neg_fan_thickness` | 3・F5.fan_thickness |
| F5.slide_clearance | 内筒の一辺 < 外筒の一辺 − 1（等号は落とす） | `neg_slide_clearance` | 3・F5.slide_clearance |
| F5.figure_height | 像の高さ ≦ 折りの高さ ＋ 6 | `neg_figure_height` | 3・F5.figure_height |
| F5.base_size | 扇の台 ≦ 内筒の一辺 | `neg_base_size` | 3・F5.base_size |
| F5.stroke | 下から押す形は 押す部品の長さ ≧ 筒の高さ。つまみの形は 内筒が筒に収まり、溝が筒の端から 5mm 以上離れる | `neg_stroke_tube`・`neg_stroke_tab` | 3・F5.stroke |
| F5.pivot | 虎の雛形の族の床。重心が軸より下、静かな時の傾きが 15° まで、穴の余白、揺れの余裕、重りと頭が底に当たらない | `neg_pivot_weight_above`・`neg_pivot_tilt`・`neg_pivot_ear`・`neg_pivot_floor` | 3・F5.pivot |
| F5.fan_clearance | 帯の長さの開く上限が、筒の口の角に当たらない角度に収まる | `neg_fan_clearance` | 3・F5.fan_clearance |
| F5.image_box | 描き直しの絵が部品の中にあり、折り線と糊代をまたがない | `neg_image_box` | 3・F5.image_box |
| F5.image_count | PDF に貼られた画像が 0 枚（原図を貼らない） | `neg_image_count` | 3・F5.image_count |

F5.fan_height は、軸の形では「中心の高さ＋折りの高さ ≦ 押し上げる量」で見る。

### F5.fan_height を直した（2026-11-04・本人の決定）

元の文は「畳んだ扇の高さ ≦ 静止時の筒の空き（高さ − 押し上げる量）」で、口の台の形はこの通りに見ていた。ところが静かな時の台から口までは押し上げる量で、高さ − 押し上げる量は台の下の空き（内筒が入る所）だった。そのため、扇が口から出る寸法が通っていた（元の `pos_rim` は扇の高さ 48・押し上げる量 36 で、静かな時に扇の上 12mm が口から出る）。全体のレビューの指摘で、本人の決定で、口の台の形も軸の形と同じく押し上げる量と比べる形に直した。
- `pos_rim` は扇が隠れる寸法（扇の高さ 36・折り数 14）に替えた。元の寸法は負の場面 `neg_fan_height_rim` にした
- `neg_fan_clearance` は口の台の形で、元の寸法（扇の高さ 48）だと F5.fan_height でも落ち、狙いの F5.fan_clearance だけで落ちる場面でなくなるので、扇の高さを 36 にした（F5.fan_clearance だけで落ちる事は変わらない）

## F5.stroke の由来

寸法の行程の計算で見つかった不足（押す部品が筒より短いと、指が筒の外にある間に押し切れない）を、検査にした物。

## 正の場面

`pos_tab`・`pos_tube`・`pos_stick`・`pos_rim`・`pos_long_title`（長い見出しでも部品が下へ送られて通る）・`pos_tiger_hang`・`pos_tiger_neck` は exit 0。

## v8 で変えた所（元の repo の 2026-11-04 の変更を写した）

- **F5.stroke（つまみの形）**: 溝を筒の下の端まで開いた切り込みにした（くり抜かない）ので、溝の端の 5mm は口の側だけを見る。下の端は開いているので見ない。柄の形には土台（短い内筒）を足し、土台の高さが静止時の筒の空きに収まる事を見る。負の対照 `neg_stroke_tab` の場面と期待は変えていない（内筒が筒に収まらない形で落ちる）
- **F5.image_count**: 型紙は今も 0 枚（元の repo では手順の紙だけに例外があるが、手順の紙はこの repo に無い）
- 試験は `tests/test_sheet_v8.py`

## この repo で足した床

既存の床は変えず、足しただけ。

| ID | 見る事 | 負の対照（場面） | 期待 |
|---|---|---|---|
| F5.fan_leg | 軸の形で、扇の足の長さ（中心の高さ − 2 ＋ 糊代）が糊代より短くない。短いと糊代が扇の本体に食い込み、糊代の折り線が要の穴の列を横切る（中心の高さ 2 未満）。v8 の足を写した後、レビューで見つかった | `neg_fan_leg` | 3・F5.fan_leg・F5.image_box（v9 から。下の注） |
| F5.hole | 穴（軸・糸・串）の円が部品の輪郭の中にある。雛形の式が寸法から穴を置くので、扇が低い・像が小さいと穴が紙の外に出た。全体のレビューで見つかった | `neg_hole` | 3・F5.hole |
| F5.figure_base | 像の足の糊代（像の幅の 0.3〜0.7）が扇の台の一辺より広くない。広いと台に貼れない。全体のレビューで見つかった | `neg_figure_base` | 3・F5.figure_base |

`neg_fan_leg` の期待に F5.image_box を足した（2026-11-04・元の repo の v9 を写した時）。v9 で扇の板に色を塗るようになり、足の糊代が扇の本体に食い込む寸法では、糊代と糊代の折り線が本当に扇の絵にかかる。偽の失敗ではないので、2 つとも期待にした（F5.fan_leg が落ちる事は変わらない）。

### この repo で広げた床（名前と期待は変えず、見る物を足した）

- **F1.marks**: 所蔵の頭の語・「改変」「仮説」の短い語だけでなく、出典の記録の所蔵の文（holding）と改変の注記（modification_note）、仮説の文を、空白を除いてそのまま探す。短い語だけだと、本文が欠けても化けても通った。試験は `tests/test_guards.py` の 4
- **F2.bom**: 型紙に刷る部品の番号が全部、部品表にある。虎の首の形の部品 5（重りの腕）が部品表に無いまま通った。試験は `tests/test_guards.py` の 3
- **F5.image_box**: 線の絵が糊代を横切るのも落とす（交わりの面積でなく長さで見る）。試験は `tests/test_guards.py` の 2

## 元の repo にあって、ここに無い床

F3（結果の値）・F4（根拠の記録）・F6（図鑑の文の印）・F7（版の更新）・F8（前例の参照）・F9（人の確認・予想）・F10（持ち寄り）・F11（見比べ）は、
試した記録や学びの輪を扱う床で、型紙を作るエンジンの外なので写していない。
