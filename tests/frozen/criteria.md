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
| F5.fan_height | 畳んだ扇の高さ ≦ 静止時の筒の空き（高さ − 押し上げる量） | `neg_fan_height` | 3・F5.fan_height |
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

## F5.stroke の由来

寸法の行程の計算で見つかった不足（押す部品が筒より短いと、指が筒の外にある間に押し切れない）を、検査にした物。

## 正の場面

`pos_tab`・`pos_tube`・`pos_stick`・`pos_rim`・`pos_long_title`（長い見出しでも部品が下へ送られて通る）・`pos_tiger_hang`・`pos_tiger_neck` は exit 0。

## 元の repo にあって、ここに無い床

F3（結果の値）・F4（根拠の記録）・F6（図鑑の文の印）・F7（版の更新）・F8（前例の参照）・F9（人の確認・予想）・F10（持ち寄り）・F11（見比べ）は、
試した記録や学びの輪を扱う床で、型紙を作るエンジンの外なので写していない。
