# 凍結した合格の基準（床の一覧）

utsushi（このエンジンを切り出した元の repo）で凍結した基準のうち、エンジンに入る床だけを写した。
床の名前と期待は元と同じにしてある（元の repo の場面とこの repo の場面を、同じ物差しで読めるようにするため）。
一度 commit したら変えない。変える時は理由を commit に残す。
exit code: 0 = 通る / 3 = 落ちる（検査の名前を出す）/ 4 = 検査できない。
入口は `run.sh`。結果は `out/RESULT.md`。

| ID | 見る事 | 負の対照（場面） | 期待 |
|---|---|---|---|
| F1.marks | 型紙の PDF から pdftotext で、所蔵（国立国会図書館デジタルコレクションと永続 ID）・改変・出典 ID・「仮説」が取り出せる | `neg_marks_all`・`neg_marks_source_id` | 3・F1.marks |
| F1.source | 刷る形ごとに出典が違う雛形（SOURCES を持つ雛形）で、形と合わない出典を渡すと落とす。既定の出典も形から選ぶ | `tests/test_guards.py` の 10・`spinner_neg_source`・`whistle_neg_source`・`popup_jar_neg_source`・`slide_box_neg_source`・`wheel_cart_neg_source`・`balance_neg_source`・`twist_drum_neg_source` | 3・F1.source |
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
| F5.spin | 回る玩具（spinner）。風車は、羽と柄の間・穴の隙間・穴の余白・柄の長さ・刷る菱形どうしの距離 2mm 以上・腕の長さを見る。独楽（平ら・円錐）は、眠る独楽の下限の回る速さが、指で回す見込みの半分以下。円盤の重心が穴の中心から 0.5mm まで。下の軸が 8° 傾くまで縁が床に付かない。車屏風は、車と前の面の間・車の大きさ・屏風が車の重さで前へ倒れない事 | `spinner_neg`〜`spinner_neg9` | 3・F5.spin |
| F5.sound | 鳴る玩具（whistle）。紙の舌は片持ちの梁の式で 150〜3000Hz・自由長が幅の 1.5 倍以上・根元を 2mm 以上挟む。ラッパの半頂角は 8〜45°。閉じた管は c/4(L+0.3d) で 200〜4000Hz・長さが径の 4 倍以上・歌口の切り欠きの比。鈴は、玉が中で転がる大きさか | `whistle_neg`〜`whistle_neg5` | 3・F5.sound |
| F5.popup | 押し上げの壺（popup_jar）。静かな時に人形が口の高さ − 2 の下に隠れ、押し切った時に体の下の端が口に届く。穴の遊びの傾きで、袖の先が壺の内の壁に当たらない。足が糊代に乗らない。帯が穴で引っかからない（引き出しの決まり） | `popup_jar_neg`・`neg2`・`neg4` | 3・F5.popup |
| F5.jar_seat | 壺の足の差し渡しが箱の一辺 − 1 に収まり、帯の穴が糊代に塞がれない | `popup_jar_neg3` | 3・F5.jar_seat |
| F5.slide | 滑る箱（slide_box）。滑る道の隙間が 0.4〜2.0mm。行程が鼠を出しきり、箱の長さの半分まで。止めが仕切りに 1.5mm 以上掛かる。止めが角の糊代に擦れない。外箱の継ぎ目の糊代が底に収まる | `slide_box_neg`〜`neg4` | 3・F5.slide |
| F5.wheel | 車の玩具（wheel_cart）。車輪の半径が軸の高さ＋2mm 以上、車輪と胴・蓋・二股のすき間 1.5mm、軸の穴の余白 4mm、鼠車の重心が前後の接地点の間 | `wheel_cart_neg`・`neg_tip`・`neg_stick`・`neg_mallet` | 3・F5.wheel |
| F5.balance | 釣り合いの玩具（balance）。弥次郎兵衛は、重心が V の先より 10mm 以上下、左右で粘土が 0.3g 違っても 10° まで、左右の玉がそれぞれ台の竹串に当たるまで 20° 以上振れ、振れた時の一番低い所で机に当たらない、竹串が体の中に収まり交わらない、支点の紙の厚み 1.0mm 以上。起き上がり小法師は、重心が底の半球の曲がりの中心より半径の 1/4 以上下、粘土が底から半径の半分まで、円錐を開いた形が半円を超えない | `balance_neg`〜`neg3` | 3・F5.balance |
| F5.drum | 振り鼓（twist_drum）。糸の長さ（結び目から玉の中心）が窓に入る: 下限は打つ点が面の中心から半径の半分の内（玉の半径も入れる）、上限は面を越えず柄に絡まない（L ＋ 玉の半径 < √2·R − 柄の半径。本当の距離の下限）。柄の穴と帯の縁は 3mm 以上、糊代の歯の先は 1mm 以上、竹串 180mm に収まる。諫鼓は、糸 ＞ 玉の半径 ＋ 1.5、花車が面に当たらない、棒を引ける長さで軸が 1 回以上回る、引く棒が竹串 180mm に収まる | `twist_drum_neg`〜`neg3`・`twist_drum_neg_kanko`〜`kanko4` | 3・F5.drum |

`neg_fan_leg` の期待に F5.image_box を足した（2026-11-04・元の repo の v9 を写した時）。v9 で扇の板に色を塗るようになり、足の糊代が扇の本体に食い込む寸法では、糊代と糊代の折り線が本当に扇の絵にかかる。偽の失敗ではないので、2 つとも期待にした（F5.fan_leg が落ちる事は変わらない）。

### この repo で広げた床（名前と期待は変えず、見る物を足した）

- **F1.marks**: 所蔵の頭の語・「改変」「仮説」の短い語だけでなく、出典の記録の所蔵の文（holding）と改変の注記（modification_note）、仮説の文を、空白を除いてそのまま探す。短い語だけだと、本文が欠けても化けても通った。試験は `tests/test_guards.py` の 4
- **F2.bom**: 型紙に刷る部品の番号が全部、部品表にある。虎の首の形の部品 5（重りの腕）が部品表に無いまま通った。試験は `tests/test_guards.py` の 3
- **F5.image_box**: 線の絵が糊代を横切るのも落とす（交わりの面積でなく長さで見る）。試験は `tests/test_guards.py` の 2

## 元の repo にあって、ここに無い床

F3（結果の値）・F4（根拠の記録）・F6（図鑑の文の印）・F7（版の更新）・F8（前例の参照）・F9（人の確認・予想）・F10（持ち寄り）・F11（見比べ）は、
試した記録や学びの輪を扱う床で、型紙を作るエンジンの外なので写していない。
