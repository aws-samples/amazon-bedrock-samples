All of the information below has been generated from the results of tests performed on the [Fishtest] framework.

Current Testing Criteria

* `1 Thread` 60 seconds + 0.6 seconds for 60,000 games `(2019-11-21 - current)`
* `8 Threads` 60 seconds + 0.6 seconds for 60,000 games `(2023-06-29 - current)`
* [UHO_4060_v3.epd][book-uho4060v3] opening book `(2023-09-10 - current)`

<details>
  <summary>Previous Testing Criteria</summary><br>

* `1 Thread` 60 seconds + 0.6 seconds for 40,000 games `(2016-01-02 - 2019-11-21)`
* `1 Thread` 60 seconds + 0.5 seconds for 40,000 games `(2013-10-13 - 2016-01-02)`
* `1 Thread` 60 seconds + 0.5 seconds for 20,000 games `(2013-03-04 - 2013-10-13)`
* `8 Threads` 30 seconds + 0.3 seconds for 40,000 games `(2018-12-13 - 2023-06-29)`
* 8moves_GM.pgn opening book `(2013-04-10 - 2013-11-01)`
* varied.bin opening book `(2013-03-04 - 2013-04-07)`
* [8moves_v3.pgn][book-8mv3] opening book `(2013-11-09 - 2023-06-29)`
* [UHO_XXL_+0.90_+1.19.epd][book-uho21epd] opening book `(2022-04-17 - 2023-06-29)`
* [UHO_4060_v2.epd][book-uho4060v2] opening book `(2023-06-29 - 2023-09-10)`

</details>

---

## Current Development

<div align="center">

[![][graph-current]][graph-current]

| `Date` | `Version` | `1 Thread` | `8 Threads` |
|:---:|:---:|:---:|:---:|
| 2023&#8209;07&#8209;19 | [master][190723-master] vs [Stockfish 16]<br><sub>`Bench: 1727577`<br>Do more futility pruning for cutNodes that are not in TT<br>[\[differences\]][190723-dif] `41`</sub> | Elo: [0.10][190723-elo1] ±1.4<br><sub>Ptnml:&nbsp;96,&nbsp;6835,&nbsp;16121,&nbsp;6851,&nbsp;97<br>nElo: 0.21 ±2.8<br>PairsRatio: 1.00<br>[\[raw statistics\]][190723-raw1]</sub> | Elo: [2.10][190723-elo8] ±1.3<br><sub>Ptnml:&nbsp;30,&nbsp;5872,&nbsp;17820,&nbsp;6261,&nbsp;17<br>nElo: 4.64 ±2.8<br>PairsRatio: 1.06<br>[\[raw statistics\]][190723-raw8]</sub>
| 2023&#8209;08&#8209;13 | [master][130823-master] vs [Stockfish 16]<br><sub>`Bench: 1447866`<br>Simplify material difference in evaluate<br>[\[differences\]][130823-dif] `68`</sub> | Elo: [0.58][130823-elo1] ±1.4<br><sub>Ptnml:&nbsp;120,&nbsp;6787,&nbsp;16066,&nbsp;6927,&nbsp;100<br>nElo: 1.17 ±2.8<br>PairsRatio: 1.02<br>[\[raw statistics\]][130823-raw1]</sub> | Elo: [2.08][130823-elo8] ±1.2<br><sub>Ptnml:&nbsp;15,&nbsp;5797,&nbsp;18021,&nbsp;6147,&nbsp;20<br>nElo: 4.65 ±2.8<br>PairsRatio: 1.06<br>[\[raw statistics\]][130823-raw8]</sub>
| 2023&#8209;09&#8209;11 | [master][110923-master] vs [Stockfish 16]<br><sub>`Bench: 1603079`<br>Cleanup code after dropping ICC support in favor of ICX<br>[\[differences\]][110923-dif] `93`</sub> | Elo: [7.66][110923-elo1] ±1.4<br><sub>Ptnml:&nbsp;86,&nbsp;6160,&nbsp;16212,&nbsp;7429,&nbsp;113<br>nElo: 15.68 ±2.8<br>PairsRatio: 1.21<br>[\[raw statistics\]][110923-raw1]</sub> | Elo: [5.65][110923-elo8] ±1.2<br><sub>Ptnml:&nbsp;16,&nbsp;5524,&nbsp;17944,&nbsp;6500,&nbsp;16<br>nElo: 12.57 ±2.8<br>PairsRatio: 1.18<br>[\[raw statistics\]][110923-raw8]</sub>
| 2023&#8209;09&#8209;22 | [master][220923-master] vs [Stockfish 16]<br><sub>`Bench: 1246812`<br>Update NNUE architecture to SFNNv8: L1-2560 nn-ac1dbea57aa3.nnue<br>[\[differences\]][220923-dif] `103`</sub> | Elo: [3.33][220923-elo1] ±1.4<br><sub>Ptnml:&nbsp;106,&nbsp;6534,&nbsp;16134,&nbsp;7131,&nbsp;95<br>nElo: 6.78 ±2.8<br>PairsRatio: 1.09<br>[\[raw statistics\]][220923-raw1]</sub> | Elo: [6.61][220923-elo8] ±1.3<br><sub>Ptnml:&nbsp;21,&nbsp;5553,&nbsp;17713,&nbsp;6689,&nbsp;24<br>nElo: 14.56 ±2.8<br>PairsRatio: 1.20<br>[\[raw statistics\]][220923-raw8]</sub>
| 2023&#8209;10&#8209;08 | [master][081023-master] vs [Stockfish 16]<br><sub>`Bench: 1246560`<br>Skip futility pruning if ttMove has bad history<br>[\[differences\]][081023-dif] `119`</sub> | Elo: [9.68][081023-elo1] ±1.4<br><sub>Ptnml:&nbsp;100,&nbsp;6094,&nbsp;15972,&nbsp;7702,&nbsp;132<br>nElo: 19.61 ±2.8<br>PairsRatio: 1.26<br>[\[raw statistics\]][081023-raw1]</sub> | Elo: [10.30][081023-elo8] ±1.3<br><sub>Ptnml:&nbsp;13,&nbsp;5168,&nbsp;17868,&nbsp;6930,&nbsp;21<br>nElo: 22.90 ±2.8<br>PairsRatio: 1.34<br>[\[raw statistics\]][081023-raw8]</sub>
| 2023&#8209;10&#8209;23 | [master][231023-master] vs [Stockfish 16]<br><sub>`Bench: 1241996`<br>Follow up Makefile changes for clang-format<br>[\[differences\]][231023-dif] `136`</sub> | Elo: [10.47][231023-elo1] ±1.4<br><sub>Ptnml:&nbsp;94,&nbsp;6071,&nbsp;15901,&nbsp;7801,&nbsp;133<br>nElo: 21.17 ±2.8<br>PairsRatio: 1.29<br>[\[raw statistics\]][231023-raw1]</sub> | Elo: [9.16][231023-elo8] ±1.3<br><sub>Ptnml:&nbsp;19,&nbsp;5311,&nbsp;17763,&nbsp;6884,&nbsp;23<br>nElo: 20.24 ± 2.8<br>ParsRatio: 1.30<br>[\[raw statistics\]][231023-raw8]</sub>
| 2023&#8209;11&#8209;03 | [master][031123-master] vs [Stockfish 16]<br><sub>`Bench: 1330590`<br>Update pawn history based on static eval difference<br>[\[differences\]][031123-dif] `150`</sub> | Elo: [10.57][031123-elo1] ±1.4<br><sub>Ptnml:&nbsp;112,&nbsp;6018,&nbsp;15922,&nbsp;7829,&nbsp;119<br>nElo: 21.38 ±2.8<br>PairsRatio: 1.30<br>[\[raw statistics\]][031123-raw1]</sub> | Elo: [9.16][031123-elo8] ±1.3<br><sub>Ptnml:&nbsp;27,&nbsp;5330,&nbsp;17701,&nbsp;6919,&nbsp;23<br>nElo: 20.17 ±2.8<br>PairsRatio: 1.30<br>[\[raw statistics\]][031123-raw8]</sub>
| 2023&#8209;12&#8209;02 | [master][021223-master] vs [Stockfish 16]<br><sub>`Bench: 1403703`<br>Tweak return value in futility pruning<br>[\[differences\]][021223-dif] `172`</sub> | Elo: [12.59][021223-elo1] ±1.4<br><sub>Ptnml:&nbsp;93,&nbsp;5810,&nbsp;16029,&nbsp;7966,&nbsp;102<br>nElo: 25.70 ±2.8<br>PairsRatio: 1.37<br>[\[raw statistics\]][021223-raw1]</sub> | Elo: [10.08][021223-elo8] ±1.3<br><sub>Ptnml:&nbsp;18,&nbsp;5168,&nbsp;17893,&nbsp;6897,&nbsp;24<br>nElo: 22.42 ±2.8<br>PairsRatio: 1.33<br>[\[raw statistics\]][021223-raw8]</sub>
| 2023&#8209;12&#8209;31 | [master][311223-master] vs [Stockfish 16]<br><sub>`Bench: 1392883`<br>Tweak static eval history update<br>[\[differences\]][311223-dif] `202`</sub> | Elo: [19.19][311223-elo1] ±1.4<br><sub>Ptnml:&nbsp;74,&nbsp;5393,&nbsp;15884,&nbsp;8446,&nbsp;203<br>nElo: 38.89 ±2.8<br>PairsRatio: 1.58<br>[\[raw statistics\]][311223-raw1]</sub> | Elo: [16.82][311223-elo8] ±1.3<br><sub>Ptnml:&nbsp;13,&nbsp;4672,&nbsp;17747,&nbsp;7535,&nbsp;33<br>nElo: 37.42 ±2.8<br>PairsRatio: 1.62<br>[\[raw statistics\]][311223-raw8]</sub>
| 2024&#8209;01&#8209;07 | [master][070124-master] vs [Stockfish 16]<br><sub>`Bench: 1438336`<br>Prefix abs with std::<br>[\[differences\]][070124-dif] `219`</sub> | Elo: [25.53][070124-elo1] ±1.4<br><sub>Ptnml:&nbsp;58,&nbsp;4917,&nbsp;15789,&nbsp;9038,&nbsp;198<br>nElo: 52.14 ±2.8<br>PairsRatio: 1.86<br>[\[raw statistics\]][070124-raw1]</sub> | Elo: [18.88][070124-elo8] ±1.3<br><sub>Ptnml:&nbsp;12,&nbsp;4602,&nbsp;17534,&nbsp;7820,&nbsp;32<br>nElo: 41.76 ±2.8<br>PairsRatio: 1.70<br>[\[raw statistics\]][070124-raw8]</sub>
| 2024&#8209;01&#8209;21 | [master][210124-master] vs [Stockfish 16]<br><sub>`Bench: 1235377`<br>VLTC search tune<br>[\[differences\]][210124-dif] `242`</sub> | Elo: [26.49][210124-elo1] ±1.4<br><sub>Ptnml:&nbsp;64,&nbsp;4791,&nbsp;15823,&nbsp;9159,&nbsp;163<br>nElo: 54.42 ±2.8<br>PairsRatio: 1.92<br>[\[raw statistics\]][210124-raw1]</sub> | Elo: [22.91][210124-elo8] ±1.2<br><sub>Ptnml:&nbsp;12,&nbsp;4114,&nbsp;17807,&nbsp;8046,&nbsp;21<br>nElo: 51.64 ±2.8<br>PairsRatio: 1.96<br>[\[raw statistics\]][210124-raw8]</sub>
| 2024&#8209;02&#8209;11 | [master][110224-master] vs [Stockfish 16]<br><sub>`Bench: 1027182`<br>Format code using clang-format<br>[\[differences\]][110224-dif] `269`</sub> | Elo: [22.81][110224-elo1] ±1.4<br><sub>Ptnml:&nbsp;81,&nbsp;5104,&nbsp;15792,&nbsp;8846,&nbsp;177<br>nElo: 46.39 ±2.8<br>PairsRatio: 1.74<br>[\[raw statistics\]][110224-raw1]</sub> | Elo: [22.13][110224-elo8] ±1.3<br><sub>Ptnml:&nbsp;22,&nbsp;4312,&nbsp;17524,&nbsp;8112,&nbsp;30<br>nElo: 49.11 ±2.8<br>PairsRatio: 1.88<br>[\[raw statistics\]][110224-raw8]</sub>
| 2024&#8209;02&#8209;17 | [master][170224-master] vs [Stockfish 16]<br><sub>`Bench: 1303971`<br>Simplify PV node reduction<br>[\[differences\]][170224-dif] `276`</sub> | Elo: [27.04][170224-elo1] ±1.4<br><sub>Ptnml:&nbsp;65,&nbsp;4832,&nbsp;15656,&nbsp;9272,&nbsp;175<br>nElo: 55.20 ±2.9<br>PairsRatio: 1.93<br>[\[raw statistics\]][170224-raw1]</sub> | Elo: [27.03][170224-elo8] ±1.2<br><sub>Ptnml:&nbsp;16,&nbsp;3891,&nbsp;17544,&nbsp;8517,&nbsp;32<br>nElo: 60.62 ±2.9<br>PairsRatio: 2.19<br>[\[raw statistics\]][170224-raw8]</sub>
| 2024&#8209;02&#8209;24 | [Stockfish 16.1] [[[https://stockfishchess.org/images/logo/icon_128x128.png\|width=20px]]][SF161RN]<br><sub>`Bench: 1303971`<br>[\[differences\]][240224-dif] `280`</sub> |  |  |  |
| 2024&#8209;03&#8209;12 | [master][120324-master] vs [Stockfish 16]<br><sub>`Bench: 1715522`<br>Search + Eval + Movepick Tune<br>[\[differences\]][120324-dif] `302`</sub> | Elo: [27.13][120324-elo1] ±1.4<br><sub>Ptnml:&nbsp;79,&nbsp;4801,&nbsp;15674,&nbsp;9257,&nbsp;189<br>nElo: 55.27 ±2.9<br>PairsRatio: 1.94<br>[\[raw statistics\]][120324-raw1]</sub> | Elo: [29.99][120324-elo8] ±1.2<br><sub>Ptnml:&nbsp;15,&nbsp;3656,&nbsp;17515,&nbsp;8775,&nbsp;39<br>nElo: 67.59 ±2.9<br>PairsRatio: 2.40<br>[\[raw statistics\]][120324-raw8]</sub>
| 2024&#8209;03&#8209;29 | [master][290324-master] vs [Stockfish 16]<br><sub>`Bench: 1759189`<br>Simplify NMP Condition<br>[\[differences\]][290324-dif] `322`</sub> | Elo: [27.73][290324-elo1] ±1.4<br><sub>Ptnml:&nbsp;80,&nbsp;4736,&nbsp;15703,&nbsp;9287,&nbsp;194<br>nElo: 56.57 ±2.9<br>PairsRatio: 1.97<br>[\[raw statistics\]][290324-raw1]</sub> | Elo: [30.03][290324-elo8] ±1.2<br><sub>Ptnml:&nbsp;16,&nbsp;3637,&nbsp;17534,&nbsp;8784,&nbsp;29<br>nElo: 67.81 ±2.9<br>PairsRatio: 2.41<br>[\[raw statistics\]][290324-raw8]</sub>
| 2024&#8209;04&#8209;11 | [master][110424-master] vs [Stockfish 16]<br><sub>`Bench: 1479416`<br>Simplify the depth-dependent part of the best value adjustment formula in main search<br>[\[differences\]][110424-dif] `333`</sub> | Elo: [23.53][110424-elo1] ±1.4<br><sub>Ptnml:&nbsp;75,&nbsp;5095,&nbsp;15696,&nbsp;8965,&nbsp;169<br>nElo: 47.82 ±2.8<br>PairsRatio: 1.77<br>[\[raw statistics\]][110424-raw1]</sub> | Elo: [35.27][110424-elo8] ±1.2<br><sub>Ptnml:&nbsp;10,&nbsp;3235,&nbsp;17465,&nbsp;9255,&nbsp;35<br>nElo: 80.49 ±2.9<br>PairsRatio: 2.86<br>[\[raw statistics\]][110424-raw8]</sub>
| 2024&#8209;04&#8209;24 | [master][240424-master] vs [Stockfish 16]<br><sub>`Bench: 1836777`<br>Implement accumulator refresh table<br>[\[differences\]][240424-dif] `348`</sub> | Elo: [32.04][240424-elo1] ±1.4<br><sub>Ptnml:&nbsp;51,&nbsp;4471,&nbsp;15578,&nbsp;9709,&nbsp;191<br>nElo: 65.84 ±2.9<br>PairsRatio: 2.19<br>[\[raw statistics\]][240424-raw1]</sub> | Elo: [37.86][240424-elo8] ±1.2<br><sub>Ptnml:&nbsp;7,&nbsp;3255,&nbsp;17012,&nbsp;9670,&nbsp;56<br>nElo: 85.18 ±2.9<br>PairsRatio: 2.98<br>[\[raw statistics\]][240424-raw8]</sub>
| 2024&#8209;05&#8209;05 | [master][050524-master] vs [Stockfish 16]<br><sub>`Bench: 2180675`<br>VVLTC search tune<br>[\[differences\]][050524-dif] `369`</sub> | Elo: [28.90][050524-elo1] ±1.4<br><sub>Ptnml:&nbsp;70,&nbsp;4716,&nbsp;15571,&nbsp;9451,&nbsp;192<br>nElo: 58.87 ±2.9<br>PairsRatio: 2.01<br>[\[raw statistics\]][050524-raw1]</sub> | Elo: [40.41][050524-elo8] ±1.2<br><sub>Ptnml:&nbsp;6,&nbsp;3047,&nbsp;16994,&nbsp;9899,&nbsp;54<br>nElo: 91.59 ±2.9<br>PairsRatio: 3.26<br>[\[raw statistics\]][050524-raw8]</sub>
| 2024&#8209;05&#8209;13 | [master][130524-master] vs [Stockfish 16]<br><sub>`Bench: 1876282`<br>Optimize update_accumulator_refresh_cache()<br>[\[differences\]][130524-dif] `386`</sub> | Elo: [28.23][130524-elo1] ±1.4<br><sub>Ptnml:&nbsp;94,&nbsp;4694,&nbsp;15651,&nbsp;9376,&nbsp;185<br>nElo: 57.50 ±2.9<br>PairsRatio: 2.00<br>[\[raw statistics\]][130524-raw1]</sub> | Elo: [39.08][130524-elo8] ±1.2<br><sub>Ptnml:&nbsp;12,&nbsp;3037,&nbsp;17207,&nbsp;9707,&nbsp;37<br>nElo: 89.14 ±2.9<br>PairsRatio: 3.20<br>[\[raw statistics\]][130524-raw8]</sub>
| 2024&#8209;05&#8209;18 | [master][180524-master] vs [Stockfish 16]<br><sub>`Bench: 1198142`<br>VVLTC search tune<br>[\[differences\]][180524-dif] `405`</sub> | Elo: [26.54][180524-elo1] ±1.4<br><sub>Ptnml:&nbsp;78,&nbsp;4876,&nbsp;15650,&nbsp;9185,&nbsp;211<br>nElo: 53.85 ±2.8<br>PairsRatio: 1.90<br>[\[raw statistics\]][180524-raw1]</sub> | Elo: [38.55][180524-elo8] ±1.2<br><sub>Ptnml:&nbsp;11,&nbsp;3150,&nbsp;17089,&nbsp;9698,&nbsp;52<br>nElo: 87.18 ±2.9<br>PairsRatio: 3.08<br>[\[raw statistics\]][180524-raw8]</sub>
| 2024&#8209;05&#8209;28 | [master][280524-master] vs [Stockfish 16]<br><sub>`Bench: 1856147`<br>Improve performance on NUMA systems<br>[\[differences\]][280524-dif] `433`</sub> | Elo: [30.13][280524-elo1] ±1.4<br><sub>Ptnml:&nbsp;65,&nbsp;4557,&nbsp;15687,&nbsp;9504,&nbsp;187<br>nElo: 61.85 ±2.9<br>PairsRatio: 2.10<br>[\[raw statistics\]][280524-raw1]</sub> | Elo: [39.34][280524-elo8] ±1.2<br><sub>Ptnml:&nbsp;6,&nbsp;3094,&nbsp;17063,&nbsp;9803,&nbsp;34<br>nElo: 89.36 ±2.9<br>PairsRatio: 3.17<br>[\[raw statistics\]][280524-raw8]</sub>
| 2024&#8209;06&#8209;08 | [master][080624-master] vs [Stockfish 16]<br><sub>`Bench: 1174094`<br>Make repeated bench runs identical<br>[\[differences\]][080624-dif] `490`</sub> | Elo: [35.60][080624-elo1] ±1.4<br><sub>Ptnml:&nbsp;70,&nbsp;4218,&nbsp;15445,&nbsp;10049,&nbsp;218<br>nElo: 73.01 ±2.9<br>PairsRatio: 2.39<br>[\[raw statistics\]][080624-raw1]</sub> | Elo: [39.31][080624-elo8] ±1.2<br><sub>Ptnml:&nbsp;15,&nbsp;3169,&nbsp;16895,&nbsp;9884,&nbsp;37<br>nElo: 88.49 ±2.9<br>PairsRatio: 3.12<br>[\[raw statistics\]][080624-raw8]</sub>
| 2024&#8209;07&#8209;01 | [master][010724-master] vs [Stockfish 16]<br><sub>`Bench: 1227870`<br>Probcut in check no matter if pv or capture<br>[\[differences\]][010724-dif] `517`</sub> | Elo: [40.07][010724-elo1] ±1.4<br><sub>Ptnml:&nbsp;83,&nbsp;3933,&nbsp;15243,&nbsp;10493,&nbsp;248<br>nElo: 82.11 ±2.9<br>PairsRatio: 2.67<br>[\[raw statistics\]][010724-raw1]</sub> | Elo: [40.34][010724-elo8] ±1.2<br><sub>Ptnml:&nbsp;11,&nbsp;3043,&nbsp;16987,&nbsp;9918,&nbsp;41<br>nElo: 91.47 ±2.9<br>PairsRatio: 3.26<br>[\[raw statistics\]][010724-raw8]</sub>
| 2024&#8209;07&#8209;09 | [master][090724-master] vs [Stockfish 16]<br><sub>`Bench: 1300471`<br>Move Loop Consistency in Probcut<br>[\[differences\]][090724-dif] `548`</sub> | Elo: [41.51][090724-elo1] ±1.4<br><sub>Ptnml:&nbsp;68,&nbsp;3769,&nbsp;15319,&nbsp;10649,&nbsp;195<br>nElo: 86.22 ±3.0<br>PairsRatio: 2.83<br>[\[raw statistics\]][090724-raw1]</sub> | Elo: [43.42][090724-elo8] ±1.2<br><sub>Ptnml:&nbsp;15,&nbsp;2811,&nbsp;16912,&nbsp;10224,&nbsp;38<br>nElo: 99.12 ±3.0<br>PairsRatio: 3.63<br>[\[raw statistics\]][090724-raw8]</sub>
| 2024&#8209;07&#8209;23 | [master][230724-master] vs [Stockfish 16]<br><sub>`Bench: 1371485`<br>Update default main net to nn-31337bea577c.nnue<br>[\[differences\]][230724-dif] `578`</sub> | Elo: [42.30][230724-elo1] ±1.4<br><sub>Ptnml:&nbsp;59,&nbsp;3800,&nbsp;15131,&nbsp;10833,&nbsp;177<br>nElo: 87.72 ±3.0<br>PairsRatio: 2.85<br>[\[raw statistics\]][230724-raw1]</sub> | Elo: [45.06][230724-elo8] ±1.2<br><sub>Ptnml:&nbsp;14,&nbsp;2685,&nbsp;16907,&nbsp;10337,&nbsp;57<br>nElo: 103.20 ±3.0<br>PairsRatio: 3.85<br>[\[raw statistics\]][230724-raw8]</sub>
| 2024&#8209;08&#8209;20 | [master][200824-master] vs [Stockfish 16]<br><sub>`Bench: 1484730`<br>Tweak late move extensions<br>[\[differences\]][200824-dif] `595`</sub> | Elo: [44.12][200824-elo1] ±1.4<br><sub>Ptnml:&nbsp;69,&nbsp;3686,&nbsp;15064,&nbsp;10960,&nbsp;221<br>nElo: 91.20 ±3.0<br>PairsRatio: 2.98<br>[\[raw statistics\]][200824-raw1]</sub> | Elo: [44.32][200824-elo8] ±1.2<br><sub>Ptnml:&nbsp;16,&nbsp;2814,&nbsp;16741,&nbsp;10400,&nbsp;29<br>nElo: 100.85 ±3.0<br>PairsRatio: 3.69<br>[\[raw statistics\]][200824-raw8]</sub>
</div>

---

## Version Comparison

### Elo Progression

| [![][graph-elo1]][graph-elo1] | [![][graph-elo8]][graph-elo8] |
|:---------------------------------:|:---------------------------------:|

### Normalized Elo Progression

| [![][graph-nelo1]][graph-nelo1] | [![][graph-nelo8]][graph-nelo8] |
|:---------------------------------:|:---------------------------------:|

### Game Pair Ratio Progression

| [![][graph-gpr1]][graph-gpr1] | [![][graph-gpr8]][graph-gpr8] |
|:---------------------------------:|:---------------------------------:|

### 30 Day Average

| [![][graph-thirty1]][graph-thirty1] | [![][graph-thirty8]][graph-thirty8] |
|:-----------------------------------:|:-----------------------------------:|

### Draw Percentage vs Elo

| [![][graph-dve1]][graph-dve1] | [![][graph-dve8]][graph-dve8] |
|:-----------------------------:|:-----------------------------:|

---

## Historical Information

<details>
  <summary><code>Stockfish 3 Development (2013-03-01 - 2013-04-30)</code></summary><br>

| `Date` | `Version` | `1 Thread` |
|:------:|:---------:|:----------:|
| 2013&#8209;03&#8209;04 | [master][040313-master] vs [Stockfish 2.3.1]<br><sub>`Bench: 4968764`<br>Increase see prune depth<br>[\[differences\]][040313-dif] `226`</sub> | Elo: [15.00][040313-elo1] ±2.8<br><sub>WDL:&nbsp;2906,&nbsp;13325,&nbsp;3769<br>nElo: 26.02 ±4.8<br>[\[raw statistics\]][040313-raw1]</sub> |
| 2013&#8209;03&#8209;11 | [master][110313A-master] vs [Stockfish 2.3.1]<br><sub>`Bench: 4968764`<br>Be more aggressive on trying to finish iterations<br>[\[differences\]][110313A-dif] `227`</sub> | Elo: [15.49][110313A-elo1] ±2.8<br><sub>WDL:&nbsp;3016,&nbsp;13077,&nbsp;3907<br>nElo: 26.38 ±4.8<br>[\[raw statistics\]][110313A-raw1]</sub> |
| 2013&#8209;03&#8209;11 | [master][110313B-master] vs [Stockfish 2.3.1]<br><sub>`Bench: 4968764`<br>Check for easy move just once<br>[\[differences\]][110313B-dif] `228`</sub> | Elo: [13.42][110313B-elo1] ±2.8<br><sub>WDL:&nbsp;2974,&nbsp;13280,&nbsp;3746<br>nElo: 23.19 ±4.8<br>[\[raw statistics\]][110313B-raw1]</sub> |
| 2013&#8209;03&#8209;16 | [master][160313-master] vs [Stockfish 2.3.1]<br><sub>`Bench: 5442365`<br>Further increase SEE prune depth<br>[\[differences\]][160313-dif] `232`</sub> | Elo: [17.77][160313-elo1] ±2.8<br><sub>WDL:&nbsp;2897,&nbsp;13184,&nbsp;3919<br>nElo: 30.53 ±4.8<br>[\[raw statistics\]][160313-raw1]</sub> |
| 2013&#8209;03&#8209;24 | [master][240313-master] vs [Stockfish 2.3.1]<br><sub>`Bench: 4985829`<br>Update bestValue when futility pruning (2)<br>[\[differences\]][240313-dif] `237`</sub> | Elo: [16.71][240313-elo1] ±2.8<br><sub>WDL:&nbsp;2874,&nbsp;13291,&nbsp;3835<br>nElo: 28.92 ±4.8<br>[\[raw statistics\]][240313-raw1]</sub> |
| 2013&#8209;03&#8209;30 | [master][300313-master] vs [Stockfish 2.3.1]<br><sub>`Bench: 4781239`<br>Set IID half way between d/2 and d-4<br>[\[differences\]][300313-dif] `241`</sub> | Elo: [18.76][300313-elo1] ±2.8<br><sub>WDL:&nbsp;2824,&nbsp;13273,&nbsp;3903<br>nElo: 32.46 ±4.8<br>[\[raw statistics\]][300313-raw1]</sub> |
| 2013&#8209;04&#8209;03 | [master][030413-master] vs [Stockfish 2.3.1]<br><sub>`Bench: 4705335`<br>Double Impact of Gain tables<br>[\[differences\]][030413-dif] `242`</sub> | Elo: [15.44][030413-elo1] ±2.8<br><sub>WDL:&nbsp;3040,&nbsp;13032,&nbsp;3928<br>nElo: 26.21 ±4.8<br>[\[raw statistics\]][030413-raw1]</sub> |
| 2013&#8209;04&#8209;06 | [master][060413-master] vs [Stockfish 2.3.1]<br><sub>`Bench: 4361224`<br>Increase null verification threshold to 12 plies<br>[\[differences\]][060413-dif] `249`</sub> | Elo: [17.11][060413-elo1] ±2.8<br><sub>WDL:&nbsp;2774,&nbsp;12861,&nbsp;3727<br>nElo: 29.62 ±4.9<br>[\[raw statistics\]][060413-raw1]</sub> |
| 2013&#8209;04&#8209;07 | [master][070413-master] vs [Stockfish 2.3.1]<br><sub>`Bench: 5473339`<br>Rescale UCI parameters to 100<br>[\[differences\]][070413-dif] `252`</sub> | Elo: [19.02][070413-elo1] ±2.8<br><sub>WDL:&nbsp;2948,&nbsp;13010,&nbsp;4042<br>nElo: 32.29 ±4.8<br>[\[raw statistics\]][070413-raw1]</sub> |
| 2013&#8209;04&#8209;10 | [master][100413-master] vs [Stockfish 2.3.1]<br><sub>`Bench: 5157061`<br>De-templetize Position::is_draw()<br>[\[differences\]][100413-dif] `257`</sub> | Elo: [24.13][100413-elo1] ±2.8<br><sub>WDL:&nbsp;2791,&nbsp;13031,&nbsp;4178<br>nElo: 41.10 ±4.8<br>[\[raw statistics\]][100413-raw1]</sub> |
| 2013&#8209;04&#8209;19 | [master][190413-master] vs [Stockfish 2.3.1]<br><sub>`Bench: 5274705`<br>Skip a couple of popcount in previous patch<br>[\[differences\]][190413-dif] `262`</sub> | Elo: [28.27][190413-elo1] ±2.9<br><sub>WDL:&nbsp;2754,&nbsp;12868,&nbsp;4378<br>nElo: 47.69 ±4.9<br>[\[raw statistics\]][190413-raw1]</sub> |
| 2013&#8209;04&#8209;26 | [master][260413-master] vs [Stockfish 2.3.1]<br><sub>`Bench: 4311634`<br>Fix a crash introduced few days ago<br>[\[differences\]][260413-dif] `270`</sub> | Elo: [33.67][260413-elo1] ±2.9<br><sub>WDL:&nbsp;2642,&nbsp;12784,&nbsp;4574<br>nElo: 56.61 ±4.9<br>[\[raw statistics\]][260413-raw1]</sub> |
| 2013&#8209;04&#8209;28 | [master][280413-master] vs [Stockfish 2.3.1]<br><sub>`Bench: 4176431`<br>Temporary revert "Expose EvalInfo struct to search"<br>[\[differences\]][280413-dif] `273`</sub> | Elo: [30.86][280413-elo1] ±2.9<br><sub>WDL:&nbsp;2721,&nbsp;12786,&nbsp;4493<br>nElo: 51.82 ±4.9<br>[\[raw statistics\]][280413-raw1]</sub> |
| 2013&#8209;04&#8209;30 | [Stockfish 3] [[[https://stockfishchess.org/images/logo/icon_128x128.png\|width=20px]]][SF3RN] [[[https://github.githubassets.com/images/icons/emoji/unicode/1f4c8.png\|width=20px]]][SF3DP]<br><sub>`Bench: 4176431`<br>[\[differences\]][300413-dif] `275`</sub> |

</details>

<details>
  <summary><code>Stockfish 4 Development (2013-04-30 - 2013-08-20)</code></summary><br>

| `Date` | `Version` | `1 Thread` |
|:------:|:---------:|:----------:|
| 2013&#8209;05&#8209;16 | [master][160513-master] vs [Stockfish 3]<br><sub>`Bench: 4327405`<br>Use two counter moves instead of one<br>[\[differences\]][160513-dif] `28`</sub> | Elo: [22.11][160513-elo1] ±3.0<br><sub>WDL:&nbsp;3212,&nbsp;12305,&nbsp;4483<br>nElo: 35.78 ±4.8<br>[\[raw statistics\]][160513-raw1]</sub> |
| 2013&#8209;05&#8209;23 | [master][230513-master] vs [Stockfish 3]<br><sub>`Bench: 4821467`<br>Bunch of 3 small patches<br>[\[differences\]][230513-dif] `33`</sub> | Elo: [26.70][230513-elo1] ±2.1<br><sub>WDL:&nbsp;6435,&nbsp;24062,&nbsp;9503<br>nElo: 42.53 ±3.4<br>[\[raw statistics\]][230513-raw1]</sub> |
| 2013&#8209;05&#8209;31 | [master][310513-master] vs [Stockfish 3]<br><sub>`Bench: 4931544`<br>Passed pawn tuning<br>[\[differences\]][310513-dif] `38`</sub> | Elo: [29.50][310513-elo1] ±2.2<br><sub>WDL:&nbsp;6588,&nbsp;23436,&nbsp;9976<br>nElo: 46.13 ±3.4<br>[\[raw statistics\]][310513-raw1]</sub> |
| 2013&#8209;06&#8209;23 | [master][230613-master] vs [Stockfish 3]<br><sub>`Bench: 4609948`<br>Fix some stale comments<br>[\[differences\]][230613-dif] `72`</sub> | Elo: [35.47][230613-elo1] ±2.2<br><sub>WDL:&nbsp;6196,&nbsp;23539,&nbsp;10265<br>nElo: 55.80 ±3.4<br>[\[raw statistics\]][230613-raw1]</sub> |
| 2013&#8209;07&#8209;03 | [master][030713-master] vs [Stockfish 3]<br><sub>`Bench: 4507288`<br>Simplify aspiration window code<br>[\[differences\]][030713-dif] `88`</sub> | Elo: [37.36][030713-elo1] ±2.2<br><sub>WDL:&nbsp;6223,&nbsp;23269,&nbsp;10508<br>nElo: 58.35 ±3.4<br>[\[raw statistics\]][030713-raw1]</sub> |
| 2013&#8209;07&#8209;13 | [master][130713-master] vs [Stockfish 3]<br><sub>`Bench: 4558173`<br>Fully qualify memset and memcpy<br>[\[differences\]][130713-dif] `100`</sub> | Elo: [39.27][130713-elo1] ±3.1<br><sub>WDL:&nbsp;3052,&nbsp;11645,&nbsp;5303<br>nElo: 61.44 ±4.9<br>[\[raw statistics\]][130713-raw1]</sub> |
| 2013&#8209;07&#8209;19 | [master][190713-master] vs [Stockfish 3]<br><sub>`Bench: 4769737`<br>Halve king eval margin<br>[\[differences\]][190713-dif] `110`</sub> | Elo: [39.83][190713-elo1] ±3.1<br><sub>WDL:&nbsp;3067,&nbsp;11583,&nbsp;5350<br>nElo: 62.10 ±4.9<br>[\[raw statistics\]][190713-raw1]</sub> |
| 2013&#8209;07&#8209;25 | [master][250713-master] vs [Stockfish 3]<br><sub>`Bench: 4727133`<br>Rewrite pawn shield and storm code<br>[\[differences\]][250713-dif] `133`</sub> | Elo: [48.84][250713-elo1] ±3.3<br><sub>WDL:&nbsp;3203,&nbsp;10801,&nbsp;5996<br>nElo: 73.11 ±4.9<br>[\[raw statistics\]][250713-raw1]</sub> |
| 2013&#8209;08&#8209;03 | [master][030813-master] vs [Stockfish 3]<br><sub>`Bench: 4424151`<br>Streamline time computation<br>[\[differences\]][030813-dif] `147`</sub> | Elo: [50.95][030813-elo1] ±3.2<br><sub>WDL:&nbsp;3056,&nbsp;10976,&nbsp;5968<br>nElo: 77.14 ±4.9<br>[\[raw statistics\]][030813-raw1]</sub> |
| 2013&#8209;08&#8209;18 | [master][180813-master] vs [Stockfish 3]<br><sub>`Bench: 4132374`<br>Further tweak movecount pruning<br>[\[differences\]][180813-dif] `162`</sub> | Elo: [56.66][180813-elo1] ±3.3<br><sub>WDL:&nbsp;2988,&nbsp;10791,&nbsp;6221<br>nElo: 85.22 ±5.0<br>[\[raw statistics\]][180813-raw1]</sub> |
| 2013&#8209;08&#8209;20 | [Stockfish 4] [[[https://stockfishchess.org/images/logo/icon_128x128.png\|width=20px]]][SF4RN] [[[https://github.githubassets.com/images/icons/emoji/unicode/1f4c8.png\|width=20px]]][SF4DP]<br><sub>`Bench: 4132374`<br>[\[differences\]][200813-dif] `165`</sub> |

</details>

<details>
  <summary><code>Stockfish DD Development (2013-08-20 - 2013-11-29)</code></summary><br>

| `Date` | `Version` | `1 Thread` |
|:------:|:---------:|:----------:|
| 2013&#8209;08&#8209;29 | [master][290813-master] vs [Stockfish 4]<br><sub>`Bench: 4620975`<br>Enable LMR for dangerous moves<br>[\[differences\]][290813-dif] `12`</sub> | Elo: [16.18][290813-elo1] ±2.9<br><sub>WDL:&nbsp;3221,&nbsp;12627,&nbsp;4152<br>nElo: 26.72 ±4.8<br>[\[raw statistics\]][290813-raw1]</sub> |
| 2013&#8209;09&#8209;01 | [master][010913-master] vs [Stockfish 4]<br><sub>`Bench: 3453945`<br>Don't use lpthread for Android<br>[\[differences\]][010913-dif] `18`</sub> | Elo: [19.30][010913-elo1] ±2.9<br><sub>WDL:&nbsp;3083,&nbsp;12724,&nbsp;4193<br>nElo: 32.11 ±4.8<br>[\[raw statistics\]][010913-raw1]</sub> |
| 2013&#8209;09&#8209;05 | [master][050913-master] vs [Stockfish 4]<br><sub>`Bench: 4633330`<br>Do not prune useless checks in QS<br>[\[differences\]][050913-dif] `23`</sub> | Elo: [23.80][050913-elo1] ±2.9<br><sub>WDL:&nbsp;2932,&nbsp;12768,&nbsp;4300<br>nElo: 39.78 ±4.8<br>[\[raw statistics\]][050913-raw1]</sub> |
| 2013&#8209;09&#8209;07 | [master][070913-master] vs [Stockfish 4]<br><sub>`Bench: 3864419`<br>Remove unreachable values in mobility table<br>[\[differences\]][070913-dif] `27`</sub> | Elo: [27.66][070913-elo1] ±2.9<br><sub>WDL:&nbsp;2766,&nbsp;12879,&nbsp;4355<br>nElo: 46.68 ±4.9<br>[\[raw statistics\]][070913-raw1]</sub> |
| 2013&#8209;09&#8209;11 | [master][110913-master] vs [Stockfish 4]<br><sub>`Bench: 4554576`<br>Extend checks more when below alpha<br>[\[differences\]][110913-dif] `35`</sub> | Elo: [24.87][110913-elo1] ±2.9<br><sub>WDL:&nbsp;2824,&nbsp;12923,&nbsp;4253<br>nElo: 42.04 ±4.8<br>[\[raw statistics\]][110913-raw1]</sub> |
| 2013&#8209;09&#8209;12 | [master][120913-master] vs [Stockfish 4]<br><sub>`Bench: 4554579`<br>Revert "Move draw by material check"<br>[\[differences\]][120913-dif] `37`</sub> | Elo: [24.34][120913-elo1] ±2.9<br><sub>WDL:&nbsp;2825,&nbsp;12951,&nbsp;4224<br>nElo: 41.22 ±4.8<br>[\[raw statistics\]][120913-raw1]</sub> |
| 2013&#8209;09&#8209;13 | [master][130913-master] vs [Stockfish 4]<br><sub>`Bench: 3846852`<br>Increase passed bonus for having more pieces<br>[\[differences\]][130913-dif] `38`</sub> | Elo: [26.21][130913-elo1] ±2.9<br><sub>WDL:&nbsp;2871,&nbsp;12752,&nbsp;4377<br>nElo: 43.80 ±4.8<br>[\[raw statistics\]][130913-raw1]</sub> |
| 2013&#8209;09&#8209;16 | [master][160913-master] vs [Stockfish 4]<br><sub>`Bench: 3884003`<br>Fix time parameters for blitz games<br>[\[differences\]][160913-dif] `47`</sub> | Elo: [31.56][160913-elo1] ±2.1<br><sub>WDL:&nbsp;5588,&nbsp;25200,&nbsp;9212<br>nElo: 52.33 ±3.4<br>[\[raw statistics\]][160913-raw1]</sub> |
| 2013&#8209;09&#8209;23 | [master][230913-master] vs [Stockfish 4]<br><sub>`Bench: 3529630`<br>Update disabled warnings for Intel compiler<br>[\[differences\]][230913-dif] `54`</sub> | Elo: [34.03][230913-elo1] ±2.1<br><sub>WDL:&nbsp;5449,&nbsp;25197,&nbsp;9354<br>nElo: 56.49 ±3.4<br>[\[raw statistics\]][230913-raw1]</sub> |
| 2013&#8209;09&#8209;28 | [master][280913-master] vs [Stockfish 4]<br><sub>`Bench: 3172206`<br>Drop 'is' prefix from query functions<br>[\[differences\]][280913-dif] `62`</sub> | Elo: [33.49][280913-elo1] ±2.9<br><sub>WDL:&nbsp;2571,&nbsp;12936,&nbsp;4493<br>nElo: 56.93 ±4.9<br>[\[raw statistics\]][280913-raw1]</sub> |
| 2013&#8209;09&#8209;29 | [master][290913-master] vs [Stockfish 4]<br><sub>`Bench: 8336338`<br>Add more depth/positions to bench<br>[\[differences\]][290913-dif] `63`</sub> | Elo: [33.90][290913-elo1] ±2.0<br><sub>WDL:&nbsp;5292,&nbsp;25525,&nbsp;9183<br>nElo: 56.93 ±3.4<br>[\[raw statistics\]][290913-raw1]</sub> |
| 2013&#8209;10&#8209;08 | [master][081013A-master] vs [Stockfish 4]<br><sub>`Bench: 8340585`<br>Use TT refined value to stand pat<br>[\[differences\]][081013A-dif] `66`</sub> | Elo: [36.58][081013A-elo1] ±2.9<br><sub>WDL:&nbsp;2623,&nbsp;12656,&nbsp;4721<br>nElo: 61.07 ±4.9<br>[\[raw statistics\]][081013A-raw1]</sub> |
| 2013&#8209;10&#8209;08 | [master][081013B-master] vs [Stockfish 4]<br><sub>`Bench: 8340585`<br>Increase slowmover and reduce instability<br>[\[differences\]][081013B-dif] `67`</sub> | Elo: [38.91][081013B-elo1] ±2.1<br><sub>WDL:&nbsp;5102,&nbsp;25335,&nbsp;9563<br>nElo: 65.11 ±3.5<br>[\[raw statistics\]][081013B-raw1]</sub> |
| 2013&#8209;10&#8209;09 | [master][091013-master] vs [Stockfish 4]<br><sub>`Bench: 8279065`<br>Smoother transition for LMR<br>[\[differences\]][091013-dif] `68`</sub> | Elo: [39.29][091013-elo1] ±2.1<br><sub>WDL:&nbsp;5071,&nbsp;25354,&nbsp;9575<br>nElo: 65.80 ±3.4<br>[\[raw statistics\]][091013-raw1]</sub> |
| 2013&#8209;10&#8209;14 | [master][141013-master] vs [Stockfish 4]<br><sub>`Bench: 7700683`<br>Double king safety weights<br>[\[differences\]][141013-dif] `75`</sub> | Elo: [43.64][141013-elo1] ±2.9<br><sub>WDL:&nbsp;2432,&nbsp;12637,&nbsp;4931<br>nElo: 73.12 ±4.9<br>[\[raw statistics\]][141013-raw1]</sub> |
| 2013&#8209;10&#8209;18 | [master][181013-master] vs [Stockfish 4]<br><sub>`Bench: 8440524`<br>Score chain pawn also by rank<br>[\[differences\]][181013-dif] `78`</sub> | Elo: [49.51][181013-elo1] ±2.1<br><sub>WDL:&nbsp;4821,&nbsp;24696,&nbsp;10483<br>nElo: 81.68 ±3.5<br>[\[raw statistics\]][181013-raw1]</sub> |
| 2013&#8209;10&#8209;19 | [master][191013-master] vs [Stockfish 4]<br><sub>`Bench: 9160831`<br>Further increase safe checks bonus<br>[\[differences\]][191013-dif] `80`</sub> | Elo: [50.11][191013-elo1] ±2.1<br><sub>WDL:&nbsp;4817,&nbsp;24636,&nbsp;10547<br>nElo: 82.54 ±3.5<br>[\[raw statistics\]][191013-raw1]</sub> |
| 2013&#8209;10&#8209;20 | [master][201013-master] vs [Stockfish 4]<br><sub>`Bench: 9294116`<br>Further improve chain pawn evaluation<br>[\[differences\]][201013-dif] `84`</sub> | Elo: [49.72][201013-elo1] ±3.1<br><sub>WDL:&nbsp;2677,&nbsp;11803,&nbsp;5520<br>nElo: 79.12 ±4.9<br>[\[raw statistics\]][201013-raw1]</sub> |
| 2013&#8209;10&#8209;22 | [master][221013-master] vs [Stockfish 4]<br><sub>`Bench: 8455956`<br>Tweak again chain pawn bonus<br>[\[differences\]][221013-dif] `87`</sub> | Elo: [53.85][221013-elo1] ±3.0<br><sub>WDL:&nbsp;2425,&nbsp;12075,&nbsp;5500<br>nElo: 87.51 ±4.9<br>[\[raw statistics\]][221013-raw1]</sub> |
| 2013&#8209;10&#8209;24 | [master][241013-master] vs [Stockfish 4]<br><sub>`Bench: 8291883`<br>Retire mirror()<br>[\[differences\]][241013-dif] `94`</sub> | Elo: [55.18][241013-elo1] ±3.0<br><sub>WDL:&nbsp;2385,&nbsp;12080,&nbsp;5535<br>nElo: 89.82 ±4.9<br>[\[raw statistics\]][241013-raw1]</sub> |
| 2013&#8209;10&#8209;28 | [master][281013-master] vs [Stockfish 4]<br><sub>`Bench: 8029334`<br>Tweak bishop pair and knight weight<br>[\[differences\]][281013-dif] `96`</sub> | Elo: [52.84][281013-elo1] ±2.1<br><sub>WDL:&nbsp;4866,&nbsp;24231,&nbsp;10903<br>nElo: 86.04 ±3.5<br>[\[raw statistics\]][281013-raw1]</sub> |
| 2013&#8209;11&#8209;01 | [master][011113-master] vs [Stockfish 4]<br><sub>`Bench: 7995098`<br>Set timer to a fixed interval<br>[\[differences\]][011113-dif] `98`</sub> | Elo: [59.73][011113-elo1] ±3.0<br><sub>WDL:&nbsp;2324,&nbsp;11947,&nbsp;5729<br>nElo: 96.77 ±5.0<br>[\[raw statistics\]][011113-raw1]</sub> |
| 2013&#8209;11&#8209;09 | [master][091113-master] vs [Stockfish 4]<br><sub>`Bench: 7243575`<br>Futility pruning simplification<br>[\[differences\]][091113-dif] `106`</sub> | Elo: [60.68][091113-elo1] ±3.0<br><sub>WDL:&nbsp;2198,&nbsp;12146,&nbsp;5656<br>nElo: 99.73 ±5.0<br>[\[raw statistics\]][091113-raw1]</sub> |
| 2013&#8209;11&#8209;10 | [master][101113-master] vs [Stockfish 4]<br><sub>`Bench: 9282549`<br>Remove opposed flag for doubled pawns<br>[\[differences\]][101113-dif] `113`</sub> | Elo: [61.23][101113-elo1] ±2.1<br><sub>WDL:&nbsp;4333,&nbsp;24357,&nbsp;11310<br>nElo: 100.91 ±3.5<br>[\[raw statistics\]][101113-raw1]</sub> |
| 2013&#8209;11&#8209;11 | [master][111113-master] vs [Stockfish 4]<br><sub>`Bench: 8331357`<br>Simplify generate\<EVASIONS\><br>[\[differences\]][111113-dif] `116`</sub> | Elo: [63.85][111113-elo1] ±2.1<br><sub>WDL:&nbsp;4185,&nbsp;24361,&nbsp;11454<br>nElo: 105.53 ±3.5<br>[\[raw statistics\]][111113-raw1]</sub> |
| 2013&#8209;11&#8209;29 | [master][291113A-master] vs [Stockfish 4]<br><sub>`Bench: 8596156`<br>Add support for PPC 64bit on Linux<br>[\[differences\]][291113A-dif] `123`</sub> | Elo: [67.44][291113A-elo1] ±2.1<br><sub>WDL:&nbsp;4119,&nbsp;24094,&nbsp;11787<br>nElo: 110.87 ±3.5<br>[\[raw statistics\]][291113A-raw1]</sub> |
| 2013&#8209;11&#8209;29 | [Stockfish DD] [[[https://stockfishchess.org/images/logo/icon_128x128.png\|width=20px]]][SFDDRN] [[[https://github.githubassets.com/images/icons/emoji/unicode/1f4c8.png\|width=20px]]][SFDDDP]<br><sub>`Bench: 8596156`<br>[\[differences\]][291113B-dif] `124`</sub> |

</details>

<details>
  <summary><code>Stockfish 5 Development (2013-11-29 - 2014-05-31)</code></summary><br>

| `Date` | `Version` | `1 Thread` |
|:------:|:---------:|:----------:|
| 2013&#8209;12&#8209;09 | [master][091213-master] vs [Stockfish DD]<br><sub>`Bench: 7869223`<br>Research at intermediate depth if LMR is very high<br>[\[differences\]][091213-dif] `23`</sub> | Elo: [7.94][091213-elo1] ±1.9<br><sub>WDL:&nbsp;5662,&nbsp;27762,&nbsp;6576<br>nElo: 14.37 ±3.4<br>[\[raw statistics\]][091213-raw1]</sub> |
| 2013&#8209;12&#8209;19 | [master][191213-master] vs [Stockfish DD]<br><sub>`Bench: 7425809`<br>Faster and simplified threat eval<br>[\[differences\]][191213-dif] `29`</sub> | Elo: [11.35][191213-elo1] ±1.9<br><sub>WDL:&nbsp;5766,&nbsp;27162,&nbsp;7072<br>nElo: 20.06 ±3.4<br>[\[raw statistics\]][191213-raw1]</sub> |
| 2013&#8209;12&#8209;23 | [master][231213-master] vs [Stockfish DD]<br><sub>`Bench: 6835416`<br>Loosened trigger condition for king safety<br>[\[differences\]][231213-dif] `31`</sub> | Elo: [18.62][231213-elo1] ±2.0<br><sub>WDL:&nbsp;5619,&nbsp;26620,&nbsp;7761<br>nElo: 32.31 ±3.4<br>[\[raw statistics\]][231213-raw1]</sub> |
| 2013&#8209;12&#8209;29 | [master][291213-master] vs [Stockfish DD]<br><sub>`Bench: 7762310`<br>Retire asymmThreshold<br>[\[differences\]][291213-dif] `36`</sub> | Elo: [19.54][291213-elo1] ±2.0<br><sub>WDL:&nbsp;5580,&nbsp;26593,&nbsp;7827<br>nElo: 33.87 ±3.4<br>[\[raw statistics\]][291213-raw1]</sub> |
| 2014&#8209;01&#8209;02 | [master][020114-master] vs [Stockfish DD]<br><sub>`Bench: 7602383`<br>Ensure move_importance() is non-zero<br>[\[differences\]][020114-dif] `46`</sub> | Elo: [25.36][020114-elo1] ±2.0<br><sub>WDL:&nbsp;5371,&nbsp;26343,&nbsp;8286<br>nElo: 43.67 ±3.4<br>[\[raw statistics\]][020114-raw1]</sub> |
| 2014&#8209;01&#8209;08 | [master][080114-master] vs [Stockfish DD]<br><sub>`Bench: 8502826`<br>Position::gives_check - use ci.ksq<br>[\[differences\]][080114-dif] `55`</sub> | Elo: [29.85][080114-elo1] ±2.0<br><sub>WDL:&nbsp;5165,&nbsp;26242,&nbsp;8593<br>nElo: 51.32 ±3.4<br>[\[raw statistics\]][080114-raw1]</sub> |
| 2014&#8209;01&#8209;14 | [master][140114-master] vs [Stockfish DD]<br><sub>`Bench: 7205153`<br>Introduce 'follow up' moves<br>[\[differences\]][140114-dif] `59`</sub> | Elo: [29.84][140114-elo1] ±2.0<br><sub>WDL:&nbsp;5222,&nbsp;26129,&nbsp;8649<br>nElo: 51.09 ±3.4<br>[\[raw statistics\]][140114-raw1]</sub> |
| 2014&#8209;01&#8209;19 | [master][190114-master] vs [Stockfish DD]<br><sub>`Bench: 7804908`<br>Small simplification to Position::see<br>[\[differences\]][190114-dif] `64`</sub> | Elo: [32.49][190114-elo1] ±2.0<br><sub>WDL:&nbsp;5088,&nbsp;26094,&nbsp;8818<br>nElo: 55.65 ±3.4<br>[\[raw statistics\]][190114-raw1]</sub> |
| 2014&#8209;01&#8209;29 | [master][290114-master] vs [Stockfish DD]<br><sub>`Bench: 6875743`<br>Tweak bishop PSQT tables<br>[\[differences\]][290114-dif] `70`</sub> | Elo: [36.66][290114-elo1] ±2.0<br><sub>WDL:&nbsp;4905,&nbsp;25985,&nbsp;9110<br>nElo: 62.70 ±3.4<br>[\[raw statistics\]][290114-raw1]</sub> |
| 2014&#8209;02&#8209;09 | [master][090214-master] vs [Stockfish DD]<br><sub>`Bench: 8347121`<br>Faster handling of king captures in Position::see<br>[\[differences\]][090214-dif] `79`</sub> | Elo: [38.63][090214-elo1] ±2.0<br><sub>WDL:&nbsp;4956,&nbsp;25659,&nbsp;9385<br>nElo: 65.38 ±3.4<br>[\[raw statistics\]][090214-raw1]</sub> |
| 2014&#8209;02&#8209;22 | [master][220214-master] vs [Stockfish DD]<br><sub>`Bench: 8430785`<br>Fix a warning with Intel compiler<br>[\[differences\]][220214-dif] `99`</sub> | Elo: [38.93][220214-elo1] ±2.0<br><sub>WDL:&nbsp;4944,&nbsp;25649,&nbsp;9407<br>nElo: 65.87 ±3.4<br>[\[raw statistics\]][220214-raw1]</sub> |
| 2014&#8209;02&#8209;26 | [master][260214-master] vs [Stockfish DD]<br><sub>`Bench: 7990513`<br>Dynamic draw value<br>[\[differences\]][260214-dif] `100`</sub> | Elo: [39.25][260214-elo1] ±2.1<br><sub>WDL:&nbsp;5164,&nbsp;25172,&nbsp;9664<br>nElo: 65.32 ±3.4<br>[\[raw statistics\]][260214-raw1]</sub> |
| 2014&#8209;03&#8209;14 | [master][140314-master] vs [Stockfish DD]<br><sub>`Bench: 7451319`<br>Depth dependent aspiration window delta<br>[\[differences\]][140314-dif] `122`</sub> | Elo: [40.85][140314-elo1] ±2.0<br><sub>WDL:&nbsp;4925,&nbsp;25469,&nbsp;9606<br>nElo: 68.77 ±3.5<br>[\[raw statistics\]][140314-raw1]</sub> |
| 2014&#8209;03&#8209;24 | [master][240314-master] vs [Stockfish DD]<br><sub>`Bench: 7682173`<br>Simplify TT replace strategy<br>[\[differences\]][240314-dif] `138`</sub> | Elo: [43.70][240314-elo1] ±2.1<br><sub>WDL:&nbsp;4887,&nbsp;25221,&nbsp;9892<br>nElo: 73.08 ±3.5<br>[\[raw statistics\]][240314-raw1]</sub> |
| 2014&#8209;04&#8209;08 | [master][080414-master] vs [Stockfish DD]<br><sub>`Bench: 7533692`<br>Restrict queen mobility to safe squares<br>[\[differences\]][080414-dif] `159`</sub> | Elo: [47.70][080414-elo1] ±2.1<br><sub>WDL:&nbsp;4689,&nbsp;25165,&nbsp;10146<br>nElo: 79.86 ±3.5<br>[\[raw statistics\]][080414-raw1]</sub> |
| 2014&#8209;04&#8209;12 | [master][120414-master] vs [Stockfish DD]<br><sub>`Bench: 6921356`<br>Move args parsing to UCI::loop<br>[\[differences\]][120414-dif] `174`</sub> | Elo: [49.21][120414-elo1] ±2.1<br><sub>WDL:&nbsp;4717,&nbsp;24938,&nbsp;10345<br>nElo: 81.84 ±3.5<br>[\[raw statistics\]][120414-raw1]</sub> |
| 2014&#8209;04&#8209;21 | [master][210414-master] vs [Stockfish DD]<br><sub>`Bench: 7384368`<br>Reset DrawValue[] before new search<br>[\[differences\]][210414-dif] `184`</sub> | Elo: [54.53][210414-elo1] ±2.1<br><sub>WDL:&nbsp;4742,&nbsp;24289,&nbsp;10969<br>nElo: 89.09 ±3.5<br>[\[raw statistics\]][210414-raw1]</sub> |
| 2014&#8209;04&#8209;25 | [master][250414-master] vs [Stockfish DD]<br><sub>`Bench: 7905850`<br>Speed up picking of killers<br>[\[differences\]][250414-dif] `191`</sub> | Elo: [57.08][250414-elo1] ±2.2<br><sub>WDL:&nbsp;4858,&nbsp;23771,&nbsp;11371<br>nElo: 91.87 ±3.5<br>[\[raw statistics\]][250414-raw1]</sub> |
| 2014&#8209;05&#8209;04 | [master][040514-master] vs [Stockfish DD]<br><sub>`Bench: 8802105`<br>Revert dynamic contempt<br>[\[differences\]][040514-dif] `216`</sub> | Elo: [53.27][040514-elo1] ±2.2<br><sub>WDL:&nbsp;5183,&nbsp;23549,&nbsp;11268<br>nElo: 84.84 ±3.5<br>[\[raw statistics\]][040514-raw1]</sub> |
| 2014&#8209;05&#8209;13 | [master][130514-master] vs [Stockfish DD]<br><sub>`Bench: 8739659`<br>Drop to qsearch at low depth in razoring<br>[\[differences\]][130514-dif] `227`</sub> | Elo: [57.15][130514-elo1] ±1.8<br><sub>WDL:&nbsp;7289,&nbsp;35641,&nbsp;17070<br>nElo: 91.95 ±2.9<br>[\[raw statistics\]][130514-raw1]</sub> |
| 2014&#8209;05&#8209;17 | [master][170514-master] vs [Stockfish DD]<br><sub>`Bench: 8732553`<br>Fix an off-by-one bug in extract_pv_from_tt<br>[\[differences\]][170514-dif] `229`</sub> | Elo: [55.26][170514-elo1] ±2.2<br><sub>WDL:&nbsp;5108,&nbsp;23475,&nbsp;11417<br>nElo: 87.95 ±3.5<br>[\[raw statistics\]][170514-raw1]</sub> |
| 2014&#8209;05&#8209;24 | [master][240514-master] vs [Stockfish DD]<br><sub>`Bench: 7396783`<br>Fix a warning with Intel compiler<br>[\[differences\]][240514-dif] `234`</sub> | Elo: [53.28][240514-elo1] ±2.1<br><sub>WDL:&nbsp;4858,&nbsp;24198,&nbsp;10944<br>nElo: 86.68 ±3.5<br>[\[raw statistics\]][240514-raw1]</sub> |
| 2014&#8209;05&#8209;31 | [Stockfish 5] [[[https://stockfishchess.org/images/logo/icon_128x128.png\|width=20px]]][SF5RN] [[[https://github.githubassets.com/images/icons/emoji/unicode/1f4c8.png\|width=20px]]][SF5DP]<br><sub>`Bench: 8732553`<br>[\[differences\]][310514-dif] `236`</sub> |

</details>

<details>
  <summary><code>Stockfish 6 Development (2014-05-31 - 2015-01-27)</code></summary><br>

| `Date` | `Version` | `1 Thread` |
|:------:|:---------:|:----------:|
| 2014&#8209;06&#8209;03 | [master][030614-master] vs [Stockfish 5]<br><sub>`Bench: 8205159`<br>Symmetric King Safety: take 2<br>[\[differences\]][030614-dif] `8`</sub> | Elo: [5.35][030614-elo1] ±1.8<br><sub>WDL:&nbsp;5386,&nbsp;28612,&nbsp;6002<br>nElo: 10.03 ±3.4<br>[\[raw statistics\]][030614-raw1]</sub> |
| 2014&#8209;06&#8209;11 | [master][110614-master] vs [Stockfish 5]<br><sub>`Bench: 7875814`<br>Simplify pawn threats and merge into ThreatenedByPawn[]<br>[\[differences\]][110614-dif] `22`</sub> | Elo: [8.30][110614-elo1] ±2.0<br><sub>WDL:&nbsp;4589,&nbsp;24491,&nbsp;5413<br>nElo: 15.43 ±3.7<br>[\[raw statistics\]][110614-raw1]</sub> |
| 2014&#8209;06&#8209;29 | [master][290614-master] vs [Stockfish 5]<br><sub>`Bench: 8759675`<br>Fix Singular extension condition to handle mate scores<br>[\[differences\]][290614-dif] `46`</sub> | Elo: [10.78][290614-elo1] ±1.8<br><sub>WDL:&nbsp;5152,&nbsp;28455,&nbsp;6393<br>nElo: 20.10 ±3.4<br>[\[raw statistics\]][290614-raw1]</sub> |
| 2014&#8209;07&#8209;22 | [master][220714-master] vs [Stockfish 5]<br><sub>`Bench: 7831429`<br>Outpost tuning<br>[\[differences\]][220714-dif] `62`</sub> | Elo: [19.63][220714-elo1] ±1.8<br><sub>WDL:&nbsp;4775,&nbsp;28192,&nbsp;7033<br>nElo: 36.29 ±3.4<br>[\[raw statistics\]][220714-raw1]</sub> |
| 2014&#8209;08&#8209;06 | [master][060814-master] vs [Stockfish 5]<br><sub>`Bench: 7461881`<br>Remove insufficient material rule<br>[\[differences\]][060814-dif] `73`</sub> | Elo: [19.68][060814-elo1] ±1.8<br><sub>WDL:&nbsp;4737,&nbsp;28263,&nbsp;7000<br>nElo: 36.49 ±3.4<br>[\[raw statistics\]][060814-raw1]</sub> |
| 2014&#8209;09&#8209;04 | [master][040914-master] vs [Stockfish 5]<br><sub>`Bench: 7461881`<br>Small tweak to idle_loop()<br>[\[differences\]][040914-dif] `82`</sub> | Elo: [15.90][040914-elo1] ±1.8<br><sub>WDL:&nbsp;4986,&nbsp;28199,&nbsp;6815<br>nElo: 29.35 ±3.4<br>[\[raw statistics\]][040914-raw1]</sub> |
| 2014&#8209;09&#8209;27 | [master][270914-master] vs [Stockfish 5]<br><sub>`Bench: 6545733`<br>Remove use of half-ply reductions<br>[\[differences\]][270914-dif] `93`</sub> | Elo: [22.80][270914-elo1] ±1.9<br><sub>WDL:&nbsp;4664,&nbsp;28051,&nbsp;7285<br>nElo: 41.96 ±3.4<br>[\[raw statistics\]][270914-raw1]</sub> |
| 2014&#8209;10&#8209;15 | [master][151014-master] vs [Stockfish 5]<br><sub>`Bench: 7328585`<br>Document why initing eval tables<br>[\[differences\]][151014-dif] `108`</sub> | Elo: [27.58][151014-elo1] ±1.9<br><sub>WDL:&nbsp;4613,&nbsp;27605,&nbsp;7782<br>nElo: 49.96 ±3.4<br>[\[raw statistics\]][151014-raw1]</sub> |
| 2014&#8209;11&#8209;01 | [master][011114-master] vs [Stockfish 5]<br><sub>`Bench: 6564212`<br>Merge pull request #89 from official-stockfish/pull_no_pretty<br>[\[differences\]][011114-dif] `129`</sub> | Elo: [31.00][011114-elo1] ±1.9<br><sub>WDL:&nbsp;4484,&nbsp;27472,&nbsp;8044<br>nElo: 55.96 ±3.4<br>[\[raw statistics\]][011114-raw1]</sub> |
| 2014&#8209;11&#8209;10 | [master][101114-master] vs [Stockfish 5]<br><sub>`Bench: 6807896`<br>Profile Build with Hash=16<br>[\[differences\]][101114-dif] `148`</sub> | Elo: [36.21][101114-elo1] ±1.9<br><sub>WDL:&nbsp;4357,&nbsp;27132,&nbsp;8511<br>nElo: 64.71 ±3.4<br>[\[raw statistics\]][101114-raw1]</sub> |
| 2014&#8209;11&#8209;25 | [master][251114-master] vs [Stockfish 5]<br><sub>`Bench: 8255966`<br>Bitbase index() from ADD to OR<br>[\[differences\]][251114-dif] `168`</sub> | Elo: [39.02][251114-elo1] ±1.9<br><sub>WDL:&nbsp;4151,&nbsp;27225,&nbsp;8624<br>nElo: 70.14 ±3.4<br>[\[raw statistics\]][251114-raw1]</sub> |
| 2014&#8209;12&#8209;07 | [master][071214-master] vs [Stockfish 5]<br><sub>`Bench: 9324905`<br>Simpler PRNG and faster magics search<br>[\[differences\]][071214-dif] `181`</sub> | Elo: [41.42][071214-elo1] ±1.9<br><sub>WDL:&nbsp;4108,&nbsp;27038,&nbsp;8854<br>nElo: 74.04 ±3.4<br>[\[raw statistics\]][071214-raw1]</sub> |
| 2014&#8209;12&#8209;22 | [master][221214-master] vs [Stockfish 5]<br><sub>`Bench: 9498821`<br>Prefer names to numbers in storm code<br>[\[differences\]][221214-dif] `197`</sub> | Elo: [46.26][221214-elo1] ±1.9<br><sub>WDL:&nbsp;4011,&nbsp;26683,&nbsp;9306<br>nElo: 81.89 ±3.4<br>[\[raw statistics\]][221214-raw1]</sub> |
| 2015&#8209;01&#8209;07 | [master][070115-master] vs [Stockfish 5]<br><sub>`Bench: 7604776`<br>Assorted formatting and comment tweaks in position.h<br>[\[differences\]][070115-dif] `213`</sub> | Elo: [52.10][070115-elo1] ±2.0<br><sub>WDL:&nbsp;3913,&nbsp;26688,&nbsp;9948<br>nElo: 91.46 ±3.4<br>[\[raw statistics\]][070115-raw1]</sub> |
| 2015&#8209;01&#8209;18 | [master][180115-master] vs [Stockfish 5]<br><sub>`Bench: 8080602`<br>Stockfish 6 Release Candidate 1<br>[\[differences\]][180115-dif] `228`</sub> | Elo: [51.71][180115-elo1] ±1.9<br><sub>WDL:&nbsp;3723,&nbsp;26644,&nbsp;9633<br>nElo: 91.89 ±3.5<br>[\[raw statistics\]][180115-raw1]</sub> |
| 2015&#8209;01&#8209;27 | [Stockfish 6] [[[https://stockfishchess.org/images/logo/icon_128x128.png\|width=20px]]][SF6RN] [[[https://github.githubassets.com/images/icons/emoji/unicode/1f4c8.png\|width=20px]]][SF6DP]<br><sub>`Bench: 8918745`<br>[\[differences\]][270115-dif] `236`</sub> |

</details>

<details>
  <summary><code>Stockfish 7 Development (2015-01-27 - 2016-01-02)</code></summary><br>

| `Date` | `Version` | `1 Thread` |
|:------:|:---------:|:----------:|
| 2015&#8209;02&#8209;08 | [master][080215-master] vs [Stockfish 6]<br><sub>`Bench: 7699138`<br>Pawn Center Bind Bonus<br>[\[differences\]][080215-dif] `12`</sub> | Elo: [7.50][080215-elo1] ±2.0<br><sub>WDL:&nbsp;6423,&nbsp;26291,&nbsp;7286<br>nElo: 12.81 ±3.4<br>[\[raw statistics\]][080215-raw1]</sub> |
| 2015&#8209;03&#8209;19 | [master][190315-master] vs [Stockfish 6]<br><sub>`Bench: 8226843`<br>Retire ConditionVariable<br>[\[differences\]][190315-dif] `123`</sub> | Elo: [15.92][190315-elo1] ±1.8<br><sub>WDL:&nbsp;4796,&nbsp;28576,&nbsp;6628<br>nElo: 29.89 ±3.4<br>[\[raw statistics\]][190315-raw1]</sub> |
| 2015&#8209;03&#8209;29 | [master][290315-master] vs [Stockfish 6]<br><sub>`Bench: 7658627`<br>Remove some difficult to understand C++11 constructs<br>[\[differences\]][290315-dif] `137`</sub> | Elo: [19.02][290315-elo1] ±1.8<br><sub>WDL:&nbsp;4590,&nbsp;28633,&nbsp;6777<br>nElo: 35.82 ±3.4<br>[\[raw statistics\]][290315-raw1]</sub> |
| 2015&#8209;04&#8209;10 | [master][100415-master] vs [Stockfish 6]<br><sub>`Bench: 6985247`<br>Allow Position::init() to be called more than once<br>[\[differences\]][100415-dif] `151`</sub> | Elo: [22.12][100415-elo1] ±1.8<br><sub>WDL:&nbsp;4480,&nbsp;28497,&nbsp;7023<br>nElo: 41.48 ±3.4<br>[\[raw statistics\]][100415-raw1]</sub> |
| 2015&#8209;05&#8209;09 | [master][090515-master] vs [Stockfish 6]<br><sub>`Bench: 8787152`<br>Smart TT save<br>[\[differences\]][090515-dif] `164`</sub> | Elo: [28.82][090515-elo1] ±1.8<br><sub>WDL:&nbsp;4197,&nbsp;28295,&nbsp;7508<br>nElo: 53.80 ±3.4<br>[\[raw statistics\]][090515-raw1]</sub> |
| 2015&#8209;06&#8209;07 | [master][070615-master] vs [Stockfish 6]<br><sub>`Bench: 6716940`<br>Simplify outpost evaluation<br>[\[differences\]][070615-dif] `176`</sub> | Elo: [27.85][070615-elo1] ±1.9<br><sub>WDL:&nbsp;4501,&nbsp;27798,&nbsp;7701<br>nElo: 50.86 ±3.4<br>[\[raw statistics\]][070615-raw1]</sub> |
| 2015&#8209;07&#8209;16 | [master][160715-master] vs [Stockfish 6]<br><sub>`Bench: 6943812`<br>Fix formatting of previous patch<br>[\[differences\]][160715-dif] `187`</sub> | Elo: [30.74][160715-elo1] ±1.9<br><sub>WDL:&nbsp;4367,&nbsp;27736,&nbsp;7897<br>nElo: 56.09 ±3.4<br>[\[raw statistics\]][160715-raw1]</sub> |
| 2015&#8209;07&#8209;30 | [master][300715-master] vs [Stockfish 6]<br><sub>`Bench: 8040572`<br>Simplify IID depth formula<br>[\[differences\]][300715-dif] `192`</sub> | Elo: [34.04][300715-elo1] ±1.9<br><sub>WDL:&nbsp;4283,&nbsp;27527,&nbsp;8190<br>nElo: 61.72 ±3.4<br>[\[raw statistics\]][300715-raw1]</sub> |
| 2015&#8209;10&#8209;03 | [master][031015-master] vs [Stockfish 6]<br><sub>`Bench: 8073614`<br>File based passed pawn bonus<br>[\[differences\]][031015-dif] `214`</sub> | Elo: [44.23][031015-elo1] ±1.9<br><sub>WDL:&nbsp;3690,&nbsp;27555,&nbsp;8755<br>nElo: 80.99 ±3.4<br>[\[raw statistics\]][031015-raw1]</sub> |
| 2015&#8209;10&#8209;25 | [master][251015-master] vs [Stockfish 6]<br><sub>`Bench: 8004751`<br>Use atomics instead of volatile<br>[\[differences\]][251015-dif] `232`</sub> | Elo: [61.76][251015-elo1] ±1.9<br><sub>WDL:&nbsp;3197,&nbsp;26570,&nbsp;10233<br>nElo: 110.69 ±3.5<br>[\[raw statistics\]][251015-raw1]</sub> |
| 2015&#8209;12&#8209;27 | [master][271215-master] vs [Stockfish 6]<br><sub>`Bench: 8355485`<br>Stockfish 7 Beta 1<br>[\[differences\]][271215-dif] `267`</sub> | Elo: [62.62][271215-elo1] ±1.6<br><sub>WDL:&nbsp;4472,&nbsp;40358,&nbsp;15170<br>nElo: 113.94 ±2.8<br>[\[raw statistics\]][271215-raw1]</sub> |
| 2016&#8209;01&#8209;02 | [Stockfish 7] [[[https://stockfishchess.org/images/logo/icon_128x128.png\|width=20px]]][SF7RN] [[[https://github.githubassets.com/images/icons/emoji/unicode/1f4c8.png\|width=20px]]][SF7DP]<br><sub>`Bench: 8355485`<br>[\[differences\]][020116-dif] `273`</sub> |

</details>

<details>
  <summary><code>Stockfish 8 Development (2016-01-02 - 2016-11-01)</code></summary><br>

| `Date` | `Version` | `1 Thread` |
|:------:|:---------:|:----------:|
| 2016&#8209;01&#8209;28 | [master][280116-master] vs [Stockfish 7]<br><sub>`Bench: 7751425`<br>Time management simplification<br>[\[differences\]][280116-dif] `16`</sub> | Elo: [4.93][280116-elo1] ±1.5<br><sub>WDL:&nbsp;3814,&nbsp;31804,&nbsp;4382<br>nElo: 10.90 ±3.4<br>[\[raw statistics\]][280116-raw1]</sub> |
| 2016&#8209;03&#8209;10 | [master][100316-master] vs [Stockfish 7]<br><sub>`Bench: 8261839`<br>Add follow up moves history for move ordering<br>[\[differences\]][100316-dif] `28`</sub> | Elo: [12.83][100316-elo1] ±1.5<br><sub>WDL:&nbsp;3354,&nbsp;31816,&nbsp;4830<br>nElo: 28.44 ±3.4<br>[\[raw statistics\]][100316-raw1]</sub> |
| 2016&#8209;04&#8209;08 | [master][080416-master] vs [Stockfish 7]<br><sub>`Bench: 7482426`<br>Small passed pawn simplification<br>[\[differences\]][080416-dif] `42`</sub> | Elo: [15.27][080416-elo1] ±1.5<br><sub>WDL:&nbsp;3251,&nbsp;31741,&nbsp;5008<br>nElo: 33.74 ±3.4<br>[\[raw statistics\]][080416-raw1]</sub> |
| 2016&#8209;05&#8209;20 | [master][200516-master] vs [Stockfish 7]<br><sub>`Bench: 8428997`<br>More detailed dependence of time allocation<br>[\[differences\]][200516-dif] `64`</sub> | Elo: [29.44][200516-elo1] ±1.6<br><sub>WDL:&nbsp;2719,&nbsp;31217,&nbsp;6104<br>nElo: 63.61 ±3.4<br>[\[raw statistics\]][200516-raw1]</sub> |
| 2016&#8209;06&#8209;10 | [master][100616-master] vs [Stockfish 7]<br><sub>`Bench: 8276130`<br>Stat Formula Tweak<br>[\[differences\]][100616-dif] `76`</sub> | Elo: [36.29][100616-elo1] ±1.6<br><sub>WDL:&nbsp;2606,&nbsp;30625,&nbsp;6769<br>nElo: 76.48 ±3.4<br>[\[raw statistics\]][100616-raw1]</sub> |
| 2016&#8209;07&#8209;24 | [master][240716-master] vs [Stockfish 7]<br><sub>`Bench: 8145304`<br>Allow null pruning at depth 1<br>[\[differences\]][240716-dif] `94`</sub> | Elo: [49.73][240716-elo1] ±1.7<br><sub>WDL:&nbsp;2415,&nbsp;29483,&nbsp;8102<br>nElo: 100.27 ±3.4<br>[\[raw statistics\]][240716-raw1]</sub> |
| 2016&#8209;08&#8209;18 | [master][180816-master] vs [Stockfish 7]<br><sub>`Bench: 7662861`<br>Remove a stale assignment<br>[\[differences\]][180816-dif] `101`</sub> | Elo: [52.59][180816-elo1] ±1.7<br><sub>WDL:&nbsp;2413,&nbsp;29165,&nbsp;8422<br>nElo: 104.74 ±3.4<br>[\[raw statistics\]][180816-raw1]</sub> |
| 2016&#8209;09&#8209;07 | [master][070916-master] vs [Stockfish 7]<br><sub>`Bench: 6024713`<br>Refactor previous patch<br>[\[differences\]][070916-dif] `124`</sub> | Elo: [66.53][070916-elo1] ±1.8<br><sub>WDL:&nbsp;1893,&nbsp;28647,&nbsp;9460<br>nElo: 131.97 ±3.3<br>[\[raw statistics\]][070916-raw1]</sub> |
| 2016&#8209;10&#8209;07 | [master][071016-master] vs [Stockfish 7]<br><sub>`Bench: 6421663`<br>Optimisation of Position::see and Position::see_sign<br>[\[differences\]][071016-dif] `149`</sub> | Elo: [76.60][071016-elo1] ±1.8<br><sub>WDL:&nbsp;1571,&nbsp;28179,&nbsp;10250<br>nElo: 151.24 ±3.3<br>[\[raw statistics\]][071016-raw1]</sub> |
| 2016&#8209;11&#8209;01 | [Stockfish 8] [[[https://stockfishchess.org/images/logo/icon_128x128.png\|width=20px]]][SF8RN] [[[https://github.githubassets.com/images/icons/emoji/unicode/1f4c8.png\|width=20px]]][SF8DP]<br><sub>`Bench: 5926706`<br>[\[differences\]][011116-dif] `168`</sub> |

</details>

<details>
  <summary><code>Stockfish 9 Development (2016-11-01 - 2018-01-31)</code></summary><br>

| `Date` | `Version` | `1 Thread` |
|:------:|:---------:|:----------:|
| 2016&#8209;12&#8209;31 | [master][311216-master] vs [Stockfish 8]<br><sub>`Bench: 5468995`<br>Small eval cleanup and renaming<br>[\[differences\]][311216-dif] `55`</sub> | Elo: [5.21][311216-elo1] ±1.5<br><sub>WDL:&nbsp;3656,&nbsp;32088,&nbsp;4256<br>nElo: 11.72 ±3.4<br>[\[raw statistics\]][311216-raw1]</sub> |
| 2017&#8209;01&#8209;29 | [master][290117-master] vs [Stockfish 8]<br><sub>`Bench: 5941174`<br>Simplify TT penalty stat (#980)<br>[\[differences\]][290117-dif] `86`</sub> | Elo: [8.82][290117-elo1] ±1.5<br><sub>WDL:&nbsp;3580,&nbsp;31825,&nbsp;4595<br>nElo: 19.53 ±3.4<br>[\[raw statistics\]][290117-raw1]</sub> |
| 2017&#8209;03&#8209;08 | [master][080317-master] vs [Stockfish 8]<br><sub>`Bench: 5803228`<br>Helper functions to count material for both sides<br>[\[differences\]][080317-dif] `106`</sub> | Elo: [10.84][080317-elo1] ±1.6<br><sub>WDL:&nbsp;3569,&nbsp;31614,&nbsp;4817<br>nElo: 23.73 ±3.4<br>[\[raw statistics\]][080317-raw1]</sub> |
| 2017&#8209;04&#8209;20 | [master][200417-master] vs [Stockfish 8]<br><sub>`Bench: 6581936`<br>simplify logic for history based pruning<br>[\[differences\]][200417-dif] `127`</sub> | Elo: [15.17][200417-elo1] ±1.6<br><sub>WDL:&nbsp;3430,&nbsp;31395,&nbsp;5175<br>nElo: 32.82 ±3.4<br>[\[raw statistics\]][200417-raw1]</sub> |
| 2017&#8209;05&#8209;07 | [master][070517-master] vs [Stockfish 8]<br><sub>`Bench: 6107863`<br>Linear Protector bonus by distance<br>[\[differences\]][070517-dif] `144`</sub> | Elo: [20.25][070517-elo1] ±1.6<br><sub>WDL:&nbsp;3258,&nbsp;31155,&nbsp;5587<br>nElo: 43.35 ±3.4<br>[\[raw statistics\]][070517-raw1]</sub> |
| 2017&#8209;06&#8209;21 | [master][210617-master] vs [Stockfish 8]<br><sub>`Bench: 5725676`<br>Increase reduction if tt-move is a capture<br>[\[differences\]][210617-dif] `167`</sub> | Elo: [27.41][210617-elo1] ±1.6<br><sub>WDL:&nbsp;2918,&nbsp;31015,&nbsp;6067<br>nElo: 58.52 ±3.4<br>[\[raw statistics\]][210617-raw1]</sub> |
| 2017&#8209;08&#8209;26 | [master][260817-master] vs [Stockfish 8]<br><sub>`Bench: 5965302`<br>Improve multi-threaded mate finding<br>[\[differences\]][260817-dif] `218`</sub> | Elo: [29.32][260817-elo1] ±1.6<br><sub>WDL:&nbsp;2886,&nbsp;30860,&nbsp;6254<br>nElo: 62.17 ±3.4<br>[\[raw statistics\]][260817-raw1]</sub> |
| 2017&#8209;10&#8209;02 | [master][021017-master] vs [Stockfish 8]<br><sub>`Bench: 5620312`<br>Good bishops on the main diagonals<br>[\[differences\]][021017-dif] `237`</sub> | Elo: [32.61][021017-elo1] ±1.6<br><sub>WDL:&nbsp;2688,&nbsp;30881,&nbsp;6431<br>nElo: 69.44 ±3.4<br>[\[raw statistics\]][021017-raw1]</sub> |
| 2017&#8209;11&#8209;03 | [master][031117-master] vs [Stockfish 8]<br><sub>`Bench: 5536775`<br>Introduce capture history table for capture move sorting<br>[\[differences\]][031117-dif] `247`</sub> | Elo: [35.18][031117-elo1] ±1.6<br><sub>WDL:&nbsp;2682,&nbsp;30600,&nbsp;6718<br>nElo: 73.93 ±3.4<br>[\[raw statistics\]][031117-raw1]</sub> |
| 2017&#8209;12&#8209;03 | [master][031217-master] vs [Stockfish 8]<br><sub>`Bench: 5051254`<br>Use constexpr when makes sense<br>[\[differences\]][031217-dif] `261`</sub> | Elo: [43.31][031217-elo1] ±1.7<br><sub>WDL:&nbsp;2406,&nbsp;30227,&nbsp;7367<br>nElo: 90.06 ±3.3<br>[\[raw statistics\]][031217-raw1]</sub> |
| 2018&#8209;01&#8209;23 | [master][230118-master] vs [Stockfish 8]<br><sub>`Bench: 5783344`<br>Contempt 20<br>[\[differences\]][230118-dif] `286`</sub> | Elo: [57.25][230118-elo1] ±1.9<br><sub>WDL:&nbsp;2917,&nbsp;27634,&nbsp;9449<br>nElo: 106.75 ±3.4<br>[\[raw statistics\]][230118-raw1]</sub> |
| 2018&#8209;01&#8209;31 | [Stockfish 9] [[[https://stockfishchess.org/images/logo/icon_128x128.png\|width=20px]]][SF9RN] [[[https://github.githubassets.com/images/icons/emoji/unicode/1f4c8.png\|width=20px]]][SF9DP]<br><sub>`Bench: 5023629`<br>[\[differences\]][310118-dif] `291`</sub> |

</details>

<details>
  <summary><code>Stockfish 10 Development (2018-01-31 - 2018-11-29)</code></summary><br>

| `Date` | `Version` | `1 Thread` |
|:------:|:---------:|:----------:|
| 2018&#8209;02&#8209;28 | [master][280218-master] vs [Stockfish 9]<br><sub>`Bench: 5765806`<br>Reintroduce depth 2 razoring (with additional margin)<br>[\[differences\]][280218-dif] `41`</sub> | Elo: [5.16][280218-elo1] ±1.7<br><sub>WDL:&nbsp;5143,&nbsp;30105,&nbsp;5752<br>nElo: 10.02 ±3.4<br>[\[raw statistics\]][280218-raw1]</sub> |
| 2018&#8209;03&#8209;07 | [master][070318-master] vs [Stockfish 9]<br><sub>`Bench: 5544908`<br>Simplification: use Arctan for the optimism S-curve<br>[\[differences\]][070318-dif] `53`</sub> | Elo: [6.94][070318-elo1] ±1.7<br><sub>WDL:&nbsp;4813,&nbsp;29575,&nbsp;5612<br>nElo: 13.60 ±3.4<br>[\[raw statistics\]][070318-raw1]</sub> |
| 2018&#8209;03&#8209;13 | [master][130318-master] vs [Stockfish 9]<br><sub>`Bench: 5741807`<br>Use intrinsics only for LSB/MSB<br>[\[differences\]][130318-dif] `64`</sub> | Elo: [13.03][130318-elo1] ±1.7<br><sub>WDL:&nbsp;4463,&nbsp;29574,&nbsp;5963<br>nElo: 25.59 ±3.4<br>[\[raw statistics\]][130318-raw1]</sub> |
| 2018&#8209;03&#8209;26 | [master][260318-master] vs [Stockfish 9]<br><sub>`Bench: 5934103`<br>Make kingRing always 8 squares<br>[\[differences\]][260318-dif] `75`</sub> | Elo: [13.77][260318-elo1] ±1.7<br><sub>WDL:&nbsp;4339,&nbsp;29737,&nbsp;5924<br>nElo: 27.26 ±3.4<br>[\[raw statistics\]][260318-raw1]</sub> |
| 2018&#8209;04&#8209;03 | [master][030418-master] vs [Stockfish 9]<br><sub>`Bench: 4989125`<br>Remove the Queen from the mobility area of minor pieces<br>[\[differences\]][030418-dif] `92`</sub> | Elo: [16.59][030418-elo1] ±1.7<br><sub>WDL:&nbsp;4283,&nbsp;29525,&nbsp;6192<br>nElo: 32.54 ±3.4<br>[\[raw statistics\]][030418-raw1]</sub> |
| 2018&#8209;04&#8209;07 | [master][070418-master] vs [Stockfish 9]<br><sub>`Bench: 5170165`<br>Reset negative statScore on fail high<br>[\[differences\]][070418-dif] `94`</sub> | Elo: [16.63][070418-elo1] ±1.8<br><sub>WDL:&nbsp;4397,&nbsp;29293,&nbsp;6310<br>nElo: 32.25 ±3.4<br>[\[raw statistics\]][070418-raw1]</sub> |
| 2018&#8209;04&#8209;23 | [master][230418-master] vs [Stockfish 9]<br><sub>`Bench: 5549801`<br>Alternative formula for dynamic contempt<br>[\[differences\]][230418-dif] `106`</sub> | Elo: [15.90][230418-elo1] ±1.8<br><sub>WDL:&nbsp;4462,&nbsp;29247,&nbsp;6291<br>nElo: 30.76 ±3.4<br>[\[raw statistics\]][230418-raw1]</sub> |
| 2018&#8209;04&#8209;29 | [master][290418-master] vs [Stockfish 9]<br><sub>`Bench: 5254862`<br>Always scale using pawn contribution<br>[\[differences\]][290418-dif] `112`</sub> | Elo: [14.61][290418-elo1] ±1.7<br><sub>WDL:&nbsp;4430,&nbsp;29459,&nbsp;6111<br>nElo: 28.54 ±3.4<br>[\[raw statistics\]][290418-raw1]</sub> |
| 2018&#8209;05&#8209;03 | [master][030518-master] vs [Stockfish 9]<br><sub>`Bench: 5186783`<br>Tweak the connected[] array value for pawns on rank 5<br>[\[differences\]][030518-dif] `116`</sub> | Elo: [18.52][030518-elo1] ±1.8<br><sub>WDL:&nbsp;4385,&nbsp;29100,&nbsp;6515<br>nElo: 35.63 ±3.4<br>[\[raw statistics\]][030518-raw1]</sub> |
| 2018&#8209;05&#8209;13 | [master][130518-master] vs [Stockfish 9]<br><sub>`Bench: 5294316`<br>Update search.cpp<br>[\[differences\]][130518-dif] `128`</sub> | Elo: [24.92][130518-elo1] ±1.8<br><sub>WDL:&nbsp;4175,&nbsp;28786,&nbsp;7039<br>nElo: 47.42 ±3.4<br>[\[raw statistics\]][130518-raw1]</sub> |
| 2018&#8209;05&#8209;24 | [master][240518-master] vs [Stockfish 9]<br><sub>`Bench: 5167159`<br>LMR Capture Tweak<br>[\[differences\]][240518-dif] `137`</sub> | Elo: [26.72][240518-elo1] ±1.8<br><sub>WDL:&nbsp;4033,&nbsp;28864,&nbsp;7103<br>nElo: 51.08 ±3.4<br>[\[raw statistics\]][240518-raw1]</sub> |
| 2018&#8209;06&#8209;05 | [master][050618-master] vs [Stockfish 9]<br><sub>`Bench: 4326784`<br>Call cycle detection before qsearch()<br>[\[differences\]][050618-dif] `148`</sub> | Elo: [28.16][050618-elo1] ±1.8<br><sub>WDL:&nbsp;3971,&nbsp;28823,&nbsp;7206<br>nElo: 53.79 ±3.4<br>[\[raw statistics\]][050618-raw1]</sub> |
| 2018&#8209;06&#8209;11 | [master][110618-master] vs [Stockfish 9]<br><sub>`Bench: 4980482`<br>Optimize an expression in endgame.cpp<br>[\[differences\]][110618-dif] `154`</sub> | Elo: [29.72][110618-elo1] ±1.9<br><sub>WDL:&nbsp;4335,&nbsp;27917,&nbsp;7748<br>nElo: 54.60 ±3.4<br>[\[raw statistics\]][110618-raw1]</sub> |
| 2018&#8209;06&#8209;23 | [master][230618-master] vs [Stockfish 9]<br><sub>`Bench: 4557946`<br>Another set of tuned values after one million games<br>[\[differences\]][230618-dif] `162`</sub> | Elo: [31.98][230618-elo1] ±1.9<br><sub>WDL:&nbsp;4354,&nbsp;27621,&nbsp;8025<br>nElo: 58.11 ±3.4<br>[\[raw statistics\]][230618-raw1]</sub> |
| 2018&#8209;07&#8209;19 | [master][190718-master] vs [Stockfish 9]<br><sub>`Bench: 4817583`<br>Better check evasion move sorting<br>[\[differences\]][190718-dif] `179`</sub> | Elo: [36.70][190718-elo1] ±1.9<br><sub>WDL:&nbsp;4312,&nbsp;27166,&nbsp;8522<br>nElo: 65.70 ±3.4<br>[\[raw statistics\]][190718-raw1]</sub> |
| 2018&#8209;07&#8209;27 | [master][270718-master] vs [Stockfish 9]<br><sub>`Bench: 4905530`<br>Simplify cmh pruning<br>[\[differences\]][270718-dif] `199`</sub> | Elo: [37.45][270718-elo1] ±1.9<br><sub>WDL:&nbsp;4183,&nbsp;27339,&nbsp;8478<br>nElo: 67.55 ±3.4<br>[\[raw statistics\]][270718-raw1]</sub> |
| 2018&#8209;07&#8209;28 | [master][280718-master] vs [Stockfish 9]<br><sub>`Bench: 4883742`<br>Increase the mg->eg gradient for the PawnlessFlank malus<br>[\[differences\]][280718-dif] `200`</sub> | Elo: [35.84][280718-elo1] ±1.9<br><sub>WDL:&nbsp;4235,&nbsp;27418,&nbsp;8347<br>nElo: 64.78 ±3.4<br>[\[raw statistics\]][280718-raw1]</sub> |
| 2018&#8209;07&#8209;31 | [master][310718-master] vs [Stockfish 9]<br><sub>`Bench: 5591925`<br>Small tweaks to recent code changes<br>[\[differences\]][310718-dif] `203`</sub> | Elo: [37.67][310718-elo1] ±1.9<br><sub>WDL:&nbsp;4019,&nbsp;27642,&nbsp;8339<br>nElo: 68.82 ±3.4<br>[\[raw statistics\]][310718-raw1]</sub> |
| 2018&#8209;08&#8209;08 | [master][080818-master] vs [Stockfish 9]<br><sub>`Bench: 4669050`<br>First check threshold in space evaluation<br>[\[differences\]][080818-dif] `207`</sub> | Elo: [37.78][080818-elo1] ±1.9<br><sub>WDL:&nbsp;4224,&nbsp;27220,&nbsp;8556<br>nElo: 67.82 ±3.4<br>[\[raw statistics\]][080818-raw1]</sub> |
| 2018&#8209;08&#8209;12 | [master][120818-master] vs [Stockfish 9]<br><sub>`Bench: 4694813`<br>Combo of several promising parameter tweaks<br>[\[differences\]][120818-dif] `211`</sub> | Elo: [40.88][120818-elo1] ±1.9<br><sub>WDL:&nbsp;4069,&nbsp;27177,&nbsp;8754<br>nElo: 73.46 ±3.4<br>[\[raw statistics\]][120818-raw1]</sub> |
| 2018&#8209;08&#8209;14 | [master][140818-master] vs [Stockfish 9]<br><sub>`Bench: 4272361`<br>Double weight of capture history<br>[\[differences\]][140818-dif] `214`</sub> | Elo: [41.69][140818-elo1] ±1.9<br><sub>WDL:&nbsp;3942,&nbsp;27339,&nbsp;8719<br>nElo: 75.47 ±3.4<br>[\[raw statistics\]][140818-raw1]</sub> |
| 2018&#8209;08&#8209;17 | [master][170818-master] vs [Stockfish 9]<br><sub>`Bench: 4592766`<br>Use an affine formula to mix stats and eval<br>[\[differences\]][170818-dif] `217`</sub> | Elo: [43.15][170818-elo1] ±1.9<br><sub>WDL:&nbsp;3922,&nbsp;27213,&nbsp;8865<br>nElo: 77.82 ±3.4<br>[\[raw statistics\]][170818-raw1]</sub> |
| 2018&#8209;08&#8209;28 | [master][280818A-master] vs [Stockfish 9]<br><sub>`Bench: 4172767`<br>Tweak stat bonus formula<br>[\[differences\]][280818A-dif] `220`</sub> | Elo: [44.20][280818A-elo1] ±1.9<br><sub>WDL:&nbsp;3861,&nbsp;27217,&nbsp;8922<br>nElo: 79.79 ±3.4<br>[\[raw statistics\]][280818A-raw1]</sub> |
| 2018&#8209;08&#8209;28 | [master][280818B-master] vs [Stockfish 9]<br><sub>`Bench: 4413173`<br>Remove PawnsOnBothFlanks<br>[\[differences\]][280818B-dif] `225`</sub> | Elo: [42.37][280818B-elo1] ±1.9<br><sub>WDL:&nbsp;3952,&nbsp;27242,&nbsp;8806<br>nElo: 76.44 ±3.4<br>[\[raw statistics\]][280818B-raw1]</sub> |
| 2018&#8209;09&#8209;01 | [master][010918-master] vs [Stockfish 9]<br><sub>`Bench: 4609645`<br>Re-introduce "keep pawns on both flanks"<br>[\[differences\]][010918-dif] `227`</sub> | Elo: [46.46][010918-elo1] ±1.9<br><sub>WDL:&nbsp;3804,&nbsp;27075,&nbsp;9121<br>nElo: 83.56 ±3.4<br>[\[raw statistics\]][010918-raw1]</sub> |
| 2018&#8209;09&#8209;10 | [master][100918-master] vs [Stockfish 9]<br><sub>`Bench: 4248710`<br>Tweak opposite colored bishops endgame scaling<br>[\[differences\]][100918-dif] `230`</sub> | Elo: [45.47][100918-elo1] ±1.9<br><sub>WDL:&nbsp;3911,&nbsp;26973,&nbsp;9116<br>nElo: 81.36 ±3.4<br>[\[raw statistics\]][100918-raw1]</sub> |
| 2018&#8209;09&#8209;27 | [master][270918-master] vs [Stockfish 9]<br><sub>`Bench: 4059356`<br>Fix two typos in comments<br>[\[differences\]][270918-dif] `235`</sub> | Elo: [46.93][270918-elo1] ±1.9<br><sub>WDL:&nbsp;3883,&nbsp;26864,&nbsp;9253<br>nElo: 83.72 ±3.4<br>[\[raw statistics\]][270918-raw1]</sub> |
| 2018&#8209;10&#8209;14 | [master][141018-master] vs [Stockfish 9]<br><sub>`Bench: 4274207`<br>Simplify check extensions<br>[\[differences\]][141018-dif] `241`</sub> | Elo: [49.01][141018-elo1] ±1.9<br><sub>WDL:&nbsp;3783,&nbsp;26829,&nbsp;9388<br>nElo: 87.49 ±3.4<br>[\[raw statistics\]][141018-raw1]</sub> |
| 2018&#8209;10&#8209;25 | [master][251018-master] vs [Stockfish 9]<br><sub>`Bench: 3314347`<br>On main thread: reduce depth after fail high<br>[\[differences\]][251018-dif] `245`</sub> | Elo: [52.82][251018-elo1] ±1.9<br><sub>WDL:&nbsp;3514,&nbsp;26937,&nbsp;9549<br>nElo: 95.10 ±3.4<br>[\[raw statistics\]][251018-raw1]</sub> |
| 2018&#8209;11&#8209;01 | [master][011118-master] vs [Stockfish 9]<br><sub>`Bench: 3556672`<br>Fix issues from using adjustedDepth too broadly<br>[\[differences\]][011118-dif] `248`</sub> | Elo: [51.68][011118-elo1] ±1.9<br><sub>WDL:&nbsp;3581,&nbsp;26932,&nbsp;9487<br>nElo: 92.90 ±3.4<br>[\[raw statistics\]][011118-raw1]</sub> |
| 2018&#8209;11&#8209;08 | [master][081118-master] vs [Stockfish 9]<br><sub>`Bench: 3647775`<br>Update list of top CPU contributors<br>[\[differences\]][081118-dif] `254`</sub> | Elo: [50.43][081118-elo1] ±1.9<br><sub>WDL:&nbsp;3773,&nbsp;26689,&nbsp;9538<br>nElo: 89.65 ±3.5<br>[\[raw statistics\]][081118-raw1]</sub> |
| 2018&#8209;11&#8209;19 | [master][191118-master] vs [Stockfish 9]<br><sub>`Bench: 3717396`<br>Stockfish 10-beta<br>[\[differences\]][191118-dif] `267`</sub> | Elo: [53.77][191118-elo1] ±1.9<br><sub>WDL:&nbsp;3612,&nbsp;26634,&nbsp;9754<br>nElo: 95.73 ±3.5<br>[\[raw statistics\]][191118-raw1]</sub> |
| 2018&#8209;11&#8209;27 | [master][271118-master] vs [Stockfish 9]<br><sub>`Bench: 3939338`<br>Simplify casting extension<br>[\[differences\]][271118-dif] `274`</sub> | Elo: [54.21][271118-elo1] ±1.9<br><sub>WDL:&nbsp;3562,&nbsp;26685,&nbsp;9753<br>nElo: 96.75 ±3.5<br>[\[raw statistics\]][271118-raw1]</sub> |
| 2018&#8209;11&#8209;29 | [Stockfish 10] [[[https://stockfishchess.org/images/logo/icon_128x128.png\|width=20px]]][SF10RN] [[[https://github.githubassets.com/images/icons/emoji/unicode/1f4c8.png\|width=20px]]][SF10DP]<br><sub>`Bench: 3939338`<br>[\[differences\]][291118-dif] `277`</sub> |

</details>

<details>
  <summary><code>Stockfish 11 Development (2018-11-29 - 2020-01-17)</code></summary><br>

| `Date` | `Version` | `1 Thread` | `8 Threads` |
|:------:|:---------:|:----------:|:-----------:|
| 2018&#8209;12&#8209;06 | [master][061218-master] vs [Stockfish 10]<br><sub>`Bench: 3773021`<br>Revert "pseudo_legal() and MOVE_NONE"<br>[\[differences\]][061218-dif] `8`</sub> | Elo: [4.32][061218-elo1] ±1.7<br><sub>WDL:&nbsp;5033,&nbsp;29437,&nbsp;5530<br>nElo: 8.40 ±3.4<br>[\[raw statistics\]][061218-raw1]</sub> |
| 2018&#8209;12&#8209;13 | [master][131218-master] vs [Stockfish 10]<br><sub>`Bench: 3332460`<br>A combo of parameter tweaks<br>[\[differences\]][131218-dif] `16`</sub> | Elo: [8.06][131218-elo1] ±1.8<br><sub>WDL:&nbsp;5020,&nbsp;29032,&nbsp;5948<br>nElo: 15.41 ±3.4<br>[\[raw statistics\]][131218-raw1]</sub> | Elo: [12.70][131218-elo8] ±1.7<br><sub>WDL:&nbsp;4068,&nbsp;30403,&nbsp;5529<br>nElo: 25.98 ±3.4<br>[\[raw statistics\]][131218-raw8]</sub> |
| 2018&#8209;12&#8209;16 | [master][161218-master] vs [Stockfish 10]<br><sub>`Bench: 3646542`<br>Use stronglyProtected<br>[\[differences\]][161218-dif] `21`</sub> | Elo: [7.85][161218-elo1] ±1.7<br><sub>WDL:&nbsp;5107,&nbsp;30004,&nbsp;6037<br>nElo: 15.10 ±3.4<br>[\[raw statistics\]][161218-raw1]</sub> |
| 2019&#8209;01&#8209;04 | [master][040119-master] vs [Stockfish 10]<br><sub>`Bench: 3559104`<br>Check tablebase files<br>[\[differences\]][040119-dif] `40`</sub> | Elo: [7.20][040119-elo1] ±1.8<br><sub>WDL:&nbsp;5164,&nbsp;28843,&nbsp;5993<br>nElo: 13.64 ±3.4<br>[\[raw statistics\]][040119-raw1]</sub> |
| 2019&#8209;01&#8209;10 | [master][100119-master] vs [Stockfish 10]<br><sub>`Bench: 3739723`<br>Remove pvExact<br>[\[differences\]][100119-dif] `45`</sub> | Elo: [13.14][100119-elo1] ±1.8<br><sub>WDL:&nbsp;4779,&nbsp;28930,&nbsp;6291<br>nElo: 25.03 ±3.4<br>[\[raw statistics\]][100119-raw1]</sub> | Elo: [16.17][100119-elo8] ±1.7<br><sub>WDL:&nbsp;3887,&nbsp;30366,&nbsp;5747<br>nElo: 33.07 ±3.4<br>[\[raw statistics\]][100119-raw8]</sub> |
| 2019&#8209;01&#8209;22 | [master][220119-master] vs [Stockfish 10]<br><sub>`Bench: 3665090`<br>Simplify TrappedRook<br>[\[differences\]][220119-dif] `53`</sub> | Elo: [13.98][220119-elo1] ±1.8<br><sub>WDL:&nbsp;4714,&nbsp;28963,&nbsp;6323<br>nElo: 26.68 ±3.4<br>[\[raw statistics\]][220119-raw1]</sub> |
| 2019&#8209;02&#8209;03 | [master][030219-master] vs [Stockfish 10]<br><sub>`Bench: 3653942`<br>Less king danger if we have a knight<br>[\[differences\]][030219-dif] `61`</sub> | Elo: [17.71][030219-elo1] ±1.8<br><sub>WDL:&nbsp;4624,&nbsp;28715,&nbsp;6661<br>nElo: 33.46 ±3.4<br>[\[raw statistics\]][030219-raw1]</sub> | Elo: [19.77][030219-elo8] ±1.7<br><sub>WDL:&nbsp;3728,&nbsp;30270,&nbsp;6002<br>nElo: 40.32 ±3.4<br>[\[raw statistics\]][030219-raw8]</sub> |
| 2019&#8209;03&#8209;12 | [master][120319-master] vs [Stockfish 10]<br><sub>`Bench: 3318033`<br>Increase thread stack for OS X (#2035)<br>[\[differences\]][120319-dif] `80`</sub> | Elo: [16.58][120319-elo1] ±1.8<br><sub>WDL:&nbsp;4635,&nbsp;28823,&nbsp;6542<br>nElo: 31.46 ±3.4<br>[\[raw statistics\]][120319-raw1]</sub> |
| 2019&#8209;03&#8209;31 | [master][310319-master] vs [Stockfish 10]<br><sub>`Bench: 3548313`<br>Assorted trivial cleanups 3/2019 (#2030)<br>[\[differences\]][310319-dif] `91`</sub> | Elo: [16.58][310319-elo1] ±1.8<br><sub>WDL:&nbsp;4742,&nbsp;28609,&nbsp;6649<br>nElo: 31.16 ±3.4<br>[\[raw statistics\]][310319-raw1]</sub> | Elo: [24.33][310319-elo8] ±1.7<br><sub>WDL:&nbsp;3633,&nbsp;29937,&nbsp;6430<br>nElo: 48.91 ±3.4<br>[\[raw statistics\]][310319-raw8]</sub> |
| 2019&#8209;04&#8209;24 | [master][240419-master] vs [Stockfish 10]<br><sub>`Bench: 3402947`<br>Remove useless initializations (#2115)<br>[\[differences\]][240419-dif] `113`</sub> | Elo: [16.39][240419-elo1] ±1.8<br><sub>WDL:&nbsp;4634,&nbsp;28847,&nbsp;6519<br>nElo: 31.13 ±3.4<br>[\[raw statistics\]][240419-raw1]</sub> |
| 2019&#8209;05&#8209;05 | [master][050519-master] vs [Stockfish 10]<br><sub>`Bench: 3644175`<br>LMR for captures not cracking alpha<br>[\[differences\]][050519-dif] `121`</sub> | Elo: [16.65][050519-elo1] ±1.8<br><sub>WDL:&nbsp;4788,&nbsp;28508,&nbsp;6704<br>nElo: 31.17 ±3.4<br>[\[raw statistics\]][050519-raw1]</sub> |
| 2019&#8209;05&#8209;15 | [master][150519-master] vs [Stockfish 10]<br><sub>`Bench: 3824325`<br>Update failedHighCnt rule #2063<br>[\[differences\]][150519-dif] `136`</sub> | Elo: [19.76][150519-elo1] ±1.8<br><sub>WDL:&nbsp;4665,&nbsp;28397,&nbsp;6938<br>nElo: 36.86 ±3.4<br>[\[raw statistics\]][150519-raw1]</sub> | Elo: [28.93][150519-elo8] ±1.7<br><sub>WDL:&nbsp;3573,&nbsp;29531,&nbsp;6896<br>nElo: 57.18 ±3.4<br>[\[raw statistics\]][150519-raw8]</sub> |
| 2019&#8209;06&#8209;09 | [master][090619-master] vs [Stockfish 10]<br><sub>`Bench: 3424592`<br>Remove depth condition for ttPv (#2166)<br>[\[differences\]][090619-dif] `151`</sub> | Elo: [19.87][090619-elo1] ±1.9<br><sub>WDL:&nbsp;4796,&nbsp;28123,&nbsp;7081<br>nElo: 36.62 ±3.4<br>[\[raw statistics\]][090619-raw1]</sub> |
| 2019&#8209;06&#8209;20 | [master][200619-master] vs [Stockfish 10]<br><sub>`Bench: 3398333`<br>More bonus for free passed pawn<br>[\[differences\]][200619-dif] `161`</sub> | Elo: [24.06][200619-elo1] ±1.8<br><sub>WDL:&nbsp;4547,&nbsp;28140,&nbsp;7313<br>nElo: 44.48 ±3.4<br>[\[raw statistics\]][200619-raw1]</sub> | Elo: [30.76][200619-elo8] ±1.7<br><sub>WDL:&nbsp;3462,&nbsp;29544,&nbsp;6994<br>nElo: 60.92 ±3.4<br>[\[raw statistics\]][200619-raw8]</sub> |
| 2019&#8209;06&#8209;27 | [master][270619-master] vs [Stockfish 10]<br><sub>`Bench: 3633546`<br>Bonus for double attacks<br>[\[differences\]][270619-dif] `167`</sub> | Elo: [22.75][270619-elo1] ±1.9<br><sub>WDL:&nbsp;4644,&nbsp;28096,&nbsp;7260<br>nElo: 41.95 ±3.4<br>[\[raw statistics\]][270619-raw1]</sub> |
| 2019&#8209;07&#8209;11 | [master][110719-master] vs [Stockfish 10]<br><sub>`Bench: 3206912`<br>Assorted trivial cleanups June 2019<br>[\[differences\]][110719-dif] `176`</sub> | Elo: [24.39][110719-elo1] ±1.9<br><sub>WDL:&nbsp;4596,&nbsp;28005,&nbsp;7399<br>nElo: 44.83 ±3.4<br>[\[raw statistics\]][110719-raw1]</sub> |
| 2019&#8209;07&#8209;25 | [master][250719-master] vs [Stockfish 10]<br><sub>`Bench: 3935523`<br>Tweak of SEE pruning condition<br>[\[differences\]][250719-dif] `192`</sub> | Elo: [25.72][250719-elo1] ±1.9<br><sub>WDL:&nbsp;4519,&nbsp;28006,&nbsp;7475<br>nElo: 47.32 ±3.4<br>[\[raw statistics\]][250719-raw1]</sub> | Elo: [37.49][250719-elo8] ±1.7<br><sub>WDL:&nbsp;3225,&nbsp;29251,&nbsp;7524<br>nElo: 73.63 ±3.4<br>[\[raw statistics\]][250719-raw8]</sub> |
| 2019&#8209;08&#8209;14 | [master][140819-master] vs [Stockfish 10]<br><sub>`Bench: 4139590`<br>Tweak unsafe checks<br>[\[differences\]][140819-dif] `198`</sub> | Elo: [32.24][140819-elo1] ±1.9<br><sub>WDL:&nbsp;4168,&nbsp;27963,&nbsp;7869<br>nElo: 59.45 ±3.4<br>[\[raw statistics\]][140819-raw1]</sub> |
| 2019&#8209;08&#8209;26 | [master][260819-master] vs [Stockfish 10]<br><sub>`Bench: 3568210`<br>Tweak Late Move Reduction at root<br>[\[differences\]][260819-dif] `207`</sub> | Elo: [35.63][260819-elo1] ±1.9<br><sub>WDL:&nbsp;4021,&nbsp;27870,&nbsp;8109<br>nElo: 65.62 ±3.4<br>[\[raw statistics\]][260819-raw1]</sub> | Elo: [44.52][260819-elo8] ±1.8<br><sub>WDL:&nbsp;2958,&nbsp;28986,&nbsp;8056<br>nElo: 86.99 ±3.4<br>[\[raw statistics\]][260819-raw8]</sub> |
| 2019&#8209;09&#8209;12 | [master][120919-master] vs [Stockfish 10]<br><sub>`Bench: 3954190`<br>Scale down complexity<br>[\[differences\]][120919-dif] `211`</sub> | Elo: [39.10][120919-elo1] ±1.9<br><sub>WDL:&nbsp;3824,&nbsp;27869,&nbsp;8307<br>nElo: 72.22 ±3.4<br>[\[raw statistics\]][120919-raw1]</sub> |
| 2019&#8209;09&#8209;16 | [master][160919-master] vs [Stockfish 10]<br><sub>`Bench: 4272173`<br>Raise stack size to 8MB for pthreads<br>[\[differences\]][160919-dif] `218`</sub> | Elo: [37.63][160919-elo1] ±1.9<br><sub>WDL:&nbsp;4007,&nbsp;27670,&nbsp;8323<br>nElo: 68.83 ±3.4<br>[\[raw statistics\]][160919-raw1]</sub> | Elo: [46.57][160919-elo8] ±1.8<br><sub>WDL:&nbsp;2764,&nbsp;28492,&nbsp;7994<br>nElo: 91.44 ±3.4<br>[\[raw statistics\]][160919-raw8]</sub> |
| 2019&#8209;09&#8209;24 | [master][240919-master] vs [Stockfish 10]<br><sub>`Bench: 3618154`<br>Increase weight for supported pawns<br>[\[differences\]][240919-dif] `226`</sub> | Elo: [38.97][240919-elo1] ±1.9<br><sub>WDL:&nbsp;3857,&nbsp;27818,&nbsp;8325<br>nElo: 71.81 ±3.4<br>[\[raw statistics\]][240919-raw1]</sub> |
| 2019&#8209;10&#8209;05 | [master][051019-master] vs [Stockfish 10]<br><sub>`Bench: 4131643`<br>Introduce separate counter-move tables<br>[\[differences\]][051019-dif] `239`</sub> | Elo: [41.96][051019-elo1] ±1.9<br><sub>WDL:&nbsp;3746,&nbsp;27701,&nbsp;8553<br>nElo: 77.13 ±3.4<br>[\[raw statistics\]][051019-raw1]</sub> | Elo: [51.76][051019-elo8] ±1.8<br><sub>WDL:&nbsp;2628,&nbsp;28829,&nbsp;8543<br>nElo: 101.26 ±3.4<br>[\[raw statistics\]][051019-raw8]</sub> |
| 2019&#8209;10&#8209;18 | [master][181019-master] vs [Stockfish 10]<br><sub>`Bench: 4423737`<br>Current capture for Counter-Move history<br>[\[differences\]][181019-dif] `247`</sub> | Elo: [44.63][181019-elo1] ±1.9<br><sub>WDL:&nbsp;3641,&nbsp;27608,&nbsp;8751<br>nElo: 81.93 ±3.4<br>[\[raw statistics\]][181019-raw1]</sub> |
| 2019&#8209;11&#8209;04 | [master][041119-master] vs [Stockfish 10]<br><sub>`Bench: 4707799`<br>Rook PSQT Tuned<br>[\[differences\]][041119-dif] `259`</sub> | Elo: [42.20][041119-elo1] ±1.9<br><sub>WDL:&nbsp;3686,&nbsp;27793,&nbsp;8521<br>nElo: 77.91 ±3.4<br>[\[raw statistics\]][041119-raw1]</sub> | Elo: [52.90][041119-elo8] ±1.8<br><sub>WDL:&nbsp;2601,&nbsp;28754,&nbsp;8645<br>nElo: 103.29 ±3.4<br>[\[raw statistics\]][041119-raw8]</sub> |
| 2019&#8209;11&#8209;14 | [master][141119-master] vs [Stockfish 10]<br><sub>`Bench: 4532366`<br>Prune before extension<br>[\[differences\]][141119-dif] `266`</sub> | Elo: [43.12][141119-elo1] ±1.9<br><sub>WDL:&nbsp;3676,&nbsp;27709,&nbsp;8615<br>nElo: 79.39 ±3.4<br>[\[raw statistics\]][141119-raw1]</sub> |
| 2019&#8209;11&#8209;21 | [master][211119-master] vs [Stockfish 10]<br><sub>`Bench: 5067870`<br>Do lmr for more captures<br>[\[differences\]][211119-dif] `271`</sub> | Elo: [46.56][211119-elo1] ±1.5<br><sub>WDL:&nbsp;5306,&nbsp;41395,&nbsp;13299<br>nElo: 85.60 ±2.8<br>[\[raw statistics\]][211119-raw1]</sub> | Elo: [53.93][211119-elo8] ±1.8<br><sub>WDL:&nbsp;2502,&nbsp;28837,&nbsp;8661<br>nElo: 105.86 ±3.4<br>[\[raw statistics\]][211119-raw8]</sub> |
| 2019&#8209;12&#8209;02 | [master][021219-master] vs [Stockfish 10]<br><sub>`Bench: 5122362`<br>UnblockedStorm tuned<br>[\[differences\]][021219-dif] `278`</sub> | Elo: [44.88][021219-elo1] ±1.5<br><sub>WDL:&nbsp;5273,&nbsp;41746,&nbsp;12981<br>nElo: 83.21 ±2.8<br>[\[raw statistics\]][021219-raw1]</sub> |
| 2019&#8209;12&#8209;10 | [master][101219-master] vs [Stockfish 10]<br><sub>`Bench: 5371271`<br>Refine improving-logic<br>[\[differences\]][101219-dif] `288`</sub> | Elo: [47.27][101219-elo1] ±1.5<br><sub>WDL:&nbsp;5329,&nbsp;41229,&nbsp;13442<br>nElo: 86.56 ±2.8<br>[\[raw statistics\]][101219-raw1]</sub> | Elo: [56.62][101219-elo8] ±1.8<br><sub>WDL:&nbsp;2365,&nbsp;28809,&nbsp;8826<br>nElo: 111.42 ±3.4<br>[\[raw statistics\]][101219-raw8]</sub> |
| 2020&#8209;01&#8209;07 | [master][070120-master] vs [Stockfish 10]<br><sub>`Bench: 4747984`<br>Tuned nullmove search<br>[\[differences\]][070120-dif] `294`</sub> | Elo: [51.50][070120-elo1] ±1.5<br><sub>Ptnml:&nbsp;160,&nbsp;3173,&nbsp;15729,&nbsp;9546,&nbsp;1387<br>nElo: 98.05 ±2.8<br>PairsRatio: 3.28<br>[\[raw statistics\]][070120-raw1]</sub> | Elo: [58.15][070120-elo8] ±1.7<br><sub>Ptnml:&nbsp;36,&nbsp;1527,&nbsp;11059,&nbsp;6509,&nbsp;860<br>nElo: 118.69 ±3.4<br>PairsRatio: 4.71<br>[\[raw statistics\]][070120-raw8]</sub> |
| 2020&#8209;01&#8209;17 | [master][170120-master] vs [Stockfish 10]<br><sub>`Bench: 5156767`<br>Stockfish 11<br>[\[differences\]][170120-dif] `307`</sub> | Elo: [53.59][170120-elo1] ±1.5<br><sub>Ptnml:&nbsp;138,&nbsp;2988,&nbsp;15833,&nbsp;9631,&nbsp;1407<br>nElo: 102.99 ±2.8<br>PairsRatio: 3.53<br>[\[raw statistics\]][170120-raw1]</sub> | Elo: [58.07][170120-elo8] ±1.7<br><sub>Ptnml:&nbsp;36,&nbsp;1478,&nbsp;11159,&nbsp;6463,&nbsp;854<br>nElo: 119.25 ±3.4<br>PairsRatio: 4.83<br>[\[raw statistics\]][170120-raw8]</sub> |
| 2020&#8209;01&#8209;17 | [Stockfish 11] [[[https://stockfishchess.org/images/logo/icon_128x128.png\|width=20px]]][SF11RN] [[[https://github.githubassets.com/images/icons/emoji/unicode/1f4c8.png\|width=20px]]][SF11DP]<br><sub>`Bench: 5156767`<br>[\[differences\]][170120-dif] `307`</sub> |

</details>

<details>
  <summary><code>Stockfish 12 Development (2020-01-17 - 2020-09-02)</code></summary><br>

| `Date` | `Version` | `1 Thread` | `8 Threads` |
|:------:|:---------:|:----------:|:-----------:|
| 2020&#8209;01&#8209;28 | [master][280120-master] vs [Stockfish 11]<br><sub>`Bench: 5545845`<br>More bonus for bestMoves<br>[\[differences\]][280120-dif] `16`</sub> | Elo: [-2.47][280120-elo1] ±1.3<br><sub>Ptnml:&nbsp;330,&nbsp;5657,&nbsp;18424,&nbsp;5285,&nbsp;303<br>nElo: -5.21 ±2.8<br>PairsRatio: 0.93<br>[\[raw statistics\]][280120-raw1]</sub> |
| 2020&#8209;01&#8209;31 | [master][310120-master] vs [Stockfish 11]<br><sub>`Bench: 5153165`<br>Revert 5 recent patches<br>[\[differences\]][310120-dif] `19`</sub> | Elo: [0.85][310120-elo1] ±1.3<br><sub>Ptnml:&nbsp;306,&nbsp;5327,&nbsp;18593,&nbsp;5457,&nbsp;314<br>nElo: 1.80 ±2.8<br>PairsRatio: 1.02<br>[\[raw statistics\]][310120-raw1]</sub> |
| 2020&#8209;02&#8209;27 | [master][270220-master] vs [Stockfish 11]<br><sub>`Bench: 4923286`<br>Weak queen protection<br>[\[differences\]][270220-dif] `32`</sub> | Elo: [1.33][270220-elo1] ±1.3<br><sub>Ptnml:&nbsp;327,&nbsp;5308,&nbsp;18486,&nbsp;5567,&nbsp;312<br>nElo: 2.80 ±2.8<br>PairsRatio: 1.04<br>[\[raw statistics\]][270220-raw1]</sub> | Elo: [0.51][270220-elo8] ±1.4<br><sub>Ptnml:&nbsp;118,&nbsp;3072,&nbsp;13560,&nbsp;3133,&nbsp;117<br>nElo: 1.21 ±3.4<br>PairsRatio: 1.02<br>[\[raw statistics\]][270220-raw8]</sub> |
| 2020&#8209;03&#8209;20 | [master][200320-master] vs [Stockfish 11]<br><sub>`Bench: 5398277`<br>Adjust singular extension search depth<br>[\[differences\]][200320-dif] `48`</sub> | Elo: [2.94][200320-elo1] ±1.3<br><sub>Ptnml:&nbsp;351,&nbsp;5099,&nbsp;18580,&nbsp;5631,&nbsp;339<br>nElo: 6.21 ±2.8<br>PairsRatio: 1.10<br>[\[raw statistics\]][200320-raw1]</sub> |
| 2020&#8209;04&#8209;07 | [master][070420-master] vs [Stockfish 11]<br><sub>`Bench: 4417023`<br>Introduce capture history pruning<br>[\[differences\]][070420-dif] `63`</sub> | Elo: [5.74][070420-elo1] ±1.3<br><sub>Ptnml:&nbsp;274,&nbsp;5058,&nbsp;18460,&nbsp;5818,&nbsp;390<br>nElo: 12.11 ±2.8<br>PairsRatio: 1.16<br>[\[raw statistics\]][070420-raw1]</sub> | Elo: [6.49][070420-elo8] ±1.5<br><sub>Ptnml:&nbsp;113,&nbsp;2854,&nbsp;13369,&nbsp;3501,&nbsp;163<br>nElo: 15.05 ±3.4<br>PairsRatio: 1.23<br>[\[raw statistics\]][070420-raw8]</sub> |
| 2020&#8209;04&#8209;16 | [master][160420-master] vs [Stockfish 11]<br><sub>`Bench: 4958027`<br>Remove one condition in probcut TTmove<br>[\[differences\]][160420-dif] `76`</sub> | Elo: [11.33][160420-elo1] ±1.3<br><sub>Ptnml:&nbsp;281,&nbsp;4681,&nbsp;18282,&nbsp;6313,&nbsp;443<br>nElo: 23.65 ±2.8<br>PairsRatio: 1.36<br>[\[raw statistics\]][160420-raw1]</sub> |
| 2020&#8209;05&#8209;02 | [master][020520-master] vs [Stockfish 11]<br><sub>`Bench: 4247490`<br>Fishtest Tuning Framework<br>[\[differences\]][020520-dif] `84`</sub> | Elo: [15.21][020520-elo1] ±1.3<br><sub>Ptnml:&nbsp;236,&nbsp;4370,&nbsp;18388,&nbsp;6545,&nbsp;461<br>nElo: 32.08 ±2.8<br>PairsRatio: 1.52<br>[\[raw statistics\]][020520-raw1]</sub> | Elo: [16.71][020520-elo8] ±1.5<br><sub>Ptnml:&nbsp;105,&nbsp;2457,&nbsp;13100,&nbsp;4087,&nbsp;251<br>nElo: 37.85 ±3.4<br>PairsRatio: 1.69<br>[\[raw statistics\]][020520-raw8]</sub> |
| 2020&#8209;05&#8209;21 | [master][210520-master] vs [Stockfish 11]<br><sub>`Bench: 4778956`<br>Tweak knight mobility<br>[\[differences\]][210520-dif] `100`</sub> | Elo: [15.97][210520-elo1] ±1.3<br><sub>Ptnml:&nbsp;230,&nbsp;4544,&nbsp;17963,&nbsp;6766,&nbsp;497<br>nElo: 33.08 ±2.8<br>PairsRatio: 1.52<br>[\[raw statistics\]][210520-raw1]</sub> |
| 2020&#8209;06&#8209;06 | [master][060620-master] vs [Stockfish 11]<br><sub>`Bench: 4582693`<br>Use lowply-history also on low depths<br>[\[differences\]][060620-dif] `117`</sub> | Elo: [19.45][060620-elo1] ±1.4<br><sub>Ptnml:&nbsp;250,&nbsp;4360,&nbsp;17761,&nbsp;7042,&nbsp;587<br>nElo: 39.70 ±2.8<br>PairsRatio: 1.65<br>[\[raw statistics\]][060620-raw1]</sub> | Elo: [23.70][060620-elo8] ±1.5<br><sub>Ptnml:&nbsp;88,&nbsp;2142,&nbsp;12987,&nbsp;4524,&nbsp;259<br>nElo: 53.99 ±3.4<br>PairsRatio: 2.14<br>[\[raw statistics\]][060620-raw8]</sub> |
| 2020&#8209;06&#8209;13 | [master][130620-master] vs [Stockfish 11]<br><sub>`Bench: 4246971`<br>Tuned values for search constants<br>[\[differences\]][130620-dif] `127`</sub> | Elo: [20.91][130620-elo1] ±1.4<br><sub>Ptnml:&nbsp;195,&nbsp;4263,&nbsp;17878,&nbsp;7069,&nbsp;595<br>nElo: 43.14 ±2.8<br>PairsRatio: 1.72<br>[\[raw statistics\]][130620-raw1]</sub> | Elo: [24.86][130620-elo8] ±1.5<br><sub>Ptnml:&nbsp;81,&nbsp;2088,&nbsp;13016,&nbsp;4523,&nbsp;292<br>nElo: 56.58 ±3.4<br>PairsRatio: 2.22<br>[\[raw statistics\]][130620-raw8]</sub> |
| 2020&#8209;06&#8209;29 | [master][290620-master] vs [Stockfish 11]<br><sub>`Bench: 4523573`<br>Tweak single queen endgame scaling<br>[\[differences\]][290620-dif] `148`</sub> | Elo: [25.67][290620-elo1] ±1.3<br><sub>Ptnml:&nbsp;192,&nbsp;3878,&nbsp;17888,&nbsp;7397,&nbsp;645<br>nElo: 53.10 ±2.8<br>PairsRatio: 1.98<br>[\[raw statistics\]][290620-raw1]</sub> |
| 2020&#8209;07&#8209;17 | [master][170720-master] vs [Stockfish 11]<br><sub>`Bench: 4578298`<br>Do not overwrite valuable TT data<br>[\[differences\]][170720-dif] `163`</sub> | Elo: [26.44][170720-elo1] ±1.3<br><sub>Ptnml:&nbsp;192,&nbsp;3800,&nbsp;17928,&nbsp;7418,&nbsp;662<br>nElo: 54.75 ±2.8<br>PairsRatio: 2.02<br>[\[raw statistics\]][170720-raw1]</sub> | Elo: [30.71][170720-elo8] ±1.5<br><sub>Ptnml:&nbsp;63,&nbsp;1923,&nbsp;12759,&nbsp;4935,&nbsp;320<br>nElo: 69.50 ±3.4<br>PairsRatio: 2.65<br>[\[raw statistics\]][170720-raw8]</sub> |
| 2020&#8209;07&#8209;31 | [master][310720-master] vs [Stockfish 11]<br><sub>`Bench: 4746616`<br>Tweak cutnode reduction<br>[\[differences\]][310720-dif] `167`</sub> | Elo: [25.49][310720-elo1] ±1.4<br><sub>Ptnml:&nbsp;203,&nbsp;3910,&nbsp;17861,&nbsp;7342,&nbsp;684<br>nElo: 52.38 ±2.8<br>PairsRatio: 1.95<br>[\[raw statistics\]][310720-raw1]</sub> | Elo: [32.39][310720-elo8] ±1.5<br><sub>Ptnml:&nbsp;69,&nbsp;1829,&nbsp;12779,&nbsp;4961,&nbsp;362<br>nElo: 73.03 ±3.4<br>PairsRatio: 2.80<br>[\[raw statistics\]][310720-raw8]</sub> |
| 2020&#8209;08&#8209;06 | [master][060820-master] vs [Stockfish 11]<br><sub>`Bench: 4746616`<br>Add NNUE evaluation<br>[\[differences\]][060820-dif] `168`</sub> | Elo: [83.42][060820-elo1] ±1.7<br><sub>Ptnml:&nbsp;172,&nbsp;2656,&nbsp;12724,&nbsp;11761,&nbsp;2687<br>nElo: 144.72 ±3.0<br>PairsRatio: 5.11<br>[\[raw statistics\]][060820-raw1]</sub> | Elo: [86.10][060820-elo8] ±1.9<br><sub>Ptnml:&nbsp;36,&nbsp;1192,&nbsp;9342,&nbsp;7881,&nbsp;1549<br>nElo: 163.20 ±3.6<br>PairsRatio: 7.68<br>[\[raw statistics\]][060820-raw8]</sub> |
| 2020&#8209;08&#8209;07 | [Add NNUE evaluation][060820-master] [[[https://stockfishchess.org/images/logo/icon_128x128.png\|width=20px]]][SFNNUERN]<br><sub>`Bench: 4746616`<br>[\[differences\]][070820-dif] `168`</sub> |
| 2020&#8209;08&#8209;08 | [master][080820-master] vs [Stockfish 11]<br><sub>`Bench: 4084753`<br>LMR search tweak<br>[\[differences\]][080820-dif] `185`</sub> | Elo: [106.20][080820-elo1] ±1.7<br><sub>Ptnml:&nbsp;67,&nbsp;1716,&nbsp;11867,&nbsp;13060,&nbsp;3290<br>nElo: 189.91 ±3.2<br>PairsRatio: 9.17<br>[\[raw statistics\]][080820-raw1]</sub> |
| 2020&#8209;08&#8209;11 | [master][110820-master] vs [Stockfish 11]<br><sub>`Bench: 4290577`<br>This commit enables a mixed bench<br>[\[differences\]][110820-dif] `205`</sub> | Elo: [125.60][110820-elo1] ±1.7<br><sub>Ptnml:&nbsp;48,&nbsp;1240,&nbsp;10613,&nbsp;14070,&nbsp;4029<br>nElo: 224.82 ±3.3<br>PairsRatio: 14.05<br>[\[raw statistics\]][110820-raw1]</sub> | Elo: [111.78][110820-elo8] ±1.9<br><sub>Ptnml:&nbsp;11,&nbsp;591,&nbsp;8286,&nbsp;9168,&nbsp;1944<br>nElo: 217.93 ±3.8<br>PairsRatio: 18.46<br>[\[raw statistics\]][110820-raw8]</sub> |
| 2020&#8209;08&#8209;18 | [master][180820-master] vs [Stockfish 11]<br><sub>`Bench: 4026216`<br>Fix Makefile typo<br>[\[differences\]][180820-dif] `226`</sub> | Elo: [121.54][180820-elo1] ±1.7<br><sub>Ptnml:&nbsp;52,&nbsp;1373,&nbsp;10930,&nbsp;13640,&nbsp;4005<br>nElo: 215.22 ±3.3<br>PairsRatio: 12.38<br>[\[raw statistics\]][180820-raw1]</sub> | Elo: [111.40][180820-elo8] ±1.9<br><sub>Ptnml:&nbsp;20,&nbsp;700,&nbsp;8128,&nbsp;9161,&nbsp;1991<br>nElo: 213.20 ±3.8<br>PairsRatio: 15.49<br>[\[raw statistics\]][180820-raw8]</sub> |
| 2020&#8209;08&#8209;30 | [master][300820-master] vs [Stockfish 11]<br><sub>`Bench: 3736029`<br>Update parameters in classical evaluation<br>[\[differences\]][300820-dif] `255`</sub> | Elo: [130.96][300820-elo1] ±1.7<br><sub>Ptnml:&nbsp;44,&nbsp;1161,&nbsp;10305,&nbsp;14128,&nbsp;4362<br>nElo: 232.58 ±3.4<br>PairsRatio: 15.34<br>[\[raw statistics\]][300820-raw1]</sub> |
| 2020&#8209;09&#8209;02 | [master][020920-master] vs [Stockfish 11]<br><sub>`Bench: 3624569`<br>Stockfish 12<br>[\[differences\]][020920-dif] `262`</sub> | Elo: [133.65][020920-elo1] ±1.7<br><sub>Ptnml:&nbsp;32,&nbsp;1088,&nbsp;10158,&nbsp;14286,&nbsp;4436<br>nElo: 238.67 ±3.4<br>PairsRatio: 16.72<br>[\[raw statistics\]][020920-raw1]</sub> | Elo: [117.62][020920-elo8] ±1.9<br><sub>Ptnml:&nbsp;10,&nbsp;562,&nbsp;8016,&nbsp;9195,&nbsp;2217<br>nElo: 224.93 ±3.8<br>PairsRatio: 19.95<br>[\[raw statistics\]][020920-raw8]</sub> |
| 2020&#8209;09&#8209;02 | [Stockfish 12] [[[https://stockfishchess.org/images/logo/icon_128x128.png\|width=20px]]][SF12RN] [[[https://github.githubassets.com/images/icons/emoji/unicode/1f4c8.png\|width=20px]]][SF12DP]<br><sub>`Bench: 3624569`<br>[\[differences\]][020920-dif] `262`</sub> |

</details>

<details>
  <summary><code>Stockfish 13 Development (2020-09-02 - 2021-02-18)</code></summary><br>

| `Date` | `Version` | `1 Thread` | `8 Threads` |
|:------:|:---------:|:----------:|:-----------:|
| 2020&#8209;09&#8209;08 | [master][080920-master] vs [Stockfish 12]<br><sub>`Bench: 4161067`<br>Double probability of using classical eval<br>[\[differences\]][080920-dif] `10`</sub> | Elo: [6.49][080920-elo1] ±1.0<br><sub>Ptnml:&nbsp;85,&nbsp;3319,&nbsp;22112,&nbsp;4359,&nbsp;125<br>nElo: 17.26 ±2.8<br>PairsRatio: 1.32<br>[\[raw statistics\]][080920-raw1]</sub> |
| 2020&#8209;09&#8209;21 | [master][210920-master] vs [Stockfish 12]<br><sub>`Bench: 3973739`<br>Add large page support for NNUE weights<br>[\[differences\]][210920-dif] `21`</sub> | Elo: [13.88][210920-elo1] ±1.0<br><sub>Ptnml:&nbsp;49,&nbsp;2767,&nbsp;22106,&nbsp;4896,&nbsp;182<br>nElo: 37.07 ±2.8<br>PairsRatio: 1.80<br>[\[raw statistics\]][210920-raw1]</sub> | Elo: [8.97][210920-elo8] ±1.1<br><sub>Ptnml:&nbsp;15,&nbsp;1474,&nbsp;16020,&nbsp;2445,&nbsp;46<br>nElo: 27.99 ±3.4<br>PairsRatio: 1.67<br>[\[raw statistics\]][210920-raw8]</sub> |
| 2020&#8209;09&#8209;28 | [master][280920-master] vs [Stockfish 12]<br><sub>`Bench: 3776081`<br>Include pawns in NNUE scaling<br>[\[differences\]][280920-dif] `33`</sub> | Elo: [23.15][280920-elo1] ±1.0<br><sub>Ptnml:&nbsp;38,&nbsp;1945,&nbsp;22217,&nbsp;5587,&nbsp;213<br>nElo: 63.29 ±2.7<br>PairsRatio: 2.92<br>[\[raw statistics\]][280920-raw1]</sub> |
| 2020&#8209;10&#8209;18 | [master][181020-master] vs [Stockfish 12]<br><sub>`Bench: 4066972`<br>Do more reductions for late quiet moves<br>[\[differences\]][181020-dif] `41`</sub> | Elo: [24.09][181020-elo1] ±1.0<br><sub>Ptnml:&nbsp;43,&nbsp;2023,&nbsp;21889,&nbsp;5827,&nbsp;218<br>nElo: 64.60 ±2.7<br>PairsRatio: 2.93<br>[\[raw statistics\]][181020-raw1]</sub> | Elo: [21.17][181020-elo8] ±1.1<br><sub>Ptnml:&nbsp;12,&nbsp;908,&nbsp;15789,&nbsp;3216,&nbsp;75<br>nElo: 65.43 ±3.2<br>PairsRatio: 3.58<br>[\[raw statistics\]][181020-raw8]</sub> |
| 2020&#8209;11&#8209;01 | [master][011120-master] vs [Stockfish 12]<br><sub>`Bench: 3517795`<br>Update default net to nn-cb26f10b1fd9.nnue<br>[\[differences\]][011120-dif] `48`</sub> | Elo: [28.02][011120-elo1] ±1.1<br><sub>Ptnml:&nbsp;63,&nbsp;2079,&nbsp;21107,&nbsp;6469,&nbsp;282<br>nElo: 71.59 ±2.7<br>PairsRatio: 3.15<br>[\[raw statistics\]][011120-raw1]</sub> |
| 2020&#8209;11&#8209;15 | [master][151120-master] vs [Stockfish 12]<br><sub>`Bench: 3597730`<br>Rook Mobility Tweak<br>[\[differences\]][151120-dif] `60`</sub> | Elo: [29.99][151120-elo1] ±1.0<br><sub>Ptnml:&nbsp;32,&nbsp;1667,&nbsp;21658,&nbsp;6389,&nbsp;254<br>nElo: 80.38 ±2.7<br>PairsRatio: 3.91<br>[\[raw statistics\]][151120-raw1]</sub> | Elo: [25.49][151120-elo8] ±1.1<br><sub>Ptnml:&nbsp;10,&nbsp;799,&nbsp;15532,&nbsp;3570,&nbsp;89<br>nElo: 77.27 ±3.2<br>PairsRatio: 4.52<br>[\[raw statistics\]][151120-raw8]</sub> |
| 2020&#8209;11&#8209;29 | [master][291120-master] vs [Stockfish 12]<br><sub>`Bench: 3561701`<br>Update default net to nn-62ef826d1a6d.nnue<br>[\[differences\]][291120-dif] `72`</sub> | Elo: [30.61][291120-elo1] ±1.0<br><sub>Ptnml:&nbsp;19,&nbsp;1645,&nbsp;21655,&nbsp;6407,&nbsp;274<br>nElo: 82.09 ±2.7<br>PairsRatio: 4.02<br>[\[raw statistics\]][291120-raw1]</sub> |
| 2020&#8209;12&#8209;14 | [master][141220-master] vs [Stockfish 12]<br><sub>`Bench: 4050630`<br>Increase reduction in case of stable best move<br>[\[differences\]][141220-dif] `79`</sub> | Elo: [32.09][141220-elo1] ±1.0<br><sub>Ptnml:&nbsp;33,&nbsp;1581,&nbsp;21474,&nbsp;6651,&nbsp;261<br>nElo: 85.57 ±2.7<br>PairsRatio: 4.28<br>[\[raw statistics\]][141220-raw1]</sub> | Elo: [27.50][141220-elo8] ±1.1<br><sub>Ptnml:&nbsp;10,&nbsp;706,&nbsp;15480,&nbsp;3723,&nbsp;81<br>nElo: 83.75 ±3.1<br>PairsRatio: 5.31<br>[\[raw statistics\]][141220-raw8]</sub> |
| 2020&#8209;12&#8209;31 | [master][311220-master] vs [Stockfish 12]<br><sub>`Bench: 4109336`<br>WeakUnopposed penalty for backwards<br>[\[differences\]][311220-dif] `89`</sub> | Elo: [33.71][311220-elo1] ±1.0<br><sub>Ptnml:&nbsp;23,&nbsp;1475,&nbsp;21475,&nbsp;6730,&nbsp;297<br>nElo: 90.01 ±2.6<br>PairsRatio: 4.69<br>[\[raw statistics\]][311220-raw1]</sub> |
| 2021&#8209;01&#8209;13 | [master][130121-master] vs [Stockfish 12]<br><sub>`Bench: 4287509`<br>Optimize generate_moves<br>[\[differences\]][130121-dif] `101`</sub> | Elo: [32.40][130121-elo1] ±1.0<br><sub>Ptnml:&nbsp;31,&nbsp;1487,&nbsp;21588,&nbsp;6660,&nbsp;234<br>nElo: 87.55 ±2.7<br>PairsRatio: 4.54<br>[\[raw statistics\]][130121-raw1]</sub> | Elo: [28.29][130121-elo8] ±1.1<br><sub>Ptnml:&nbsp;10,&nbsp;671,&nbsp;15468,&nbsp;3761,&nbsp;90<br>nElo: 86.06 ±3.1<br>PairsRatio: 5.65<br>[\[raw statistics\]][130121-raw8]</sub> |
| 2021&#8209;02&#8209;15 | [master][150221-master] vs [Stockfish 12]<br><sub>`Bench: 3766422`<br>Small trivial clean-ups, February 2021<br>[\[differences\]][150221-dif] `121`</sub> | Elo: [36.03][150221-elo1] ±1.1<br><sub>Ptnml:&nbsp;29,&nbsp;1395,&nbsp;21210,&nbsp;7079,&nbsp;287<br>nElo: 95.63 ±2.7<br>PairsRatio: 5.17<br>[\[raw statistics\]][150221-raw1]</sub> | Elo: [29.08][150221-elo8] ±1.1<br><sub>Ptnml:&nbsp;6,&nbsp;626,&nbsp;15476,&nbsp;3806,&nbsp;86<br>nElo: 89.08 ±3.1<br>PairsRatio: 6.16<br>[\[raw statistics\]][150221-raw8]</sub> |
| 2021&#8209;02&#8209;18 | [Stockfish 13] [[[https://stockfishchess.org/images/logo/icon_128x128.png\|width=20px]]][SF13RN] [[[https://github.githubassets.com/images/icons/emoji/unicode/1f4c8.png\|width=20px]]][SF13DP]<br><sub>`Bench: 3766422`<br>[\[differences\]][180221-dif] `123`</sub> |

</details>

<details>
  <summary><code>Stockfish 14 Development (2021-02-18 - 2021-07-02)</code></summary><br>

| `Date` | `Version` | `1 Thread` | `8 Threads` |
|:------:|:---------:|:----------:|:-----------:|
| 2021&#8209;02&#8209;26 | [master][260221-master] vs [Stockfish 13]<br><sub>`Bench: 5037279`<br>Introduce DistanceFromPV<br>[\[differences\]][260221-dif] `4`</sub> | Elo: [1.34][260221-elo1] ±0.8<br><sub>Ptnml:&nbsp;28,&nbsp;2367,&nbsp;24980,&nbsp;2596,&nbsp;29<br>nElo: 4.55 ±2.8<br>PairsRatio: 1.10<br>[\[raw statistics\]][260221-raw1]</sub> |
| 2021&#8209;03&#8209;24 | [master][240321-master] vs [Stockfish 13]<br><sub>`Bench: 4339126`<br>Small cleanups (march 2021)<br>[\[differences\]][240321-dif] `18`</sub> | Elo: [0.61][240321-elo1] ±0.8<br><sub>Ptnml:&nbsp;18,&nbsp;2457,&nbsp;24938,&nbsp;2575,&nbsp;12<br>nElo: 2.09 ±2.8<br>PairsRatio: 1.05<br>[\[raw statistics\]][240321-raw1]</sub> |
| 2021&#8209;04&#8209;15 | [master][150421-master] vs [Stockfish 13]<br><sub>`Bench: 4503918`<br>Use classical eval for Bishop vs Pawns<br>[\[differences\]][150421-dif] `29`</sub> | Elo: [1.47][150421-elo1] ±0.8<br><sub>Ptnml:&nbsp;39,&nbsp;2384,&nbsp;24886,&nbsp;2667,&nbsp;24<br>nElo: 4.93 ±2.8<br>PairsRatio: 1.11<br>[\[raw statistics\]][150421-raw1]</sub> | Elo: [0.89][150421-elo8] ±0.9<br><sub>Ptnml:&nbsp;11,&nbsp;1279,&nbsp;17318,&nbsp;1381,&nbsp;11<br>nElo: 3.38 ±3.4<br>PairsRatio: 1.08<br>[\[raw statistics\]][150421-raw8]</sub> |
| 2021&#8209;05&#8209;22 | [master][220521-master] vs [Stockfish 13]<br><sub>`Bench: 3856635`<br>Sometimes change the balance<br>[\[differences\]][220521-dif] `62`</sub> | Elo: [10.12][220521-elo1] ±1.0<br><sub>Ptnml:&nbsp;60,&nbsp;2454,&nbsp;23277,&nbsp;4096,&nbsp;113<br>nElo: 29.34 ±2.8<br>PairsRatio: 1.67<br>[\[raw statistics\]][220521-raw1]</sub> |
| 2021&#8209;06&#8209;14 | [master][140621-master] vs [Stockfish 13]<br><sub>`Bench: 4877339`<br>Update default net to nn-8e47cf062333.nnue<br>[\[differences\]][140621-dif] `90`</sub> | Elo: [21.80][140621-elo1] ±1.1<br><sub>Ptnml:&nbsp;67,&nbsp;2216,&nbsp;21852,&nbsp;5620,&nbsp;245<br>nElo: 57.47 ±2.7<br>PairsRatio: 2.57<br>[\[raw statistics\]][140621-raw1]</sub> | Elo: [16.96][140621-elo8] ±1.1<br><sub>Ptnml:&nbsp;15,&nbsp;1083,&nbsp;15923,&nbsp;2894,&nbsp;85<br>nElo: 52.38 ±3.3<br>PairsRatio: 2.71<br>[\[raw statistics\]][140621-raw8]</sub> |
| 2021&#8209;06&#8209;18 | [master][180621-master] vs [Stockfish 13]<br><sub>`Bench: 4900906`<br>Make net nn-50144f835024.nnue the default<br>[\[differences\]][180621-dif] `100`</sub> | Elo: [25.56][180621-elo1] ±1.0<br><sub>Ptnml:&nbsp;30,&nbsp;1814,&nbsp;22084,&nbsp;5864,&nbsp;208<br>nElo: 69.95 ±2.7<br>PairsRatio: 3.29<br>[\[raw statistics\]][180621-raw1]</sub> |
| 2021&#8209;06&#8209;29 | [master][290621-master] vs [Stockfish 13]<br><sub>`Bench: 4770936`<br>Update Top CPU Contributors<br>[\[differences\]][290621-dif] `113`</sub> | Elo: [30.27][290621-elo1] ±1.0<br><sub>Ptnml:&nbsp;14,&nbsp;1443,&nbsp;22127,&nbsp;6146,&nbsp;270<br>nElo: 83.66 ±2.6<br>PairsRatio: 4.40<br>[\[raw statistics\]][290621-raw1]</sub> | Elo: [22.62][290621-elo8] ±1.1<br><sub>Ptnml:&nbsp;7,&nbsp;755,&nbsp;15977,&nbsp;3153,&nbsp;108<br>nElo: 71.15 ±3.1<br>PairsRatio: 4.28<br>[\[raw statistics\]][290621-raw8]</sub> |
| 2021&#8209;07&#8209;02 | [Stockfish 14] [[[https://stockfishchess.org/images/logo/icon_128x128.png\|width=20px]]][SF14RN] [[[https://github.githubassets.com/images/icons/emoji/unicode/1f4c8.png\|width=20px]]][SF14DP]<br><sub>`Bench: 4770936`<br>[\[differences\]][020721-dif] `114`</sub> |

</details>

<details>
  <summary><code>Stockfish 15 Development (2021-07-02 - 2022-04-18)</code></summary><br>

| `Date` | `Version` | `1 Thread` | `8 Threads` | `1 Thread (UHO)` |
|:---:|:---:|:---:|:---:|:---:|
| 2021&#8209;07&#8209;26 | [master][260721-master] vs [Stockfish 14]<br><sub>`Bench: 5124774`<br>Update default net to nn-26abeed38351.nnue<br>[\[differences\]][260721-dif] `17`</sub> | Elo: [2.74][260721-elo1] ±0.8<br><sub>Ptnml:&nbsp;24,&nbsp;2000,&nbsp;25476,&nbsp;2478,&nbsp;22<br>nElo: 9.85 ±2.8<br>PairsRatio: 1.24<br>[\[raw statistics\]][260721-raw1]</sub> | |
| 2021&#8209;08&#8209;15 | [master][150821-master] vs [Stockfish 14]<br><sub>`Bench: 5189338`<br>New NNUE architecture and net<br>[\[differences\]][150821-dif] `26`</sub> | Elo: [9.31][150821-elo1] ±0.9<br><sub>Ptnml:&nbsp;24,&nbsp;2044,&nbsp;24321,&nbsp;3522,&nbsp;89<br>nElo: 29.61 ±2.7<br>PairsRatio: 1.75<br>[\[raw statistics\]][150821-raw1]</sub> | Elo: [6.08][150821-elo8] ±0.9<br><sub>Ptnml:&nbsp;5,&nbsp;1063,&nbsp;17183,&nbsp;1725,&nbsp;24<br>nElo: 22.66 ±3.4<br>PairsRatio: 1.64<br>[\[raw statistics\]][150821-raw8]</sub> | |
| 2021&#8209;08&#8209;31 | [master][310821-master] vs [Stockfish 14]<br><sub>`Bench: 5600615`<br>Update default net to nn-735bba95dec0.nnue<br>[\[differences\]][310821-dif] `39`</sub> | Elo: [15.04][310821-elo1] ±0.9<br><sub>Ptnml:&nbsp;17,&nbsp;1601,&nbsp;24272,&nbsp;3990,&nbsp;120<br>nElo: 47.86 ±2.7<br>PairsRatio: 2.54<br>[\[raw statistics\]][310821-raw1]</sub> | |
| 2021&#8209;09&#8209;15 | [master][150921-master] vs [Stockfish 14]<br><sub>`Bench: 6658747`<br>Update default net to nn-13406b1dcbe0.nnue<br>[\[differences\]][150921-dif] `46`</sub> | Elo: [16.64][150921-elo1] ±0.9<br><sub>Ptnml:&nbsp;21,&nbsp;1878,&nbsp;23452,&nbsp;4506,&nbsp;143<br>nElo: 49.53 ±2.7<br>PairsRatio: 2.45<br>[\[raw statistics\]][150921-raw1]</sub> | Elo: [12.39][150921-elo8] ±0.9<br><sub>Ptnml:&nbsp;1,&nbsp;766,&nbsp;17084,&nbsp;2104,&nbsp;45<br>nElo: 45.59 ±3.2<br>PairsRatio: 2.80<br>[\[raw statistics\]][150921-raw8]</sub> | |
| 2021&#8209;10&#8209;06 | [master][061021-master] vs [Stockfish 14]<br><sub>`Bench: 6261865`<br>Capping stat bonus at 2000<br>[\[differences\]][061021-dif] `57`</sub> | Elo: [18.68][061021-elo1] ±0.9<br><sub>Ptnml:&nbsp;28,&nbsp;1496,&nbsp;23821,&nbsp;4535,&nbsp;120<br>nElo: 57.70 ±2.7<br>PairsRatio: 3.05<br>[\[raw statistics\]][061021-raw1]</sub> | Elo: [11.74][061021-elo8] ±0.9<br><sub>Ptnml:&nbsp;4,&nbsp;769,&nbsp;17137,&nbsp;2052,&nbsp;38<br>nElo: 43.60 ±3.2<br>PairsRatio: 2.70<br>[\[raw statistics\]][061021-raw8]</sub> | |
| 2021&#8209;10&#8209;18 | [master][181021-master] vs [Stockfish 14]<br><sub>`Bench: 5005810`<br>Simplify probCutCount away<br>[\[differences\]][181021-dif] `67`</sub> | Elo: [17.69][181021-elo1] ±0.9<br><sub>Ptnml:&nbsp;13,&nbsp;1577,&nbsp;23891,&nbsp;4382,&nbsp;137<br>nElo: 54.78 ±2.7<br>PairsRatio: 2.84<br>[\[raw statistics\]][181021-raw1]</sub> | |
| 2021&#8209;10&#8209;23 | [master][231021-master] vs [Stockfish 14]<br><sub>`Bench: 6334068`<br>Adjust ButterflyHistory decay parameter<br>[\[differences\]][231021-dif] `78`</sub> | Elo: [17.87][231021-elo1] ±0.9<br><sub>Ptnml:&nbsp;11,&nbsp;1377,&nbsp;24244,&nbsp;4253,&nbsp;115<br>nElo: 57.35 ±2.6<br>PairsRatio: 3.15<br>[\[raw statistics\]][231021-raw1]</sub> | Elo: [10.27][231021-elo8] ±0.9<br><sub>Ptnml:&nbsp;3,&nbsp;696,&nbsp;17438,&nbsp;1842,&nbsp;21<br>nElo: 40.55 ±3.2<br>PairsRatio: 2.67<br>[\[raw statistics\]][231021-raw8]</sub> | |
| 2021&#8209;10&#8209;28 | [Stockfish 14.1] [[[https://stockfishchess.org/images/logo/icon_128x128.png\|width=20px]]][SF141RN]<br><sub>`Bench: 6334068`<br>[\[differences\]][281021-dif] `80`</sub> | |
| 2021&#8209;11&#8209;05 | [master][051121-master] vs [Stockfish 14]<br><sub>`Bench: 6719976`<br>Tweak initial aspiration window<br>[\[differences\]][051121-dif] `89`</sub> | Elo: [18.71][051121-elo1] ±0.9<br><sub>Ptnml:&nbsp;16,&nbsp;1293,&nbsp;24255,&nbsp;4319,&nbsp;117<br>nElo: 60.14 ±2.6<br>PairsRatio: 3.39<br>[\[raw statistics\]][051121-raw1]</sub> | |
| 2021&#8209;11&#8209;23 | [master][231121-master] vs [Stockfish 14]<br><sub>`Bench: 7334766`<br>Less futility pruning<br>[\[differences\]][231121-dif] `98`</sub> | Elo: [19.35][231121-elo1] ±0.9<br><sub>Ptnml:&nbsp;19,&nbsp;1405,&nbsp;23923,&nbsp;4524,&nbsp;129<br>nElo: 60.39 ±2.6<br>PairsRatio: 3.27<br>[\[raw statistics\]][231121-raw1]</sub> | Elo: [13.28][231121-elo8] ±0.9<br><sub>Ptnml:&nbsp;3,&nbsp;696,&nbsp;17112,&nbsp;2148,&nbsp;41<br>nElo: 49.26 ±3.2<br>PairsRatio: 3.13<br>[\[raw statistics\]][231121-raw8]</sub> | |
| 2021&#8209;11&#8209;28 | [master][281121-master] vs [Stockfish 14]<br><sub>`Bench: 6302543`<br>Refine futility pruning for parent nodes<br>[\[differences\]][281121-dif] `103`</sub> | Elo: [24.44][281121-elo1] ±0.9<br><sub>Ptnml:&nbsp;9,&nbsp;1054,&nbsp;23776,&nbsp;5037,&nbsp;124<br>nElo: 76.95 ±2.5<br>PairsRatio: 4.86<br>[\[raw statistics\]][281121-raw1]</sub> | |
| 2021&#8209;12&#8209;07 | [master][071221-master] vs [Stockfish 14]<br><sub>`Bench: 4667742`<br>Update default net to nn-63376713ba63.nnue<br>[\[differences\]][071221-dif] `118`</sub> | Elo: [26.99][071221-elo1] ±0.9<br><sub>Ptnml:&nbsp;11,&nbsp;998,&nbsp;23473,&nbsp;5365,&nbsp;153<br>nElo: 83.13 ±2.5<br>PairsRatio: 5.47<br>[\[raw statistics\]][071221-raw1]</sub> | Elo: [17.80][071221-elo8] ±0.9<br><sub>Ptnml:&nbsp;6,&nbsp;529,&nbsp;16919,&nbsp;2504,&nbsp;42<br>nElo: 64.76 ±3.1<br>PairsRatio: 4.76<br>[\[raw statistics\]][071221-raw8]</sub> | |
| 2021&#8209;12&#8209;14 | [master][141221-master] vs [Stockfish 14]<br><sub>`Bench: 4735679`<br>Remove NNUE scaling term<br>[\[differences\]][141221-dif] `126`</sub> | Elo: [26.45][141221-elo1] ±0.9<br><sub>Ptnml:&nbsp;9,&nbsp;962,&nbsp;23656,&nbsp;5207,&nbsp;166<br>nElo: 82.28 ±2.5<br>PairsRatio: 5.53<br>[\[raw statistics\]][141221-raw1]</sub> | |
| 2021&#8209;12&#8209;22 | [master][221221-master] vs [Stockfish 14]<br><sub>`Bench: 4633875`<br>Update default net to nn-ac07bd334b62.nnue<br>[\[differences\]][221221-dif] `139`</sub> | Elo: [28.65][221221-elo1] ±0.9<br><sub>Ptnml:&nbsp;11,&nbsp;1036,&nbsp;23172,&nbsp;5567,&nbsp;214<br>nElo: 85.61 ±2.5<br>PairsRatio: 5.52<br>[\[raw statistics\]][221221-raw1]</sub> | Elo: [17.66][221221-elo8] ±0.9<br><sub>Ptnml:&nbsp;2,&nbsp;520,&nbsp;16976,&nbsp;2448,&nbsp;54<br>nElo: 64.60 ±3.0<br>PairsRatio: 4.79<br>[\[raw statistics\]][221221-raw8]</sub> | |
| 2022&#8209;01&#8209;10 | [master][100122-master] vs [Stockfish 14]<br><sub>`Bench: 4572746`<br>Adjust pruning constants<br>[\[differences\]][100122-dif] `148`</sub> | Elo: [30.51][100122-elo1] ±1.0<br><sub>Ptnml:&nbsp;13,&nbsp;1065,&nbsp;22809,&nbsp;5879,&nbsp;234<br>nElo: 89.03 ±2.5<br>PairsRatio: 5.67<br>[\[raw statistics\]][100122-raw1]</sub> | |
| 2022&#8209;01&#8209;29 | [master][290122-master] vs [Stockfish 14]<br><sub>`Bench: 4637392`<br>Do stats updates after LMR for captures<br>[\[differences\]][290122-dif] `159`</sub> | Elo: [32.07][290122-elo1] ±1.0<br><sub>Ptnml:&nbsp;10,&nbsp;1009,&nbsp;22681,&nbsp;6049,&nbsp;251<br>nElo: 93.05 ±2.5<br>PairsRatio: 6.18<br>[\[raw statistics\]][290122-raw1]</sub> | Elo: [22.31][290122-elo8] ±1.0<br><sub>Ptnml:&nbsp;3,&nbsp;496,&nbsp;16495,&nbsp;2945,&nbsp;61<br>nElo: 76.78 ±3.0<br>PairsRatio: 6.02<br>[\[raw statistics\]][290122-raw8]</sub> | |
| 2022&#8209;02&#8209;10 | [master][100222-master] vs [Stockfish 14]<br><sub>`Bench: 4919707`<br>Update architecture to "SFNNv4"<br>[\[differences\]][100222-dif] `166`</sub> | Elo: [34.88][100222-elo1] ±1.0<br><sub>Ptnml:&nbsp;13,&nbsp;884,&nbsp;22430,&nbsp;6432,&nbsp;241<br>nElo: 100.85 ±2.5<br>PairsRatio: 7.44<br>[\[raw statistics\]][100222-raw1]</sub> | Elo: [24.37][100222-elo8] ±1.0<br><sub>Ptnml:&nbsp;2,&nbsp;416,&nbsp;16441,&nbsp;3061,&nbsp;80<br>nElo: 83.29 ±2.9<br>PairsRatio: 7.51<br>[\[raw statistics\]][100222-raw8]</sub> | |
| 2022&#8209;02&#8209;17 | [master][170222-master] vs [Stockfish 14]<br><sub>`Bench: 6318903`<br>Tune search at very long time control<br>[\[differences\]][170222-dif] `168`</sub> | Elo: [33.07][170222-elo1] ±1.0<br><sub>Ptnml:&nbsp;17,&nbsp;984,&nbsp;22522,&nbsp;6243,&nbsp;234<br>nElo: 95.49 ±2.5<br>PairsRatio: 6.47<br>[\[raw statistics\]][170222-raw1]</sub> | Elo: [23.83][170222-elo8] ±1.0<br><sub>Ptnml:&nbsp;4,&nbsp;410,&nbsp;16496,&nbsp;3023,&nbsp;67<br>nElo: 82.31 ±2.9<br>PairsRatio: 7.46<br>[\[raw statistics\]][170222-raw8]</sub> | |
| 2022&#8209;03&#8209;19 | [master][190322-master] vs [Stockfish 14]<br><sub>`Bench: 7044203`<br>Remove ttPv tree shrinking<br>[\[differences\]][190322-dif] `180`</sub> | Elo: [35.01][190322-elo1] ±1.0<br><sub>Ptnml:&nbsp;11,&nbsp;801,&nbsp;22566,&nbsp;6395,&nbsp;227<br>nElo: 102.62 ±2.5<br>PairsRatio: 8.16<br>[\[raw statistics\]][190322-raw1]</sub> | |
| 2022&#8209;04&#8209;17 | [master][170422-master] vs [Stockfish 14]<br><sub>`Bench: 8129754`<br>Decrease LMR at PV nodes with low depth<br>[\[differences\]][170422-dif] `189`</sub> | Elo: [36.69][170422-elo1] ±1.0<br><sub>Ptnml:&nbsp;5,&nbsp;711,&nbsp;22489,&nbsp;6557,&nbsp;238<br>nElo: 107.69 ±2.4<br>PairsRatio: 9.49<br>[\[raw statistics\]][170422-raw1]</sub> | Elo: [26.09][170422-elo8] ±1.0<br><sub>Ptnml:&nbsp;1,&nbsp;341,&nbsp;16379,&nbsp;3217,&nbsp;62<br>nElo: 89.84 ±2.8<br>PairsRatio: 9.59<br>[\[raw statistics\]][170422-raw8]</sub> | Elo: [91.22][170422-elo1uho] ±1.3<br><sub>Ptnml:&nbsp;17,&nbsp;1335,&nbsp;12388,&nbsp;15750,&nbsp;510<br>nElo: 205.62 ±3.6<br>PairsRatio: 12.03<br>[\[raw statistics\]][170422-raw1uho]</sub> |
| 2022&#8209;04&#8209;18 | [Stockfish 15] [[[https://stockfishchess.org/images/logo/icon_128x128.png\|width=20px]]][SF15RN] [[[https://github.githubassets.com/images/icons/emoji/unicode/1f4c8.png\|width=20px]]][SF15DP]<br><sub>`Bench: 8129754`<br>[\[differences\]][180422-dif] `190`</sub> | |

</details>

<details>
  <summary><code>Stockfish 16 Development (2022-04-18 - 2023-06-29)</code></summary><br>

| `Date` | `Version` | `1 Thread` | `8 Threads` | `1 Thread (UHO)` |
|:---:|:---:|:---:|:---:|:---:|
| 2022&#8209;05&#8209;14 | [master][140522-master] vs [Stockfish 15]<br><sub>`Bench: 6481017`<br>SE depth scaling using the previous depth<br>[\[differences\]][140522-dif] `9`</sub> | Elo: [4.54][140522-elo1] ±0.8<br><sub>Ptnml:&nbsp;18,&nbsp;1850,&nbsp;25507,&nbsp;2580,&nbsp;45<br>nElo: 16.29 ±2.8<br>PairsRatio: 1.41<br>[\[raw statistics\]][140522-raw1]</sub> | Elo: [3.12][140522-elo8] ±0.8<br><sub>Ptnml:&nbsp;5,&nbsp;803,&nbsp;18029,&nbsp;1154,&nbsp;9<br>nElo: 13.92 ±3.4<br>PairsRatio: 1.44<br>[\[raw statistics\]][140522-raw8]</sub> |  |
| 2022&#8209;06&#8209;16 | [master][160622-master] vs [Stockfish 15]<br><sub>`Bench: 5845802`<br>Simplify away condition in ttSave in probCut<br>[\[differences\]][160622-dif] `25`</sub> | Elo: [5.72][160622-elo1] ±0.8<br><sub>Ptnml:&nbsp;31,&nbsp;1838,&nbsp;25288,&nbsp;2799,&nbsp;44<br>nElo: 19.99 ±2.8<br>PairsRatio: 1.52<br>[\[raw statistics\]][160622-raw1]</sub> |  |  |
| 2022&#8209;07&#8209;13 | [master][130722-master] vs [Stockfish 15]<br><sub>`Bench: 5905619`<br>Update default net to nn-ad9b42354671.nnue<br>[\[differences\]][130722-dif] `34`</sub> | Elo: [5.70][130722-elo1] ±0.8<br><sub>Ptnml:&nbsp;42,&nbsp;1867,&nbsp;25207,&nbsp;2832,&nbsp;52<br>nElo: 19.67 ±2.8<br>PairsRatio: 1.51<br>[\[raw statistics\]][130722-raw1]</sub> | Elo: [4.86][130722-elo8] ±0.8<br><sub>Ptnml:&nbsp;3,&nbsp;734,&nbsp;17975,&nbsp;1276,&nbsp;12<br>nElo: 21.46 ±3.3<br>PairsRatio: 1.75<br>[\[raw statistics\]][130722-raw8]</sub> |  |
| 2022&#8209;08&#8209;12 | [master][120822-master] vs [Stockfish 15]<br><sub>`Bench: 5868987`<br>Remove an unneeded randomization of evals<br>[\[differences\]][120822-dif] `43`</sub> | Elo: [7.18][120822-elo1] ±0.8<br><sub>Ptnml:&nbsp;48,&nbsp;1784,&nbsp;25112,&nbsp;2993,&nbsp;63<br>nElo: 24.44 ±2.8<br>PairsRatio: 1.67<br>[\[raw statistics\]][120822-raw1]</sub> | Elo: [4.60][120822-elo8] ±0.8<br><sub>Ptnml:&nbsp;5,&nbsp;737,&nbsp;17987,&nbsp;1265,&nbsp;6<br>nElo: 20.43 ±3.4<br>PairsRatio: 1.71<br>[\[raw statistics\]][120822-raw8]</sub> | Elo: [14.61][120822-elo1uho] ±1.3<br><sub>Ptnml:&nbsp;149,&nbsp;5043,&nbsp;17073,&nbsp;7608,&nbsp;127<br>nElo: 30.73 ±2.8<br>PairsRatio: 1.49<br>[\[raw statistics\]][120822-raw1uho]</sub> |
| 2022&#8209;09&#8209;07 | [master][070922-master] vs [Stockfish 15]<br><sub>`Bench: 5609606`<br>VLTC tuning<br>[\[differences\]][070922-dif] `52`</sub> | Elo: [6.87][070922-elo1] ±0.8<br><sub>Ptnml:&nbsp;40,&nbsp;1796,&nbsp;25154,&nbsp;2958,&nbsp;52<br>nElo: 23.61 ±2.8<br>PairsRatio: 1.64<br>[\[raw statistics\]][070922-raw1]</sub> | Elo: [5.45][070922-elo8] ±0.8<br><sub>Ptnml:&nbsp;3,&nbsp;732,&nbsp;17913,&nbsp;1339,&nbsp;13<br>nElo: 23.68 ±3.3<br>PairsRatio: 1.84<br>[\[raw statistics\]][070922-raw8]</sub> |  |
| 2022&#8209;10&#8209;05 | [master][051022-master] vs [Stockfish 15]<br><sub>`Bench: 4114228`<br>Revert "Mix alpha and statScore for reduction"<br>[\[differences\]][051022-dif] `66`</sub> | Elo: [6.86][051022-elo1] ±0.8<br><sub>Ptnml:&nbsp;21,&nbsp;1580,&nbsp;25632,&nbsp;2727,&nbsp;40<br>nElo: 25.04 ±2.7<br>PairsRatio: 1.73<br>[\[raw statistics\]][051022-raw1]</sub> | Elo: [5.98][051022-elo8] ±0.8<br><sub>Ptnml:&nbsp;6,&nbsp;643,&nbsp;18015,&nbsp;1329,&nbsp;7<br>nElo: 26.72 ±3.3<br>PairsRatio: 2.06<br>[\[raw statistics\]][051022-raw8]</sub> |  |
| 2022&#8209;10&#8209;30 | [master][301022-master] vs [Stockfish 15]<br><sub>`Bench: 4271738`<br>Adjust reduction less at medium depths<br>[\[differences\]][301022-dif] `81`</sub> | Elo: [8.52][301022-elo1] ±0.8<br><sub>Ptnml:&nbsp;23,&nbsp;1469,&nbsp;25573,&nbsp;2884,&nbsp;51<br>nElo: 30.84 ±2.7<br>PairsRatio: 1.97<br>[\[raw statistics\]][301022-raw1]</sub> | Elo: [5.91][301022-elo8] ±0.7<br><sub>Ptnml:&nbsp;6,&nbsp;589,&nbsp;18129,&nbsp;1271,&nbsp;5<br>nElo: 27.24 ±3.3<br>PairsRatio: 2.14<br>[\[raw statistics\]][301022-raw8]</sub> | Elo: [17.17][301022-elo1uho] ±1.8<br><sub>Ptnml:&nbsp;38,&nbsp;2430,&nbsp;8572,&nbsp;3933,&nbsp;27<br>nElo: 36.91 ±4.0<br>PairsRatio: 1.60<br>[\[raw statistics\]][301022-raw1uho]</sub> |
| 2022&#8209;12&#8209;02 | [master][021222-master] vs [Stockfish 15]<br><sub>`Bench: 3467381`<br>Fix bestThread selection<br>[\[differences\]][021222-dif] `97`</sub> | Elo: [7.46][021222-elo1] ±0.7<br><sub>Ptnml:&nbsp;21,&nbsp;1389,&nbsp;25902,&nbsp;2657,&nbsp;31<br>nElo: 28.19 ±2.7<br>PairsRatio: 1.91<br>[\[raw statistics\]][021222-raw1]</sub> | Elo: [5.97][021222-elo8] ±0.7<br><sub>Ptnml:&nbsp;3,&nbsp;573,&nbsp;18164,&nbsp;1254,&nbsp;6<br>nElo: 27.83 ±3.3<br>PairsRatio: 2.19<br>[\[raw statistics\]][021222-raw8]</sub> | Elo: [17.04][021222-elo1uho] ±1.3<br><sub>Ptnml:&nbsp;73,&nbsp;4844,&nbsp;17208,&nbsp;7820,&nbsp;55<br>nElo: 36.73 ±2.8<br>PairsRatio: 1.60<br>[\[raw statistics\]][021222-raw1uho]</sub> |
| 2022&#8209;12&#8209;04 | [Stockfish 15.1] [[[https://stockfishchess.org/images/logo/icon_128x128.png\|width=20px]]][SF151RN]<br><sub>`Bench: 3467381`<br>[\[differences\]][041222-dif] `98`</sub> |  |  |  |
| 2022&#8209;12&#8209;19 | [master][191222-master] vs [Stockfish 15]<br><sub>`Bench: 3727508`<br>Sometimes do a reduced search if LMR is skipped<br>[\[differences\]][191222-dif] `119`</sub> | Elo: [8.55][191222-elo1] ±0.8<br><sub>Ptnml:&nbsp;16,&nbsp;1420,&nbsp;25675,&nbsp;2850,&nbsp;39<br>nElo: 31.50 ±2.7<br>PairsRatio: 2.01<br>[\[raw statistics\]][191222-raw1]</sub> |  |  |
| 2023&#8209;01&#8209;01 | [master][010123-master] vs [Stockfish 15]<br><sub>`Bench: 4015511`<br>Update default net to nn-60fa44e376d9.nnue<br>[\[differences\]][010123-dif] `126`</sub> | Elo: [10.00][010123-elo1] ±0.8<br><sub>Ptnml:&nbsp;15,&nbsp;1301,&nbsp;25667,&nbsp;2976,&nbsp;41<br>nElo: 36.92 ±2.7<br>PairsRatio: 2.29<br>[\[raw statistics\]][010123-raw1]</sub> | Elo: [7.10][010123-elo8] ±0.7<br><sub>Ptnml:&nbsp;6,&nbsp;529,&nbsp;18118,&nbsp;1336,&nbsp;11<br>nElo: 32.56 ±3.2<br>PairsRatio: 2.52<br>[\[raw statistics\]][010123-raw8]</sub> | Elo: [23.55][010123-elo1uho] ±1.3<br><sub>Ptnml:&nbsp;59,&nbsp;4354,&nbsp;17132,&nbsp;8377,&nbsp;78<br>nElo: 51.05 ±2.8<br>PairsRatio: 1.92<br>[\[raw statistics\]][010123-raw1uho]</sub> |
| 2023&#8209;01&#8209;23 | [master][230123-master] vs [Stockfish 15]<br><sub>`Bench: 3941848`<br>Update default net to nn-bc24c101ada0.nnue<br>[\[differences\]][230123-dif] `143`</sub> | Elo: [11.37][230123-elo1] ±0.7<br><sub>Ptnml:&nbsp;9,&nbsp;1127,&nbsp;25786,&nbsp;3048,&nbsp;30<br>nElo: 42.95 ±2.7<br>PairsRatio: 2.71<br>[\[raw statistics\]][230123-raw1]</sub> | Elo: [9.09][230123-elo8] ±0.8<br><sub>Ptnml:&nbsp;2,&nbsp;484,&nbsp;17984,&nbsp;1526,&nbsp;4<br>nElo: 40.84 ±3.2<br>PairsRatio: 3.15<br>[\[raw statistics\]][230123-raw8]</sub> | Elo: [29.49][230123-elo1uho] ±1.3<br><sub>Ptnml:&nbsp;43,&nbsp;3893,&nbsp;17099,&nbsp;8870,&nbsp;95<br>nElo: 64.58 ±2.9<br>PairsRatio: 2.28<br>[\[raw statistics\]][230123-raw1uho]</sub> |
| 2023&#8209;02&#8209;09 | [master][090223-master] vs [Stockfish 15]<br><sub>`Bench: 3841998`<br>Update default net to nn-1337b1adec5b.nnue<br>[\[differences\]][090223-dif] `162`</sub> | Elo: [12.76][090223-elo1] ±0.8<br><sub>Ptnml:&nbsp;9,&nbsp;1089,&nbsp;25635,&nbsp;3224,&nbsp;43<br>nElo: 47.33 ±2.6<br>PairsRatio: 2.98<br>[\[raw statistics\]][090223-raw1]</sub> | Elo: [8.49][090223-elo8] ±0.8<br><sub>Ptnml:&nbsp;2,&nbsp;502,&nbsp;18018,&nbsp;1473,&nbsp;5<br>nElo: 38.38 ±3.2<br>PairsRatio: 2.93<br>[\[raw statistics\]][090223-raw8]</sub> | Elo: [32.71][090223-elo1uho] ±1.3<br><sub>Ptnml:&nbsp;44,&nbsp;3760,&nbsp;16821,&nbsp;9269,&nbsp;106<br>nElo: 71.26 ±2.9<br>PairsRatio: 2.46<br>[\[raw statistics\]][090223-raw1uho]</sub> |
| 2023&#8209;02&#8209;18 | [master][180223-master] vs [Stockfish 15]<br><sub>`Bench: 4283297`<br>Remove one reduction call<br>[\[differences\]][180223-dif] `168`</sub> | Elo: [12.58][180223-elo1] ±0.8<br><sub>Ptnml:&nbsp;11,&nbsp;1127,&nbsp;25591,&nbsp;3221,&nbsp;50<br>nElo: 46.26 ±2.6<br>PairsRatio: 2.87<br>[\[raw statistics\]][180223-raw1]</sub> |  | Elo: [31.91][180223-elo1uho] ±1.3<br><sub>Ptnml:&nbsp;47,&nbsp;3828,&nbsp;16804,&nbsp;9225,&nbsp;96<br>nElo: 69.38 ±2.9<br>PairsRatio: 2.41<br>[\[raw statistics\]][180223-raw1uho]</sub> |
| 2023&#8209;02&#8209;24 | [master][240223-master] vs [Stockfish 15]<br><sub>`Bench: 4705194`<br>Search tuning at very long time control<br>[\[differences\]][240223-dif] `174`</sub> | Elo: [11.69][240223-elo1] ±0.7<br><sub>Ptnml:&nbsp;10,&nbsp;1151,&nbsp;25692,&nbsp;3105,&nbsp;42<br>nElo: 43.51 ±2.6<br>PairsRatio: 2.71<br>[\[raw statistics\]][240223-raw1]</sub> | Elo: [9.37][240223-elo8] ±0.8<br><sub>Ptnml:&nbsp;1,&nbsp;455,&nbsp;18013,&nbsp;1526,&nbsp;5<br>nElo: 42.48 ±3.1<br>PairsRatio: 3.36<br>[\[raw statistics\]][240223-raw8]</sub> | Elo: [32.42][240223-elo1uho] ±1.3<br><sub>Ptnml:&nbsp;44,&nbsp;3804,&nbsp;16761,&nbsp;9307,&nbsp;84<br>nElo: 70.59 ±2.9<br>PairsRatio: 2.44<br>[\[raw statistics\]][240223-raw1uho]</sub> |
| 2023&#8209;03&#8209;19 | [master][190323-master] vs [Stockfish 15]<br><sub>`Bench: 4980082`<br>Remove 'si' StateInfo variable/parameter.<br>[\[differences\]][190323-dif] `196`</sub> | Elo: [13.36][190323-elo1] ±0.8<br><sub>Ptnml:&nbsp;9,&nbsp;1098,&nbsp;25532,&nbsp;3300,&nbsp;61<br>nElo: 48.75 ±2.6<br>PairsRatio: 3.04<br>[\[raw statistics\]][190323-raw1]</sub> | Elo: [10.10][190323-elo8] ±0.8<br><sub>Ptnml:&nbsp;0,&nbsp;460,&nbsp;17934,&nbsp;1589,&nbsp;17<br>nElo: 44.63 ±3.1<br>PairsRatio: 3.49<br>[\[raw statistics\]][190323-raw8]</sub> | Elo: [35.27][190323-elo1uho] ±1.3<br><sub>Ptnml:&nbsp;48,&nbsp;3610,&nbsp;16657,&nbsp;9594,&nbsp;91<br>nElo: 76.91 ±2.9<br>PairsRatio: 2.65<br>[\[raw statistics\]][190323-raw1uho]</sub> |
| 2023&#8209;04&#8209;01 | [master][010423-master] vs [Stockfish 15]<br><sub>`Bench: 4380438`<br>Decrease Depth more for positions not in TT.<br>[\[differences\]][010423-dif] `211`</sub> | Elo: [14.42][010423-elo1] ±0.8<br><sub>Ptnml:&nbsp;7,&nbsp;1031,&nbsp;25480,&nbsp;3431,&nbsp;51<br>nElo: 52.68 ±2.6<br>PairsRatio: 3.35<br>[\[raw statistics\]][010423-raw1]</sub> | Elo: [9.90][010423-elo8] ±0.8<br><sub>Ptnml:&nbsp;2,&nbsp;450,&nbsp;17964,&nbsp;1575,&nbsp;9<br>nElo: 44.20 ±3.1<br>PairsRatio: 3.50<br>[\[raw statistics\]][010423-raw8]</sub> | Elo: [37.37][010423-elo1uho] ±1.3<br><sub>Ptnml:&nbsp;48,&nbsp;3485,&nbsp;16555,&nbsp;9815,&nbsp;97<br>nElo: 81.54 ±2.9<br>PairsRatio: 2.81<br>[\[raw statistics\]][010423-raw1uho]</sub> |
| 2023&#8209;04&#8209;22 | [master][220423-master] vs [Stockfish 15]<br><sub>`Bench: 3548023`<br>Less reduction for tt move.<br>[\[differences\]][220423-dif] `235`</sub> | Elo: [14.60][220423-elo1] ±0.8<br><sub>Ptnml:&nbsp;9,&nbsp;967,&nbsp;25569,&nbsp;3405,&nbsp;50<br>nElo: 53.91 ±2.6<br>PairsRatio: 3.54<br>[\[raw statistics\]][220423-raw1]</sub> | Elo: [11.32][220423-elo8] ±0.8<br><sub>Ptnml:&nbsp;0,&nbsp;386,&nbsp;17939,&nbsp;1661,&nbsp;14<br>nElo: 50.39 ±3.0<br>PairsRatio: 4.34<br>[\[raw statistics\]][220423-raw8]</sub> | Elo: [38.07][220423-elo1uho] ±1.3<br><sub>Ptnml:&nbsp;27,&nbsp;3392,&nbsp;16687,&nbsp;9793,&nbsp;101<br>nElo: 83.87 ±2.9<br>PairsRatio: 2.89<br>[\[raw statistics\]][220423-raw1uho]</sub> |
| 2023&#8209;05&#8209;07 | [master][070523-master] vs [Stockfish 15]<br><sub>`Bench: 3808503`<br>Refine deeper post-lmr searches<br>[\[differences\]][070523-dif] `244`</sub> | Elo: [14.36][070523-elo1] ±0.8<br><sub>Ptnml:&nbsp;11,&nbsp;1004,&nbsp;25521,&nbsp;3423,&nbsp;41<br>nElo: 52.83 ±2.6<br>PairsRatio: 3.41<br>[\[raw statistics\]][070523-raw1]</sub> | Elo: [10.63][070523-elo8] ±0.7<br><sub>Ptnml:&nbsp;0,&nbsp;379,&nbsp;18029,&nbsp;1581,&nbsp;11<br>nElo: 48.41 ±3.0<br>PairsRatio: 4.20<br>[\[raw statistics\]][070523-raw8]</sub> | Elo: [39.62][070523-elo1uho] ±1.3<br><sub>Ptnml:&nbsp;34,&nbsp;3309,&nbsp;16568,&nbsp;9988,&nbsp;101<br>nElo: 87.17 ±2.9<br>PairsRatio: 3.02<br>[\[raw statistics\]][070523-raw1uho]</sub> |
| 2023&#8209;06&#8209;04 | [master][040623-master] vs [Stockfish 15]<br><sub>`Bench: 2551691`<br>Move internal iterative reduction before probcut<br>[\[differences\]][040623-dif] `265`</sub> | Elo: [15.01][040623-elo1] ±0.8<br><sub>Ptnml:&nbsp;9,&nbsp;1037,&nbsp;25355,&nbsp;3552,&nbsp;47<br>nElo: 54.25 ±2.6<br>PairsRatio: 3.44<br>[\[raw statistics\]][040623-raw1]</sub> | Elo: [11.87][040623-elo8] ±0.8<br><sub>Ptnml:&nbsp;3,&nbsp;362,&nbsp;17908,&nbsp;1720,&nbsp;7<br>nElo: 52.68 ±3.0<br>PairsRatio: 4.73<br>[\[raw statistics\]][040623-raw8]</sub> | Elo: [38.10][040623-elo1uho] ±1.3<br><sub>Ptnml:&nbsp;48,&nbsp;3387,&nbsp;16634,&nbsp;9826,&nbsp;105<br>nElo: 83.49 ±2.9<br>PairsRatio: 2.89<br>[\[raw statistics\]][040623-raw1uho]</sub> |
| 2023&#8209;06&#8209;12 | [master][120623-master] vs [Stockfish 15]<br><sub>`Bench: 2370027`<br>Use block sparse input for the first layer.<br>[\[differences\]][120623-dif] `274`</sub> | Elo: [17.57][120623-elo1] ±0.8<br><sub>Ptnml:&nbsp;10,&nbsp;881,&nbsp;25223,&nbsp;3840,&nbsp;46<br>nElo: 63.12 ±2.5<br>PairsRatio: 4.36<br>[\[raw statistics\]][120623-raw1]</sub> | Elo: [13.95][120623-elo8] ±0.8<br><sub>Ptnml:&nbsp;1,&nbsp;290,&nbsp;17828,&nbsp;1865,&nbsp;16<br>nElo: 60.93 ±2.8<br>PairsRatio: 6.46<br>[\[raw statistics\]][120623-raw8]</sub> | Elo: [44.18][120623-elo1uho] ±1.3<br><sub>Ptnml:&nbsp;45,&nbsp;3031,&nbsp;16345,&nbsp;10449,&nbsp;130<br>nElo: 97.20 ±3.0<br>PairsRatio: 3.44<br>[\[raw statistics\]][120623-raw1uho]</sub> |
| 2023&#8209;06&#8209;22 | [master][220623-master] vs [Stockfish 15]<br><sub>`Bench: 2593605`<br>Update default net to nn-5af11540bbfe.nnue<br>[\[differences\]][220623-dif] `289`</sub> | Elo: [18.30][220623-elo1] ±0.8<br><sub>Ptnml:&nbsp;3,&nbsp;812,&nbsp;25265,&nbsp;3864,&nbsp;56<br>nElo: 66.19 ±2.5<br>PairsRatio: 4.81<br>[\[raw statistics\]][220623-raw1]</sub> | Elo: [14.33][220623-elo8] ±0.8<br><sub>Ptnml:&nbsp;3,&nbsp;297,&nbsp;17767,&nbsp;1914,&nbsp;19<br>nElo: 61.59 ±2.9<br>PairsRatio: 6.44<br>[\[raw statistics\]][220623-raw8]</sub> | Elo: [47.03][220623-elo1uho] ±1.3<br><sub>Ptnml:&nbsp;26,&nbsp;2938,&nbsp;16102,&nbsp;10805,&nbsp;129<br>nElo: 103.71 ±3.0<br>PairsRatio: 3.69<br>[\[raw statistics\]][220623-raw1uho]</sub> |
| 2023&#8209;06&#8209;29 | [Stockfish 16] [[[https://stockfishchess.org/images/logo/icon_128x128.png\|width=20px]]][SF16RN] [[[https://github.githubassets.com/images/icons/emoji/unicode/1f4c8.png\|width=20px]]][SF16DP]<br><sub>`Bench: 2593605`<br>[\[differences\]][290623-dif] `290`</sub> | |

</details>

---

## External Links

There are several pages on the web run by chess engine fans. Some collect progress of Stockfish
over previous stable versions and development builds. Some compare Stockfish progress to other
chess engines. Here is a collection of some useful links in that regard.

* [Computer Chess Rating Lists (CCRL)](https://computerchess.org.uk/ccrl/4040/)
* [FastGMs Rating Lists (FGRL)](http://www.fastgm.de)
* [Ipman Chess](http://ipmanchess.yolasite.com)
* [Mate Finding Effectiveness](https://github.com/vondele/matetrack)
* [Next Chess Move (NCM)](https://nextchessmove.com/dev-builds)
* [Stefan Pohl Computer Chess (SPCC)](https://www.sp-cc.de)

[book-8mv3]:      https://github.com/official-stockfish/books/blob/master/8moves_v3.pgn.zip
[book-uho21epd]:  https://github.com/official-stockfish/books/blob/master/UHO_XXL_%2B0.90_%2B1.19.epd.zip
[book-uho4060v2]: https://github.com/official-stockfish/books/blob/master/UHO_4060_v2.epd.zip
[book-uho4060v3]: https://github.com/official-stockfish/books/blob/master/UHO_4060_v3.epd.zip
[Fishtest]:       https://tests.stockfishchess.org/tests
[Stockfish 2.3.1]:https://github.com/official-stockfish/Stockfish/commit/3caeabf73b12ad53ac7ba64122a2feab819c6527
[040313-dif]:     https://github.com/official-stockfish/Stockfish/compare/3caeabf73b...10429dd616
[040313-elo1]:    https://tests.stockfishchess.org/tests/view/51345f228f0c3e28913c9cf0
[040313-master]:  https://github.com/official-stockfish/Stockfish/commit/10429dd616b97250107a64c1b91fdffee03e4790
[040313-raw1]:    https://tests.stockfishchess.org/tests/stats/51345f228f0c3e28913c9cf0
[110313A-dif]:    https://github.com/official-stockfish/Stockfish/compare/3caeabf73b...3698d9aa55
[110313A-elo1]:   https://tests.stockfishchess.org/tests/view/5146bf698f0c3e3cad8ee607
[110313A-master]: https://github.com/official-stockfish/Stockfish/commit/3698d9aa5573ca666c238b7d31a48b2aeede43dd
[110313A-raw1]:   https://tests.stockfishchess.org/tests/stats/5146bf698f0c3e3cad8ee607
[110313B-dif]:    https://github.com/official-stockfish/Stockfish/compare/3caeabf73b...a24da071f0
[110313B-elo1]:   https://tests.stockfishchess.org/tests/view/513e4c258f0c3e7dc24b8186
[110313B-master]: https://github.com/official-stockfish/Stockfish/commit/a24da071f0d6128c633febab7df55f14475217c3
[110313B-raw1]:   https://tests.stockfishchess.org/tests/stats/513e4c258f0c3e7dc24b8186
[160313-dif]:     https://github.com/official-stockfish/Stockfish/compare/3caeabf73b...0586b51f9c
[160313-elo1]:    https://tests.stockfishchess.org/tests/view/51445c42e4721c1de2dc1246
[160313-master]:  https://github.com/official-stockfish/Stockfish/commit/0586b51f9c398008f264d78a2888c0d68d9561cb
[160313-raw1]:    https://tests.stockfishchess.org/tests/stats/51445c42e4721c1de2dc1246
[240313-dif]:     https://github.com/official-stockfish/Stockfish/compare/3caeabf73b...0b4ea54da9
[240313-elo1]:    https://tests.stockfishchess.org/tests/view/514f7f3b8f0c3e4a8a33bf78
[240313-master]:  https://github.com/official-stockfish/Stockfish/commit/0b4ea54da999e591284aaeec702b6239ca219b81
[240313-raw1]:    https://tests.stockfishchess.org/tests/stats/514f7f3b8f0c3e4a8a33bf78
[300313-dif]:     https://github.com/official-stockfish/Stockfish/compare/3caeabf73b...7d42d02ec7
[300313-elo1]:    https://tests.stockfishchess.org/tests/view/515759308f0c3e3b5303952e
[300313-master]:  https://github.com/official-stockfish/Stockfish/commit/7d42d02ec77a03c4c1e1b399df30ef8b363c1237
[300313-raw1]:    https://tests.stockfishchess.org/tests/stats/515759308f0c3e3b5303952e
[030413-dif]:     https://github.com/official-stockfish/Stockfish/compare/3caeabf73b...36c82b751c
[030413-elo1]:    https://tests.stockfishchess.org/tests/view/515c654a8f0c3e0a8a4b9d79
[030413-master]:  https://github.com/official-stockfish/Stockfish/commit/36c82b751ce227c05bfb0dc74c311a469f7f8ec4
[030413-raw1]:    https://tests.stockfishchess.org/tests/stats/515c654a8f0c3e0a8a4b9d79
[060413-dif]:     https://github.com/official-stockfish/Stockfish/compare/3caeabf73b...889922041b
[060413-elo1]:    https://tests.stockfishchess.org/tests/view/515fb1708f0c3e20bb6b7b43
[060413-master]:  https://github.com/official-stockfish/Stockfish/commit/889922041be317f26a2547498b6751ed55f0ee22
[060413-raw1]:    https://tests.stockfishchess.org/tests/stats/515fb1708f0c3e20bb6b7b43
[070413-dif]:     https://github.com/official-stockfish/Stockfish/compare/3caeabf73b...9498b2af82
[070413-elo1]:    https://tests.stockfishchess.org/tests/view/516141648f0c3e3124ab6c73
[070413-master]:  https://github.com/official-stockfish/Stockfish/commit/9498b2af82e51a42b5baf6579faeb66589be9ebb
[070413-raw1]:    https://tests.stockfishchess.org/tests/stats/516141648f0c3e3124ab6c73
[100413-dif]:     https://github.com/official-stockfish/Stockfish/compare/3caeabf73b...fe72c93141
[100413-elo1]:    https://tests.stockfishchess.org/tests/view/5165cbb68f0c3e5968ed27e9
[100413-master]:  https://github.com/official-stockfish/Stockfish/commit/fe72c93141627c8109761da6546014a8d0461450
[100413-raw1]:    https://tests.stockfishchess.org/tests/stats/5165cbb68f0c3e5968ed27e9
[190413-dif]:     https://github.com/official-stockfish/Stockfish/compare/3caeabf73b...f84f04742a
[190413-elo1]:    https://tests.stockfishchess.org/tests/view/517105698f0c3e2dd765906d
[190413-master]:  https://github.com/official-stockfish/Stockfish/commit/f84f04742a30166c2751de28245e11922da132fb
[190413-raw1]:    https://tests.stockfishchess.org/tests/stats/517105698f0c3e2dd765906d
[260413-dif]:     https://github.com/official-stockfish/Stockfish/compare/3caeabf73b...e508494a99
[260413-elo1]:    https://tests.stockfishchess.org/tests/view/517a569e8f0c3e13d8c85d32
[260413-master]:  https://github.com/official-stockfish/Stockfish/commit/e508494a9985a5d54e77df694e8f160bb3346de3
[260413-raw1]:    https://tests.stockfishchess.org/tests/stats/517a569e8f0c3e13d8c85d32
[280413-dif]:     https://github.com/official-stockfish/Stockfish/compare/3caeabf73b...06b9140e5c
[280413-elo1]:    https://tests.stockfishchess.org/tests/view/517f5f538f0c3e0fd9df8d35
[280413-master]:  https://github.com/official-stockfish/Stockfish/commit/06b9140e5ccd9e3579315ea2abb2ba93126c48fa
[280413-raw1]:    https://tests.stockfishchess.org/tests/stats/517f5f538f0c3e0fd9df8d35
[Stockfish 3]:    https://github.com/official-stockfish/Stockfish/commit/aa2368a6878a867fe63247ee2adf2fde3dfe22be
[SF3DP]:          https://user-images.githubusercontent.com/64992190/156417306-225679a1-f73b-4dd8-9fc7-390cca2c6e4f.png "Development Progress"
[SF3RN]:          https://stockfishchess.org/blog/2013/stockfish-3/ "Release Notes"
[300413-dif]:     https://github.com/official-stockfish/Stockfish/compare/3caeabf73b...aa2368a687
[160513-dif]:     https://github.com/official-stockfish/Stockfish/compare/aa2368a687...f7c013edd0
[160513-elo1]:    https://tests.stockfishchess.org/tests/view/519547768f0c3e3efd273e4f
[160513-master]:  https://github.com/official-stockfish/Stockfish/commit/f7c013edd08a0e2d26491eb087c145e103e0f708
[160513-raw1]:    https://tests.stockfishchess.org/tests/stats/519547768f0c3e3efd273e4f
[230513-dif]:     https://github.com/official-stockfish/Stockfish/compare/aa2368a687...d4a02b135d
[230513-elo1]:    https://tests.stockfishchess.org/tests/view/51a02c038f0c3e3acadfbb11
[230513-master]:  https://github.com/official-stockfish/Stockfish/commit/d4a02b135deade2f3273716ccedb6f8a97316263
[230513-raw1]:    https://tests.stockfishchess.org/tests/stats/51a02c038f0c3e3acadfbb11
[310513-dif]:     https://github.com/official-stockfish/Stockfish/compare/aa2368a687...d8b266af8b
[310513-elo1]:    https://tests.stockfishchess.org/tests/view/51a8c12a8f0c3e6ac564d865
[310513-master]:  https://github.com/official-stockfish/Stockfish/commit/d8b266af8b714a86b815bb83d2b47f038137d604
[310513-raw1]:    https://tests.stockfishchess.org/tests/stats/51a8c12a8f0c3e6ac564d865
[230613-dif]:     https://github.com/official-stockfish/Stockfish/compare/aa2368a687...17d41b3861
[230613-elo1]:    https://tests.stockfishchess.org/tests/view/51c6daa18f0c3e355c8e0aef
[230613-master]:  https://github.com/official-stockfish/Stockfish/commit/17d41b386117f3b93daeb3a183f7a12e46812cdb
[230613-raw1]:    https://tests.stockfishchess.org/tests/stats/51c6daa18f0c3e355c8e0aef
[030713-dif]:     https://github.com/official-stockfish/Stockfish/compare/aa2368a687...a55fb76dcc
[030713-elo1]:    https://tests.stockfishchess.org/tests/view/51d459d10ebc590f75531fef
[030713-master]:  https://github.com/official-stockfish/Stockfish/commit/a55fb76dcc66c9cc17a81a9a99dd506108ee1fee
[030713-raw1]:    https://tests.stockfishchess.org/tests/stats/51d459d10ebc590f75531fef
[130713-dif]:     https://github.com/official-stockfish/Stockfish/compare/aa2368a687...4ede49cd85
[130713-elo1]:    https://tests.stockfishchess.org/tests/view/51e17aad0ebc595218f6a77f
[130713-master]:  https://github.com/official-stockfish/Stockfish/commit/4ede49cd850392f28bc9da9537c111d2c3f0b297
[130713-raw1]:    https://tests.stockfishchess.org/tests/stats/51e17aad0ebc595218f6a77f
[190713-dif]:     https://github.com/official-stockfish/Stockfish/compare/aa2368a687...4b3a0fdab0
[190713-elo1]:    https://tests.stockfishchess.org/tests/view/51e8da3c0ebc59080383cfde
[190713-master]:  https://github.com/official-stockfish/Stockfish/commit/4b3a0fdab03a7529ede42891963d3036712a0bd5
[190713-raw1]:    https://tests.stockfishchess.org/tests/stats/51e8da3c0ebc59080383cfde
[250713-dif]:     https://github.com/official-stockfish/Stockfish/compare/aa2368a687...7487eb0dca
[250713-elo1]:    https://tests.stockfishchess.org/tests/view/51f20d9b0ebc59080383d06a
[250713-master]:  https://github.com/official-stockfish/Stockfish/commit/7487eb0dcae93731330f06c7d289ca156487a16f
[250713-raw1]:    https://tests.stockfishchess.org/tests/stats/51f20d9b0ebc59080383d06a
[030813-dif]:     https://github.com/official-stockfish/Stockfish/compare/aa2368a687...f31847302d
[030813-elo1]:    https://tests.stockfishchess.org/tests/view/51ff4e6d0ebc59344346bf77
[030813-master]:  https://github.com/official-stockfish/Stockfish/commit/f31847302d4ec62f4da7d22447d6c9fbf36230dc
[030813-raw1]:    https://tests.stockfishchess.org/tests/stats/51ff4e6d0ebc59344346bf77
[180813-dif]:     https://github.com/official-stockfish/Stockfish/compare/aa2368a687...91c2c44fb1
[180813-elo1]:    https://tests.stockfishchess.org/tests/view/521077fb0ebc593f4bb9a39d
[180813-master]:  https://github.com/official-stockfish/Stockfish/commit/91c2c44fb1987e3587a9b1037ce6a34369995ba2
[180813-raw1]:    https://tests.stockfishchess.org/tests/stats/521077fb0ebc593f4bb9a39d
[Stockfish 4]:    https://github.com/official-stockfish/Stockfish/commit/4d120ee02edff250a6661e63d913e70efc37e2b6
[SF4DP]:          https://user-images.githubusercontent.com/64992190/156417121-89472d65-0d79-496d-a660-8073de2f1e45.png "Development Progress"
[SF4RN]:          https://stockfishchess.org/blog/2013/stockfish-4/ "Release Notes"
[200813-dif]:     https://github.com/official-stockfish/Stockfish/compare/aa2368a687...4d120ee02e
[290813-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...5d90c149b5
[290813-elo1]:    https://tests.stockfishchess.org/tests/view/521fbafc0ebc5972cf4733d6
[290813-master]:  https://github.com/official-stockfish/Stockfish/commit/5d90c149b5804403e5e8c1a25d0b37577b059712
[290813-raw1]:    https://tests.stockfishchess.org/tests/stats/521fbafc0ebc5972cf4733d6
[010913-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...849b089a63
[010913-elo1]:    https://tests.stockfishchess.org/tests/view/5224c2350ebc594ff262acc7
[010913-master]:  https://github.com/official-stockfish/Stockfish/commit/849b089a63cb40833006704fb6e3fc66e8010dfa
[010913-raw1]:    https://tests.stockfishchess.org/tests/stats/5224c2350ebc594ff262acc7
[050913-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...10b53e1c5e
[050913-elo1]:    https://tests.stockfishchess.org/tests/view/5228bc7b0ebc5909cbaa79be
[050913-master]:  https://github.com/official-stockfish/Stockfish/commit/10b53e1c5e6aeba156eb5c02afccfd7db1f84d16
[050913-raw1]:    https://tests.stockfishchess.org/tests/stats/5228bc7b0ebc5909cbaa79be
[070913-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...0515ad0fb0
[070913-elo1]:    https://tests.stockfishchess.org/tests/view/522bcb1c0ebc592ee68dc04a
[070913-master]:  https://github.com/official-stockfish/Stockfish/commit/0515ad0fb0f2d46ee60288b0541cea495e6c90ef
[070913-raw1]:    https://tests.stockfishchess.org/tests/stats/522bcb1c0ebc592ee68dc04a
[110913-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...4803d5772c
[110913-elo1]:    https://tests.stockfishchess.org/tests/view/5230d4630ebc5963f25cba15
[110913-master]:  https://github.com/official-stockfish/Stockfish/commit/4803d5772c120121dad6bad78cc2b6be5c24fb1f
[110913-raw1]:    https://tests.stockfishchess.org/tests/stats/5230d4630ebc5963f25cba15
[120913-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...27f2ce8f6e
[120913-elo1]:    https://tests.stockfishchess.org/tests/view/5231631d0ebc5963f25cba49
[120913-master]:  https://github.com/official-stockfish/Stockfish/commit/27f2ce8f6e8462bd9be4b201dd95fc2df17aafe6
[120913-raw1]:    https://tests.stockfishchess.org/tests/stats/5231631d0ebc5963f25cba49
[130913-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...fc17d0de77
[130913-elo1]:    https://tests.stockfishchess.org/tests/view/523339200ebc59749a54ac84
[130913-master]:  https://github.com/official-stockfish/Stockfish/commit/fc17d0de7748b68bddc5cd7f97a6c15ebc7adaac
[130913-raw1]:    https://tests.stockfishchess.org/tests/stats/523339200ebc59749a54ac84
[160913-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...77b5ee0117
[160913-elo1]:    https://tests.stockfishchess.org/tests/view/5236af460ebc59749a54ad38
[160913-master]:  https://github.com/official-stockfish/Stockfish/commit/77b5ee0117e86736817cf90f64055dce1ddbc55e
[160913-raw1]:    https://tests.stockfishchess.org/tests/stats/5236af460ebc59749a54ad38
[230913-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...7b2cda95d9
[230913-elo1]:    https://tests.stockfishchess.org/tests/view/5240800d0ebc595ff2f50ab9
[230913-master]:  https://github.com/official-stockfish/Stockfish/commit/7b2cda95d9d697a047ac8df33d3805ba77590a8f
[230913-raw1]:    https://tests.stockfishchess.org/tests/stats/5240800d0ebc595ff2f50ab9
[280913-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...cca34e234c
[280913-elo1]:    https://tests.stockfishchess.org/tests/view/52479d200ebc591a31ad9203
[280913-master]:  https://github.com/official-stockfish/Stockfish/commit/cca34e234cc98ed4b61e75a25f8cd0d917c2a3fa
[280913-raw1]:    https://tests.stockfishchess.org/tests/stats/52479d200ebc591a31ad9203
[290913-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...bd1c3ed7e3
[290913-elo1]:    https://tests.stockfishchess.org/tests/view/524baf1b0ebc5963752e0503
[290913-master]:  https://github.com/official-stockfish/Stockfish/commit/bd1c3ed7e32d3df0ceb29cb6959599e3cac2057c
[290913-raw1]:    https://tests.stockfishchess.org/tests/stats/524baf1b0ebc5963752e0503
[081013A-dif]:    https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...984ee9d05b
[081013A-elo1]:   https://tests.stockfishchess.org/tests/view/525446ab0ebc593ba5ae7100
[081013A-master]: https://github.com/official-stockfish/Stockfish/commit/984ee9d05b6b1916e564047b2a0b8f117f911bca
[081013A-raw1]:   https://tests.stockfishchess.org/tests/stats/525446ab0ebc593ba5ae7100
[081013B-dif]:    https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...bb83a417cb
[081013B-elo1]:   https://tests.stockfishchess.org/tests/view/52545c850ebc593ba5ae7104
[081013B-master]: https://github.com/official-stockfish/Stockfish/commit/bb83a417cb708e105c88052809ddfdf308b55aa9
[081013B-raw1]:   https://tests.stockfishchess.org/tests/stats/52545c850ebc593ba5ae7104
[091013-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...b15e148b5e
[091013-elo1]:    https://tests.stockfishchess.org/tests/view/52558f3b0ebc593ba5ae7135
[091013-master]:  https://github.com/official-stockfish/Stockfish/commit/b15e148b5e8929cfc17a388c79fbf4acdc0712f6
[091013-raw1]:    https://tests.stockfishchess.org/tests/stats/52558f3b0ebc593ba5ae7135
[141013-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...5aeb907fa1
[141013-elo1]:    https://tests.stockfishchess.org/tests/view/525c61c80ebc5951f87d21f3
[141013-master]:  https://github.com/official-stockfish/Stockfish/commit/5aeb907fa19afb22c92b3076d3ff73386cf7755c
[141013-raw1]:    https://tests.stockfishchess.org/tests/stats/525c61c80ebc5951f87d21f3
[181013-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...25cb851f8a
[181013-elo1]:    https://tests.stockfishchess.org/tests/view/5260f1e60ebc5951f87d229e
[181013-master]:  https://github.com/official-stockfish/Stockfish/commit/25cb851f8aa914634666789473a7809695dec6d1
[181013-raw1]:    https://tests.stockfishchess.org/tests/stats/5260f1e60ebc5951f87d229e
[191013-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...4bc2374450
[191013-elo1]:    https://tests.stockfishchess.org/tests/view/52625f270ebc5951f87d22ce
[191013-master]:  https://github.com/official-stockfish/Stockfish/commit/4bc2374450e30101392510006373a4a9ae2da4fd
[191013-raw1]:    https://tests.stockfishchess.org/tests/stats/52625f270ebc5951f87d22ce
[201013-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...97015afce8
[201013-elo1]:    https://tests.stockfishchess.org/tests/view/526450660ebc594568789520
[201013-master]:  https://github.com/official-stockfish/Stockfish/commit/97015afce834a68be4a955768caab7152834d7d8
[201013-raw1]:    https://tests.stockfishchess.org/tests/stats/526450660ebc594568789520
[221013-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...2c825294ec
[221013-elo1]:    https://tests.stockfishchess.org/tests/view/5266a0280ebc595f6d3486d3
[221013-master]:  https://github.com/official-stockfish/Stockfish/commit/2c825294ecbc7c959af9bc05300efd137d9ec7c6
[221013-raw1]:    https://tests.stockfishchess.org/tests/stats/5266a0280ebc595f6d3486d3
[241013-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...48f38f3092
[241013-elo1]:    https://tests.stockfishchess.org/tests/view/5269abe70ebc597fb21bb8fc
[241013-master]:  https://github.com/official-stockfish/Stockfish/commit/48f38f3092626f0dfef3728568ad5d85ca6c2f92
[241013-raw1]:    https://tests.stockfishchess.org/tests/stats/5269abe70ebc597fb21bb8fc
[281013-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...3cc47edf62
[281013-elo1]:    https://tests.stockfishchess.org/tests/view/52705c1a0ebc5936609edfcc
[281013-master]:  https://github.com/official-stockfish/Stockfish/commit/3cc47edf622b1d12a37b3637cae503d6862437c4
[281013-raw1]:    https://tests.stockfishchess.org/tests/stats/52705c1a0ebc5936609edfcc
[011113-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...a3a0df92a3
[011113-elo1]:    https://tests.stockfishchess.org/tests/view/5273658c0ebc5936609ee076
[011113-master]:  https://github.com/official-stockfish/Stockfish/commit/a3a0df92a3ed5ce7c98ff596e687d3d6533590c8
[011113-raw1]:    https://tests.stockfishchess.org/tests/stats/5273658c0ebc5936609ee076
[091113-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...eed508b444
[091113-elo1]:    https://tests.stockfishchess.org/tests/view/527e00050ebc5945a2478d7b
[091113-master]:  https://github.com/official-stockfish/Stockfish/commit/eed508b4445057cd26bfb95ab5cd754ac96629fd
[091113-raw1]:    https://tests.stockfishchess.org/tests/stats/527e00050ebc5945a2478d7b
[101113-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...4ef6b2c32a
[101113-elo1]:    https://tests.stockfishchess.org/tests/view/52803e7a0ebc594ba1fac466
[101113-master]:  https://github.com/official-stockfish/Stockfish/commit/4ef6b2c32a0f4e7b6193349312da5e335d48416b
[101113-raw1]:    https://tests.stockfishchess.org/tests/stats/52803e7a0ebc594ba1fac466
[111113-dif]:     https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...9763c69fa5
[111113-elo1]:    https://tests.stockfishchess.org/tests/view/5281e2820ebc594ba1fac4a5
[111113-master]:  https://github.com/official-stockfish/Stockfish/commit/9763c69fa5683accd7e81786977be4b195370a7b
[111113-raw1]:    https://tests.stockfishchess.org/tests/stats/5281e2820ebc594ba1fac4a5
[291113A-dif]:    https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...67e5581e37
[291113A-elo1]:   https://tests.stockfishchess.org/tests/view/529939330ebc5903719161c0
[291113A-master]: https://github.com/official-stockfish/Stockfish/commit/67e5581e37df2c7481be6261dcefa9fb41439c81
[291113A-raw1]:   https://tests.stockfishchess.org/tests/stats/529939330ebc5903719161c0
[Stockfish DD]:   https://github.com/official-stockfish/Stockfish/commit/c5bb9b9da943c49fbead1507ba7213bd7fb5e415
[SFDDDP]:         https://user-images.githubusercontent.com/64992190/156417012-2f1670a7-583d-4519-b86b-f3604c38d0d6.png "Development Progress"
[SFDDRN]:         https://stockfishchess.org/blog/2013/stockfish-dd/ "Release Notes"
[291113B-dif]:    https://github.com/official-stockfish/Stockfish/compare/4d120ee02e...c5bb9b9da9
[091213-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...8e9d4081ee
[091213-elo1]:    https://tests.stockfishchess.org/tests/view/52a61e9e0ebc5949c4e733f6
[091213-master]:  https://github.com/official-stockfish/Stockfish/commit/8e9d4081ee9def12f50dbd3169b765839fcb4c86
[091213-raw1]:    https://tests.stockfishchess.org/tests/stats/52a61e9e0ebc5949c4e733f6
[191213-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...26689d8c2a
[191213-elo1]:    https://tests.stockfishchess.org/tests/view/52b462600ebc5954c3432bbb
[191213-master]:  https://github.com/official-stockfish/Stockfish/commit/26689d8c2ae506e4da1a5654fcfdfe04886c3692
[191213-raw1]:    https://tests.stockfishchess.org/tests/stats/52b462600ebc5954c3432bbb
[231213-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...899a2c033e
[231213-elo1]:    https://tests.stockfishchess.org/tests/view/52b8fab60ebc5954c3432c6e
[231213-master]:  https://github.com/official-stockfish/Stockfish/commit/899a2c033e2e74d3da97c7aefff74fb05a59db0a
[231213-raw1]:    https://tests.stockfishchess.org/tests/stats/52b8fab60ebc5954c3432c6e
[291213-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...f7742669cb
[291213-elo1]:    https://tests.stockfishchess.org/tests/view/52c0bf040ebc5954c3432e1d
[291213-master]:  https://github.com/official-stockfish/Stockfish/commit/f7742669cb52dff7a64bd1a9ba466e333abb87bc
[291213-raw1]:    https://tests.stockfishchess.org/tests/stats/52c0bf040ebc5954c3432e1d
[020114-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...8454d871ec
[020114-elo1]:    https://tests.stockfishchess.org/tests/view/52c5ad780ebc5954c3432f07
[020114-master]:  https://github.com/official-stockfish/Stockfish/commit/8454d871ec105749fb5e2e7e9aea9e7c25cfdf6e
[020114-raw1]:    https://tests.stockfishchess.org/tests/stats/52c5ad780ebc5954c3432f07
[080114-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...262c380c4b
[080114-elo1]:    https://tests.stockfishchess.org/tests/view/52ce26de0ebc594082ffce98
[080114-master]:  https://github.com/official-stockfish/Stockfish/commit/262c380c4bf8dcadf07741ec458a9e6565ecf8b4
[080114-raw1]:    https://tests.stockfishchess.org/tests/stats/52ce26de0ebc594082ffce98
[140114-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...53ab32ef0b
[140114-elo1]:    https://tests.stockfishchess.org/tests/view/52d584ce0ebc590891e7abc5
[140114-master]:  https://github.com/official-stockfish/Stockfish/commit/53ab32ef0b6e47d8d962f8c1fccd32d3c22f138c
[140114-raw1]:    https://tests.stockfishchess.org/tests/stats/52d584ce0ebc590891e7abc5
[190114-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...a08a21d5a0
[190114-elo1]:    https://tests.stockfishchess.org/tests/view/52de28590ebc59025698f817
[190114-master]:  https://github.com/official-stockfish/Stockfish/commit/a08a21d5a0b5aafcdb340364bf73b13d852349a0
[190114-raw1]:    https://tests.stockfishchess.org/tests/stats/52de28590ebc59025698f817
[290114-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...77341f67f3
[290114-elo1]:    https://tests.stockfishchess.org/tests/view/52e936590ebc59025698f9ce
[290114-master]:  https://github.com/official-stockfish/Stockfish/commit/77341f67f30456dc456177062309ad5e73e2e1a4
[290114-raw1]:    https://tests.stockfishchess.org/tests/stats/52e936590ebc59025698f9ce
[090214-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...ddeb01612b
[090214-elo1]:    https://tests.stockfishchess.org/tests/view/52fa72e90ebc5901df50f9c8
[090214-master]:  https://github.com/official-stockfish/Stockfish/commit/ddeb01612b122bbeeb59a26ba6f8c6f1e4283199
[090214-raw1]:    https://tests.stockfishchess.org/tests/stats/52fa72e90ebc5901df50f9c8
[220214-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...0949f06a60
[220214-elo1]:    https://tests.stockfishchess.org/tests/view/530fbd8a0ebc591a7be1a0a8
[220214-master]:  https://github.com/official-stockfish/Stockfish/commit/0949f06a60579a4dd70ad5bf66c694988528596e
[220214-raw1]:    https://tests.stockfishchess.org/tests/stats/530fbd8a0ebc591a7be1a0a8
[260214-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...b917cd275e
[260214-elo1]:    https://tests.stockfishchess.org/tests/view/530eebad0ebc591a7be1a097
[260214-master]:  https://github.com/official-stockfish/Stockfish/commit/b917cd275e6f9825bc860d2fc7b7d67dacef2915
[260214-raw1]:    https://tests.stockfishchess.org/tests/stats/530eebad0ebc591a7be1a097
[140314-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...36c381154b
[140314-elo1]:    https://tests.stockfishchess.org/tests/view/532352350ebc590d680856df
[140314-master]:  https://github.com/official-stockfish/Stockfish/commit/36c381154bcfb23b1ba9f1178c9eb9232099b821
[140314-raw1]:    https://tests.stockfishchess.org/tests/stats/532352350ebc590d680856df
[240314-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...865b71309c
[240314-elo1]:    https://tests.stockfishchess.org/tests/view/53311b1a0ebc597b9673c33b
[240314-master]:  https://github.com/official-stockfish/Stockfish/commit/865b71309c4dd5c6c67c9c9422df5790cbb22440
[240314-raw1]:    https://tests.stockfishchess.org/tests/stats/53311b1a0ebc597b9673c33b
[080414-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...5c75455c8e
[080414-elo1]:    https://tests.stockfishchess.org/tests/view/53447c7c0ebc593d8c927638
[080414-master]:  https://github.com/official-stockfish/Stockfish/commit/5c75455c8ea998bb3e60bafbc3fab850bb877187
[080414-raw1]:    https://tests.stockfishchess.org/tests/stats/53447c7c0ebc593d8c927638
[120414-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...b2c0634d48
[120414-elo1]:    https://tests.stockfishchess.org/tests/view/534931e80ebc5909cec073da
[120414-master]:  https://github.com/official-stockfish/Stockfish/commit/b2c0634d4898a78a9e82fca9197467d442e5cb95
[120414-raw1]:    https://tests.stockfishchess.org/tests/stats/534931e80ebc5909cec073da
[210414-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...56273fca1e
[210414-elo1]:    https://tests.stockfishchess.org/tests/view/5355380a0ebc5949818c04c0
[210414-master]:  https://github.com/official-stockfish/Stockfish/commit/56273fca1edc51ffa0efc73715609f428c000c97
[210414-raw1]:    https://tests.stockfishchess.org/tests/stats/5355380a0ebc5949818c04c0
[250414-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...7ddbcf7e87
[250414-elo1]:    https://tests.stockfishchess.org/tests/view/535b388d0ebc593bee1c3bc2
[250414-master]:  https://github.com/official-stockfish/Stockfish/commit/7ddbcf7e87a0b0c882d8d33841bd7ae53969619d
[250414-raw1]:    https://tests.stockfishchess.org/tests/stats/535b388d0ebc593bee1c3bc2
[040514-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...5413fda739
[040514-elo1]:    https://tests.stockfishchess.org/tests/view/536bfe840ebc597126891867
[040514-master]:  https://github.com/official-stockfish/Stockfish/commit/5413fda7397f8ffe32e41b9c7f13297c39929f5c
[040514-raw1]:    https://tests.stockfishchess.org/tests/stats/536bfe840ebc597126891867
[130514-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...5ec63eb6b6
[130514-elo1]:    https://tests.stockfishchess.org/tests/view/53752dc30ebc5935dbfeea67
[130514-master]:  https://github.com/official-stockfish/Stockfish/commit/5ec63eb6b6f43cbd4e25b8f8b97bc8980dbbabef
[130514-raw1]:    https://tests.stockfishchess.org/tests/stats/53752dc30ebc5935dbfeea67
[170514-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...5e03734eac
[170514-elo1]:    https://tests.stockfishchess.org/tests/view/5382e5190ebc59646b252a28
[170514-master]:  https://github.com/official-stockfish/Stockfish/commit/5e03734eacc8e52a6c92be19e73b69ab3e398518
[170514-raw1]:    https://tests.stockfishchess.org/tests/stats/5382e5190ebc59646b252a28
[240514-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...495a0fa699
[240514-elo1]:    https://tests.stockfishchess.org/tests/view/53828e440ebc595e74193f03
[240514-master]:  https://github.com/official-stockfish/Stockfish/commit/495a0fa699fb3f8ed36fe343fbd910479df4e2f1
[240514-raw1]:    https://tests.stockfishchess.org/tests/stats/53828e440ebc595e74193f03
[Stockfish 5]:    https://github.com/official-stockfish/Stockfish/commit/54f8a9cb138a1bc0b0054b98f911fafd8d1b03ad
[SF5DP]:          https://user-images.githubusercontent.com/64992190/156416921-bd44dc86-a612-4963-b067-ba2b5e3547f5.png "Development Progress"
[SF5RN]:          https://stockfishchess.org/blog/2014/stockfish-5/ "Release Notes"
[310514-dif]:     https://github.com/official-stockfish/Stockfish/compare/c5bb9b9da9...54f8a9cb13
[030614-dif]:     https://github.com/official-stockfish/Stockfish/compare/54f8a9cb13...adeded29fb
[030614-elo1]:    https://tests.stockfishchess.org/tests/view/538e10500ebc5940a3b7f018
[030614-master]:  https://github.com/official-stockfish/Stockfish/commit/adeded29fb6ce483bbbafaa0f67aa086cad968f9
[030614-raw1]:    https://tests.stockfishchess.org/tests/stats/538e10500ebc5940a3b7f018
[110614-dif]:     https://github.com/official-stockfish/Stockfish/compare/54f8a9cb13...84dabe5982
[110614-elo1]:    https://tests.stockfishchess.org/tests/view/539d0ccf0ebc59659be39682
[110614-master]:  https://github.com/official-stockfish/Stockfish/commit/84dabe5982dab5ee65770eeb77c4f966db9514f8
[110614-raw1]:    https://tests.stockfishchess.org/tests/stats/539d0ccf0ebc59659be39682
[290614-dif]:     https://github.com/official-stockfish/Stockfish/compare/54f8a9cb13...ffedfa3354
[290614-elo1]:    https://tests.stockfishchess.org/tests/view/53b06b140ebc5948a2398082
[290614-master]:  https://github.com/official-stockfish/Stockfish/commit/ffedfa33542a7de7d87fd545ea0a4b2fef8f8c6e
[290614-raw1]:    https://tests.stockfishchess.org/tests/stats/53b06b140ebc5948a2398082
[220714-dif]:     https://github.com/official-stockfish/Stockfish/compare/54f8a9cb13...4758fd31b1
[220714-elo1]:    https://tests.stockfishchess.org/tests/view/53cff3620ebc592c34a4a383
[220714-master]:  https://github.com/official-stockfish/Stockfish/commit/4758fd31b17129530dfeb81119b423c5bdde704a
[220714-raw1]:    https://tests.stockfishchess.org/tests/stats/53cff3620ebc592c34a4a383
[060814-dif]:     https://github.com/official-stockfish/Stockfish/compare/54f8a9cb13...9da015517c
[060814-elo1]:    https://tests.stockfishchess.org/tests/view/53e207dd0ebc592db1a06475
[060814-master]:  https://github.com/official-stockfish/Stockfish/commit/9da015517c20e9c5b8e0ef6e7103e60404211baa
[060814-raw1]:    https://tests.stockfishchess.org/tests/stats/53e207dd0ebc592db1a06475
[040914-dif]:     https://github.com/official-stockfish/Stockfish/compare/54f8a9cb13...cd065dd584
[040914-elo1]:    https://tests.stockfishchess.org/tests/view/54144bf40ebc5923f6d66d54
[040914-master]:  https://github.com/official-stockfish/Stockfish/commit/cd065dd584d080f56735007f7ff52bd1ada2fea3
[040914-raw1]:    https://tests.stockfishchess.org/tests/stats/54144bf40ebc5923f6d66d54
[270914-dif]:     https://github.com/official-stockfish/Stockfish/compare/54f8a9cb13...ea9c424bba
[270914-elo1]:    https://tests.stockfishchess.org/tests/view/54276b500ebc59568afa4265
[270914-master]:  https://github.com/official-stockfish/Stockfish/commit/ea9c424bba07d522d4acff54f2883fc124574e50
[270914-raw1]:    https://tests.stockfishchess.org/tests/stats/54276b500ebc59568afa4265
[151014-dif]:     https://github.com/official-stockfish/Stockfish/compare/54f8a9cb13...480682b670
[151014-elo1]:    https://tests.stockfishchess.org/tests/view/54411bc40ebc59731a7ea6ae
[151014-master]:  https://github.com/official-stockfish/Stockfish/commit/480682b67097160bfc25e52ab02facffeec104f0
[151014-raw1]:    https://tests.stockfishchess.org/tests/stats/54411bc40ebc59731a7ea6ae
[011114-dif]:     https://github.com/official-stockfish/Stockfish/compare/54f8a9cb13...79fa72f392
[011114-elo1]:    https://tests.stockfishchess.org/tests/view/545559640ebc59410ea4e5fa
[011114-master]:  https://github.com/official-stockfish/Stockfish/commit/79fa72f392343fb93c16c133dedc3dbdf795e746
[011114-raw1]:    https://tests.stockfishchess.org/tests/stats/545559640ebc59410ea4e5fa
[101114-dif]:     https://github.com/official-stockfish/Stockfish/compare/54f8a9cb13...c6d45c60b5
[101114-elo1]:    https://tests.stockfishchess.org/tests/view/5463d2e40ebc592ab9e50ff7
[101114-master]:  https://github.com/official-stockfish/Stockfish/commit/c6d45c60b516e799526f1163733b74b23fc1b63c
[101114-raw1]:    https://tests.stockfishchess.org/tests/stats/5463d2e40ebc592ab9e50ff7
[251114-dif]:     https://github.com/official-stockfish/Stockfish/compare/54f8a9cb13...fe07ae4cb4
[251114-elo1]:    https://tests.stockfishchess.org/tests/view/5479f1ef0ebc5910c1f22551
[251114-master]:  https://github.com/official-stockfish/Stockfish/commit/fe07ae4cb4c2553fb48cab44c502ba766d1f09ce
[251114-raw1]:    https://tests.stockfishchess.org/tests/stats/5479f1ef0ebc5910c1f22551
[071214-dif]:     https://github.com/official-stockfish/Stockfish/compare/54f8a9cb13...158864270a
[071214-elo1]:    https://tests.stockfishchess.org/tests/view/548716860ebc59615b9c1cda
[071214-master]:  https://github.com/official-stockfish/Stockfish/commit/158864270a055fe20dca4a87f4b7a8aa9cedfeb9
[071214-raw1]:    https://tests.stockfishchess.org/tests/stats/548716860ebc59615b9c1cda
[221214-dif]:     https://github.com/official-stockfish/Stockfish/compare/54f8a9cb13...296534f234
[221214-elo1]:    https://tests.stockfishchess.org/tests/view/549e0cfa0ebc595444a9aa4f
[221214-master]:  https://github.com/official-stockfish/Stockfish/commit/296534f23489e6d95ba7ce1bb35e8a2cbf9a5a9d
[221214-raw1]:    https://tests.stockfishchess.org/tests/stats/549e0cfa0ebc595444a9aa4f
[070115-dif]:     https://github.com/official-stockfish/Stockfish/compare/54f8a9cb13...aea2fde611
[070115-elo1]:    https://tests.stockfishchess.org/tests/view/54ae6da20ebc59608c5caffe
[070115-master]:  https://github.com/official-stockfish/Stockfish/commit/aea2fde6117be2fbda1caa62c842dea766780be5
[070115-raw1]:    https://tests.stockfishchess.org/tests/stats/54ae6da20ebc59608c5caffe
[180115-dif]:     https://github.com/official-stockfish/Stockfish/compare/54f8a9cb13...97a034ad3e
[180115-elo1]:    https://tests.stockfishchess.org/tests/view/54bbf1c10ebc59238ddbd4d0
[180115-master]:  https://github.com/official-stockfish/Stockfish/commit/97a034ad3e8b25f0e8e1dd03d31f4689180f7547
[180115-raw1]:    https://tests.stockfishchess.org/tests/stats/54bbf1c10ebc59238ddbd4d0
[Stockfish 6]:    https://github.com/official-stockfish/Stockfish/commit/5b555525d2f9cbff446b7461d1317948e8e21cd1
[SF6DP]:          https://user-images.githubusercontent.com/64992190/156416818-2c46d7cf-6cf1-40be-ba6e-c19ceed3e6b0.png "Development Progress"
[SF6RN]:          https://stockfishchess.org/blog/2015/stockfish-6/ "Release Notes"
[270115-dif]:     https://github.com/official-stockfish/Stockfish/compare/54f8a9cb13...5b555525d2
[080215-dif]:     https://github.com/official-stockfish/Stockfish/compare/5b555525d2...e118570038
[080215-elo1]:    https://tests.stockfishchess.org/tests/view/54d869130ebc592194804134
[080215-master]:  https://github.com/official-stockfish/Stockfish/commit/e118570038f2d9b668b445fe6d31df94151a717b
[080215-raw1]:    https://tests.stockfishchess.org/tests/stats/54d869130ebc592194804134
[190315-dif]:     https://github.com/official-stockfish/Stockfish/compare/5b555525d2...ebf3735754
[190315-elo1]:    https://tests.stockfishchess.org/tests/view/550c678f0ebc5902160ec2f7
[190315-master]:  https://github.com/official-stockfish/Stockfish/commit/ebf3735754d015dfda72930a676b8b43f0614086
[190315-raw1]:    https://tests.stockfishchess.org/tests/stats/550c678f0ebc5902160ec2f7
[290315-dif]:     https://github.com/official-stockfish/Stockfish/compare/5b555525d2...60beb18efc
[290315-elo1]:    https://tests.stockfishchess.org/tests/view/5517c0790ebc5902160ec596
[290315-master]:  https://github.com/official-stockfish/Stockfish/commit/60beb18efcb3c19b36a164a50e32b6ba6e24e7c4
[290315-raw1]:    https://tests.stockfishchess.org/tests/stats/5517c0790ebc5902160ec596
[100415-dif]:     https://github.com/official-stockfish/Stockfish/compare/5b555525d2...a66c73deef
[100415-elo1]:    https://tests.stockfishchess.org/tests/view/55282b5c0ebc596367ee97e3
[100415-master]:  https://github.com/official-stockfish/Stockfish/commit/a66c73deef420104e74b6645ee60e20b37fd8549
[100415-raw1]:    https://tests.stockfishchess.org/tests/stats/55282b5c0ebc596367ee97e3
[090515-dif]:     https://github.com/official-stockfish/Stockfish/compare/5b555525d2...eaeb63f1d0
[090515-elo1]:    https://tests.stockfishchess.org/tests/view/554e65190ebc5940ca5d6980
[090515-master]:  https://github.com/official-stockfish/Stockfish/commit/eaeb63f1d03aa71edf719605a31d121bf086a03d
[090515-raw1]:    https://tests.stockfishchess.org/tests/stats/554e65190ebc5940ca5d6980
[070615-dif]:     https://github.com/official-stockfish/Stockfish/compare/5b555525d2...ad87d707ff
[070615-elo1]:    https://tests.stockfishchess.org/tests/view/5573eeed0ebc5940ca5d7081
[070615-master]:  https://github.com/official-stockfish/Stockfish/commit/ad87d707fffeeac9aa1ae3e3e8d6fa2449ea1df9
[070615-raw1]:    https://tests.stockfishchess.org/tests/stats/5573eeed0ebc5940ca5d7081
[160715-dif]:     https://github.com/official-stockfish/Stockfish/compare/5b555525d2...4095ff0ee5
[160715-elo1]:    https://tests.stockfishchess.org/tests/view/55ab57b80ebc590abbe1bb68
[160715-master]:  https://github.com/official-stockfish/Stockfish/commit/4095ff0ee51bdc76c247bd11d5f3a7008974e2ad
[160715-raw1]:    https://tests.stockfishchess.org/tests/stats/55ab57b80ebc590abbe1bb68
[300715-dif]:     https://github.com/official-stockfish/Stockfish/compare/5b555525d2...68d61b80c6
[300715-elo1]:    https://tests.stockfishchess.org/tests/view/55bab2280ebc590abbe1bdeb
[300715-master]:  https://github.com/official-stockfish/Stockfish/commit/68d61b80c60a81055a2ffb2e251a237b979e9b31
[300715-raw1]:    https://tests.stockfishchess.org/tests/stats/55bab2280ebc590abbe1bdeb
[031015-dif]:     https://github.com/official-stockfish/Stockfish/compare/5b555525d2...83e19fbed5
[031015-elo1]:    https://tests.stockfishchess.org/tests/view/5611c5070ebc597e4f23e550
[031015-master]:  https://github.com/official-stockfish/Stockfish/commit/83e19fbed539fc05626d82afefde730bdcb344ab
[031015-raw1]:    https://tests.stockfishchess.org/tests/stats/5611c5070ebc597e4f23e550
[251015-dif]:     https://github.com/official-stockfish/Stockfish/compare/5b555525d2...00d9e9fd28
[251015-elo1]:    https://tests.stockfishchess.org/tests/view/562df8850ebc5964d34460a6
[251015-master]:  https://github.com/official-stockfish/Stockfish/commit/00d9e9fd283b31e63389af091b158dbc3fedfc0e
[251015-raw1]:    https://tests.stockfishchess.org/tests/stats/562df8850ebc5964d34460a6
[271215-dif]:     https://github.com/official-stockfish/Stockfish/compare/5b555525d2...a5c76d69c3
[271215-elo1]:    https://tests.stockfishchess.org/tests/view/5681810d0ebc5966b711a940
[271215-master]:  https://github.com/official-stockfish/Stockfish/commit/a5c76d69c346d620b6f7a300d4a33cc5867f4d64
[271215-raw1]:    https://tests.stockfishchess.org/tests/stats/5681810d0ebc5966b711a940
[Stockfish 7]:    https://github.com/official-stockfish/Stockfish/commit/dd9cf305816c84c2acfa11cae09a31c4d77cc5a5
[SF7DP]:          https://user-images.githubusercontent.com/64992190/156416613-a26e434d-37f9-47fc-a87e-7c3969d54dca.png "Development Progress"
[SF7RN]:          https://stockfishchess.org/blog/2016/stockfish-7/ "Release Notes"
[020116-dif]:     https://github.com/official-stockfish/Stockfish/compare/5b555525d2...dd9cf30581
[280116-dif]:     https://github.com/official-stockfish/Stockfish/compare/dd9cf30581...aedebe35cf
[280116-elo1]:    https://tests.stockfishchess.org/tests/view/56af108a0ebc590247cdfa63
[280116-master]:  https://github.com/official-stockfish/Stockfish/commit/aedebe35cfa38b543041bae97e91e8194738b202
[280116-raw1]:    https://tests.stockfishchess.org/tests/stats/56af108a0ebc590247cdfa63
[100316-dif]:     https://github.com/official-stockfish/Stockfish/compare/dd9cf30581...a273b6ef8c
[100316-elo1]:    https://tests.stockfishchess.org/tests/view/56e274540ebc59301a353b37
[100316-master]:  https://github.com/official-stockfish/Stockfish/commit/a273b6ef8c899f546cf585ace584a1b498c04144
[100316-raw1]:    https://tests.stockfishchess.org/tests/stats/56e274540ebc59301a353b37
[080416-dif]:     https://github.com/official-stockfish/Stockfish/compare/dd9cf30581...1cbba8d6fa
[080416-elo1]:    https://tests.stockfishchess.org/tests/view/5707ffdd0ebc59301a3543dc
[080416-master]:  https://github.com/official-stockfish/Stockfish/commit/1cbba8d6fadaae2c6e6df5c541c4e2b8a8bf5a0a
[080416-raw1]:    https://tests.stockfishchess.org/tests/stats/5707ffdd0ebc59301a3543dc
[200516-dif]:     https://github.com/official-stockfish/Stockfish/compare/dd9cf30581...71bfbb22fc
[200516-elo1]:    https://tests.stockfishchess.org/tests/view/573fd5a90ebc59301a354f9c
[200516-master]:  https://github.com/official-stockfish/Stockfish/commit/71bfbb22fce23f56b57d69b59a5cec1ff4b5aa03
[200516-raw1]:    https://tests.stockfishchess.org/tests/stats/573fd5a90ebc59301a354f9c
[100616-dif]:     https://github.com/official-stockfish/Stockfish/compare/dd9cf30581...7d2a79f037
[100616-elo1]:    https://tests.stockfishchess.org/tests/view/575c6ff20ebc59029919b409
[100616-master]:  https://github.com/official-stockfish/Stockfish/commit/7d2a79f0372d67f3d66bd07bf637eae02038831c
[100616-raw1]:    https://tests.stockfishchess.org/tests/stats/575c6ff20ebc59029919b409
[240716-dif]:     https://github.com/official-stockfish/Stockfish/compare/dd9cf30581...f2f3a06a1a
[240716-elo1]:    https://tests.stockfishchess.org/tests/view/579475b00ebc59099c1a6632
[240716-master]:  https://github.com/official-stockfish/Stockfish/commit/f2f3a06a1acfa14b3054bfd73d6c3966c326a7cc
[240716-raw1]:    https://tests.stockfishchess.org/tests/stats/579475b00ebc59099c1a6632
[180816-dif]:     https://github.com/official-stockfish/Stockfish/compare/dd9cf30581...e3af492142
[180816-elo1]:    https://tests.stockfishchess.org/tests/view/57b59da90ebc591c761f64e1
[180816-master]:  https://github.com/official-stockfish/Stockfish/commit/e3af492142c8aff71f50dbec025722d69b84f85e
[180816-raw1]:    https://tests.stockfishchess.org/tests/stats/57b59da90ebc591c761f64e1
[070916-dif]:     https://github.com/official-stockfish/Stockfish/compare/dd9cf30581...d909d10f33
[070916-elo1]:    https://tests.stockfishchess.org/tests/view/57d0e7b70ebc59030fbe5050
[070916-master]:  https://github.com/official-stockfish/Stockfish/commit/d909d10f33df023be46a2633608bdf655d1f5a62
[070916-raw1]:    https://tests.stockfishchess.org/tests/stats/57d0e7b70ebc59030fbe5050
[071016-dif]:     https://github.com/official-stockfish/Stockfish/compare/dd9cf30581...073eed590e
[071016-elo1]:    https://tests.stockfishchess.org/tests/view/57f9f64d0ebc59038170fb15
[071016-master]:  https://github.com/official-stockfish/Stockfish/commit/073eed590edf992ed3aeb6c754cb0b3b394fe79d
[071016-raw1]:    https://tests.stockfishchess.org/tests/stats/57f9f64d0ebc59038170fb15
[Stockfish 8]:    https://github.com/official-stockfish/Stockfish/commit/369eff437cc081eb4b8ab5f519cf3f86b79e87d0
[SF8DP]:          https://user-images.githubusercontent.com/64992190/156416476-2ce4e02c-62a1-4f0d-9430-d14368bca1a1.png "Development Progress"
[SF8RN]:          https://stockfishchess.org/blog/2016/stockfish-8/ "Release Notes"
[011116-dif]:     https://github.com/official-stockfish/Stockfish/compare/dd9cf30581...369eff437c
[311216-dif]:     https://github.com/official-stockfish/Stockfish/compare/369eff437c...43f6b33e50
[311216-elo1]:    https://tests.stockfishchess.org/tests/view/5867b55c0ebc5903140c639c
[311216-master]:  https://github.com/official-stockfish/Stockfish/commit/43f6b33e50c4bea354b963b0e1e47445c8298299
[311216-raw1]:    https://tests.stockfishchess.org/tests/stats/5867b55c0ebc5903140c639c
[290117-dif]:     https://github.com/official-stockfish/Stockfish/compare/369eff437c...fa24cc25a4
[290117-elo1]:    https://tests.stockfishchess.org/tests/view/588dc7620ebc5915193f7d19
[290117-master]:  https://github.com/official-stockfish/Stockfish/commit/fa24cc25a43da5ac41a086edda02dfc2e8e9b830
[290117-raw1]:    https://tests.stockfishchess.org/tests/stats/588dc7620ebc5915193f7d19
[080317-dif]:     https://github.com/official-stockfish/Stockfish/compare/369eff437c...c3d2e6aba9
[080317-elo1]:    https://tests.stockfishchess.org/tests/view/58c11dcf0ebc59035df32b75
[080317-master]:  https://github.com/official-stockfish/Stockfish/commit/c3d2e6aba981ecc0caf82f81a1d44e8c4954e151
[080317-raw1]:    https://tests.stockfishchess.org/tests/stats/58c11dcf0ebc59035df32b75
[200417-dif]:     https://github.com/official-stockfish/Stockfish/compare/369eff437c...ced29248c9
[200417-elo1]:    https://tests.stockfishchess.org/tests/view/58f92a310ebc59035df33d48
[200417-master]:  https://github.com/official-stockfish/Stockfish/commit/ced29248c93de7fc5a4e284807f8f052006e647c
[200417-raw1]:    https://tests.stockfishchess.org/tests/stats/58f92a310ebc59035df33d48
[070517-dif]:     https://github.com/official-stockfish/Stockfish/compare/369eff437c...6b4959e3e0
[070517-elo1]:    https://tests.stockfishchess.org/tests/view/59100d7c0ebc59035df343ef
[070517-master]:  https://github.com/official-stockfish/Stockfish/commit/6b4959e3e00035dbcabd74a6d49ce7d04008d62c
[070517-raw1]:    https://tests.stockfishchess.org/tests/stats/59100d7c0ebc59035df343ef
[210617-dif]:     https://github.com/official-stockfish/Stockfish/compare/369eff437c...77342126d8
[210617-elo1]:    https://tests.stockfishchess.org/tests/view/594b324e0ebc593ea732d332
[210617-master]:  https://github.com/official-stockfish/Stockfish/commit/77342126d8417469bd6a398cfc6c0594b1f02f82
[210617-raw1]:    https://tests.stockfishchess.org/tests/stats/594b324e0ebc593ea732d332
[260817-dif]:     https://github.com/official-stockfish/Stockfish/compare/369eff437c...d5f883ab29
[260817-elo1]:    https://tests.stockfishchess.org/tests/view/59a1a55a0ebc5916ff64aba4
[260817-master]:  https://github.com/official-stockfish/Stockfish/commit/d5f883ab29d43b35746ff605cf13c3722df56041
[260817-raw1]:    https://tests.stockfishchess.org/tests/stats/59a1a55a0ebc5916ff64aba4
[021017-dif]:     https://github.com/official-stockfish/Stockfish/compare/369eff437c...452e5154cf
[021017-elo1]:    https://tests.stockfishchess.org/tests/view/59d1e0770ebc5916ff64baf5
[021017-master]:  https://github.com/official-stockfish/Stockfish/commit/452e5154cf29ee46aa35a12dfb54bd24e4ed61de
[021017-raw1]:    https://tests.stockfishchess.org/tests/stats/59d1e0770ebc5916ff64baf5
[031117-dif]:     https://github.com/official-stockfish/Stockfish/compare/369eff437c...4bc11984fc
[031117-elo1]:    https://tests.stockfishchess.org/tests/view/59fcc7570ebc590ccbb8a151
[031117-master]:  https://github.com/official-stockfish/Stockfish/commit/4bc11984fc5a148ee8f1b55d6ac47c4a397cc8b8
[031117-raw1]:    https://tests.stockfishchess.org/tests/stats/59fcc7570ebc590ccbb8a151
[031217-dif]:     https://github.com/official-stockfish/Stockfish/compare/369eff437c...28b6a457c2
[031217-elo1]:    https://tests.stockfishchess.org/tests/view/5a23e7c10ebc590ccbb8b6d8
[031217-master]:  https://github.com/official-stockfish/Stockfish/commit/28b6a457c24d9202ba43a6d6703221250f0f8749
[031217-raw1]:    https://tests.stockfishchess.org/tests/stats/5a23e7c10ebc590ccbb8b6d8
[230118-dif]:     https://github.com/official-stockfish/Stockfish/compare/369eff437c...254d995e18
[230118-elo1]:    https://tests.stockfishchess.org/tests/view/5a673c8a0ebc590d945d5815
[230118-master]:  https://github.com/official-stockfish/Stockfish/commit/254d995e187d8ecd02c3e5613e43aab525e41e22
[230118-raw1]:    https://tests.stockfishchess.org/tests/stats/5a673c8a0ebc590d945d5815
[Stockfish 9]:    https://github.com/official-stockfish/Stockfish/commit/378c8bdbb8f930472fc4316aa6c417802294bbad
[SF9DP]:          https://user-images.githubusercontent.com/64992190/156416383-f40f1fda-6577-4b5e-b359-c5dd97620086.png "Development Progress"
[SF9RN]:          https://stockfishchess.org/blog/2018/stockfish-9/ "Release Notes"
[310118-dif]:     https://github.com/official-stockfish/Stockfish/compare/369eff437c...378c8bdbb8
[280218-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...94abc2a0cf
[280218-elo1]:    https://tests.stockfishchess.org/tests/view/5a96cfdb0ebc590297cc8d2b
[280218-master]:  https://github.com/official-stockfish/Stockfish/commit/94abc2a0cfa262e2e040886394c782af226bc1bd
[280218-raw1]:    https://tests.stockfishchess.org/tests/stats/5a96cfdb0ebc590297cc8d2b
[070318-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...82697f1193
[070318-elo1]:    https://tests.stockfishchess.org/tests/view/5aa06d050ebc590297cb62d9
[070318-master]:  https://github.com/official-stockfish/Stockfish/commit/82697f1193cc8c99c99c282361a3ada25c758243
[070318-raw1]:    https://tests.stockfishchess.org/tests/stats/5aa06d050ebc590297cb62d9
[130318-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...edf4c07d25
[130318-elo1]:    https://tests.stockfishchess.org/tests/view/5aa8e2540ebc5902978101c8
[130318-master]:  https://github.com/official-stockfish/Stockfish/commit/edf4c07d251f1d6c709d47969bfe1452194d9430
[130318-raw1]:    https://tests.stockfishchess.org/tests/stats/5aa8e2540ebc5902978101c8
[260318-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...f0f6da2d30
[260318-elo1]:    https://tests.stockfishchess.org/tests/view/5aba52ab0ebc5902a4743e6e
[260318-master]:  https://github.com/official-stockfish/Stockfish/commit/f0f6da2d30fc005fd0fa126ee1eefd11fe10a604
[260318-raw1]:    https://tests.stockfishchess.org/tests/stats/5aba52ab0ebc5902a4743e6e
[030418-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...04a228f9c8
[030418-elo1]:    https://tests.stockfishchess.org/tests/view/5ac5f0220ebc590305f0f5bd
[030418-master]:  https://github.com/official-stockfish/Stockfish/commit/04a228f9c83dafde1953e43b1906fc0929832976
[030418-raw1]:    https://tests.stockfishchess.org/tests/stats/5ac5f0220ebc590305f0f5bd
[070418-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...b88374b14a
[070418-elo1]:    https://tests.stockfishchess.org/tests/view/5ae5b0240ebc59442aa387d4
[070418-master]:  https://github.com/official-stockfish/Stockfish/commit/b88374b14a7baa2f8e4c37b16a2e653e7472adcc
[070418-raw1]:    https://tests.stockfishchess.org/tests/stats/5ae5b0240ebc59442aa387d4
[230418-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...aef7076c34
[230418-elo1]:    https://tests.stockfishchess.org/tests/view/5ae5f3090ebc59442aa387ea
[230418-master]:  https://github.com/official-stockfish/Stockfish/commit/aef7076c344881954b4f586bd4779594d0b29037
[230418-raw1]:    https://tests.stockfishchess.org/tests/stats/5ae5f3090ebc59442aa387ea
[290418-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...213166ba22
[290418-elo1]:    https://tests.stockfishchess.org/tests/view/5ae55fdd0ebc5902b3f347f7
[290418-master]:  https://github.com/official-stockfish/Stockfish/commit/213166ba225bcefbbe7dbecdacfd726dfb6c34f9
[290418-raw1]:    https://tests.stockfishchess.org/tests/stats/5ae55fdd0ebc5902b3f347f7
[030518-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...d4cb80b210
[030518-elo1]:    https://tests.stockfishchess.org/tests/view/5aebee200ebc5962311adb36
[030518-master]:  https://github.com/official-stockfish/Stockfish/commit/d4cb80b2106efb58db87495090a3898d902075d6
[030518-raw1]:    https://tests.stockfishchess.org/tests/stats/5aebee200ebc5962311adb36
[130518-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...aacee91a5a
[130518-elo1]:    https://tests.stockfishchess.org/tests/view/5afb21bd0ebc591fdf408d59
[130518-master]:  https://github.com/official-stockfish/Stockfish/commit/aacee91a5a295f1d9de2ea6dc0ca4a48e934e3b6
[130518-raw1]:    https://tests.stockfishchess.org/tests/stats/5afb21bd0ebc591fdf408d59
[240518-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...3d6995eae8
[240518-elo1]:    https://tests.stockfishchess.org/tests/view/5b06f59b0ebc5914abc12bb1
[240518-master]:  https://github.com/official-stockfish/Stockfish/commit/3d6995eae8039b2bf4141cbc02d87d5a6c2a1905
[240518-raw1]:    https://tests.stockfishchess.org/tests/stats/5b06f59b0ebc5914abc12bb1
[050618-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...e4f8a4fa7f
[050618-elo1]:    https://tests.stockfishchess.org/tests/view/5b1777950ebc596dfa6acbe6
[050618-master]:  https://github.com/official-stockfish/Stockfish/commit/e4f8a4fa7f5da8287579c0c74e292974c6acfd8d
[050618-raw1]:    https://tests.stockfishchess.org/tests/stats/5b1777950ebc596dfa6acbe6
[110618-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...fc3af7c4fb
[110618-elo1]:    https://tests.stockfishchess.org/tests/view/5b1e41190ebc5902ab9c778b
[110618-master]:  https://github.com/official-stockfish/Stockfish/commit/fc3af7c4fbeaa3c5b85424077829223f9d18184e
[110618-raw1]:    https://tests.stockfishchess.org/tests/stats/5b1e41190ebc5902ab9c778b
[230618-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...efd4ca27c4
[230618-elo1]:    https://tests.stockfishchess.org/tests/view/5b2ecd830ebc5902b2e57650
[230618-master]:  https://github.com/official-stockfish/Stockfish/commit/efd4ca27c4d7abad41e0469aa9b3b26b12068914
[230618-raw1]:    https://tests.stockfishchess.org/tests/stats/5b2ecd830ebc5902b2e57650
[190718-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...12e79be910
[190718-elo1]:    https://tests.stockfishchess.org/tests/view/5b50bec70ebc5902bdb7bf97
[190718-master]:  https://github.com/official-stockfish/Stockfish/commit/12e79be91039796299187ba1b2f1559552642ea4
[190718-raw1]:    https://tests.stockfishchess.org/tests/stats/5b50bec70ebc5902bdb7bf97
[270718-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...6184d2b2ac
[270718-elo1]:    https://tests.stockfishchess.org/tests/view/5b5b2de00ebc5902bdb8dcce
[270718-master]:  https://github.com/official-stockfish/Stockfish/commit/6184d2b2ac25691dc171560903a81e6d38a0593a
[270718-raw1]:    https://tests.stockfishchess.org/tests/stats/5b5b2de00ebc5902bdb8dcce
[280718-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...c08e05b494
[280718-elo1]:    https://tests.stockfishchess.org/tests/view/5b5c02e70ebc5902bdb8f4d0
[280718-master]:  https://github.com/official-stockfish/Stockfish/commit/c08e05b494d54c7fc28621204382d77d3595d436
[280718-raw1]:    https://tests.stockfishchess.org/tests/stats/5b5c02e70ebc5902bdb8f4d0
[310718-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...fae57273b2
[310718-elo1]:    https://tests.stockfishchess.org/tests/view/5b60e7a70ebc5902bdb946b0
[310718-master]:  https://github.com/official-stockfish/Stockfish/commit/fae57273b20468f534cce5843152a21214b5da05
[310718-raw1]:    https://tests.stockfishchess.org/tests/stats/5b60e7a70ebc5902bdb946b0
[080818-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...bd4d2b0576
[080818-elo1]:    https://tests.stockfishchess.org/tests/view/5b6b16d90ebc5902bdb9df94
[080818-master]:  https://github.com/official-stockfish/Stockfish/commit/bd4d2b0576ec320367769d5720c7a5b4d094ceef
[080818-raw1]:    https://tests.stockfishchess.org/tests/stats/5b6b16d90ebc5902bdb9df94
[120818-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...b5581b7779
[120818-elo1]:    https://tests.stockfishchess.org/tests/view/5b6fedde0ebc5902bdba1d10
[120818-master]:  https://github.com/official-stockfish/Stockfish/commit/b5581b7779b6e286fa2277625572996477d74b10
[120818-raw1]:    https://tests.stockfishchess.org/tests/stats/5b6fedde0ebc5902bdba1d10
[140818-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...881cab2525
[140818-elo1]:    https://tests.stockfishchess.org/tests/view/5b72955f0ebc5902bdba4b07
[140818-master]:  https://github.com/official-stockfish/Stockfish/commit/881cab252530c8711e942f7936a3eb41b2956a6b
[140818-raw1]:    https://tests.stockfishchess.org/tests/stats/5b72955f0ebc5902bdba4b07
[170818-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...f3b8a69919
[170818-elo1]:    https://tests.stockfishchess.org/tests/view/5b775ad60ebc5902bdbaa8cb
[170818-master]:  https://github.com/official-stockfish/Stockfish/commit/f3b8a699194515e0b74f5349cf84175a97f824e8
[170818-raw1]:    https://tests.stockfishchess.org/tests/stats/5b775ad60ebc5902bdbaa8cb
[280818A-dif]:    https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...6307fd08e6
[280818A-elo1]:   https://tests.stockfishchess.org/tests/view/5b85d4520ebc5902bdbbb871
[280818A-master]: https://github.com/official-stockfish/Stockfish/commit/6307fd08e6e8c315802301fd35b22ca2a67071a9
[280818A-raw1]:   https://tests.stockfishchess.org/tests/stats/5b85d4520ebc5902bdbbb871
[280818B-dif]:    https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...e846a9306d
[280818B-elo1]:   https://tests.stockfishchess.org/tests/view/5b8915fb0ebc592cf2747bf8
[280818B-master]: https://github.com/official-stockfish/Stockfish/commit/e846a9306d6108fb24cb216689867777ac2b0c4f
[280818B-raw1]:   https://tests.stockfishchess.org/tests/stats/5b8915fb0ebc592cf2747bf8
[010918-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...2bfaf45455
[010918-elo1]:    https://tests.stockfishchess.org/tests/view/5b8dccf60ebc592cf274d4b0
[010918-master]:  https://github.com/official-stockfish/Stockfish/commit/2bfaf454551ae5a9d99d271d0d87d2a6c829c7e4
[010918-raw1]:    https://tests.stockfishchess.org/tests/stats/5b8dccf60ebc592cf274d4b0
[100918-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...0fa957cf66
[100918-elo1]:    https://tests.stockfishchess.org/tests/view/5b976bbc0ebc592cf275a312
[100918-master]:  https://github.com/official-stockfish/Stockfish/commit/0fa957cf66069c4499d9fe793cf07a11c4ccb87c
[100918-raw1]:    https://tests.stockfishchess.org/tests/stats/5b976bbc0ebc592cf275a312
[270918-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...8141bdd179
[270918-elo1]:    https://tests.stockfishchess.org/tests/view/5bad44590ebc592439f6654d
[270918-master]:  https://github.com/official-stockfish/Stockfish/commit/8141bdd179da8f36c04f99d51812b19bbd1a8efd
[270918-raw1]:    https://tests.stockfishchess.org/tests/stats/5bad44590ebc592439f6654d
[141018-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...738a6dfd4c
[141018-elo1]:    https://tests.stockfishchess.org/tests/view/5bc38fda0ebc592439f7f4dd
[141018-master]:  https://github.com/official-stockfish/Stockfish/commit/738a6dfd4c71c3ce11d614076117793b4cdf119e
[141018-raw1]:    https://tests.stockfishchess.org/tests/stats/5bc38fda0ebc592439f7f4dd
[251018-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...081af90805
[251018-elo1]:    https://tests.stockfishchess.org/tests/view/5bd36e170ebc595e0ae1e776
[251018-master]:  https://github.com/official-stockfish/Stockfish/commit/081af9080542a0d076a5482da37103a96ee15f64
[251018-raw1]:    https://tests.stockfishchess.org/tests/stats/5bd36e170ebc595e0ae1e776
[011118-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...3f1eb85a1c
[011118-elo1]:    https://tests.stockfishchess.org/tests/view/5bdb1a140ebc595e0ae2620a
[011118-master]:  https://github.com/official-stockfish/Stockfish/commit/3f1eb85a1ceb1b408f8f51cb82064b69e095399d
[011118-raw1]:    https://tests.stockfishchess.org/tests/stats/5bdb1a140ebc595e0ae2620a
[081118-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...05aa34e00e
[081118-elo1]:    https://tests.stockfishchess.org/tests/view/5be464190ebc595e0ae303be
[081118-master]:  https://github.com/official-stockfish/Stockfish/commit/05aa34e00ed78adfa943242026a00dc497acd563
[081118-raw1]:    https://tests.stockfishchess.org/tests/stats/5be464190ebc595e0ae303be
[191118-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...cf5d683408
[191118-elo1]:    https://tests.stockfishchess.org/tests/view/5bf29f4a0ebc5902bbbddfeb
[191118-master]:  https://github.com/official-stockfish/Stockfish/commit/cf5d683408a2ef8a1c80be9bf7d6790a38b16277
[191118-raw1]:    https://tests.stockfishchess.org/tests/stats/5bf29f4a0ebc5902bbbddfeb
[271118-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...7b6fa353a3
[271118-elo1]:    https://tests.stockfishchess.org/tests/view/5bfcfa2b0ebc5902bced8acf
[271118-master]:  https://github.com/official-stockfish/Stockfish/commit/7b6fa353a3858b092e1a43ef69b3035cb5d3b5c0
[271118-raw1]:    https://tests.stockfishchess.org/tests/stats/5bfcfa2b0ebc5902bced8acf
[Stockfish 10]:   https://github.com/official-stockfish/Stockfish/commit/b4c239b625285307c5871f1104dc3fb80aa6d5d2
[SF10DP]:         https://user-images.githubusercontent.com/64992190/156416236-9dc49028-5cf4-4cb3-9314-a3c3a3d7b12b.png "Development Progress"
[SF10RN]:         https://stockfishchess.org/blog/2018/stockfish-10/ "Release Notes"
[291118-dif]:     https://github.com/official-stockfish/Stockfish/compare/378c8bdbb8...b4c239b625
[061218-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...5c2fbcd09b
[061218-elo1]:    https://tests.stockfishchess.org/tests/view/5c092f8b0ebc5902bcee8877
[061218-master]:  https://github.com/official-stockfish/Stockfish/commit/5c2fbcd09b43bd6867780a3ace303ffb1e09d763
[061218-raw1]:    https://tests.stockfishchess.org/tests/stats/5c092f8b0ebc5902bcee8877
[131218-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...31ac538f96
[131218-elo1]:    https://tests.stockfishchess.org/tests/view/5c126a140ebc5902ba11afb0
[131218-elo8]:    https://tests.stockfishchess.org/tests/view/5d01302d0ebc5925cf09d044
[131218-master]:  https://github.com/official-stockfish/Stockfish/commit/31ac538f96a54b294e79213d33aacf5d8a182c87
[131218-raw1]:    https://tests.stockfishchess.org/tests/stats/5c126a140ebc5902ba11afb0
[131218-raw8]:    https://tests.stockfishchess.org/tests/stats/5d01302d0ebc5925cf09d044
[161218-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...7240a90bf9
[161218-elo1]:    https://tests.stockfishchess.org/tests/view/5c17830c0ebc5902ba1234c4
[161218-master]:  https://github.com/official-stockfish/Stockfish/commit/7240a90bf9be3f39f3ca4f34921dd644c5cebb3a
[161218-raw1]:    https://tests.stockfishchess.org/tests/stats/5c17830c0ebc5902ba1234c4
[040119-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...bb843a00c1
[040119-elo1]:    https://tests.stockfishchess.org/tests/view/5c2f7d4f0ebc596a450be7dc
[040119-master]:  https://github.com/official-stockfish/Stockfish/commit/bb843a00c1ef381162dc9c2491b5436b6cf5563f
[040119-raw1]:    https://tests.stockfishchess.org/tests/stats/5c2f7d4f0ebc596a450be7dc
[100119-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...5446e6f408
[100119-elo1]:    https://tests.stockfishchess.org/tests/view/5c376bd30ebc596a450c8216
[100119-elo8]:    https://tests.stockfishchess.org/tests/view/5ced50b50ebc5925cf07eabf
[100119-master]:  https://github.com/official-stockfish/Stockfish/commit/5446e6f408f2ed7fa281dbe0097c46674d193260
[100119-raw1]:    https://tests.stockfishchess.org/tests/stats/5c376bd30ebc596a450c8216
[100119-raw8]:    https://tests.stockfishchess.org/tests/stats/5ced50b50ebc5925cf07eabf
[220119-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...2d0af36753
[220119-elo1]:    https://tests.stockfishchess.org/tests/view/5c46dbef0ebc5902bb5d6b6f
[220119-master]:  https://github.com/official-stockfish/Stockfish/commit/2d0af36753a2f1acdf43b4e1d30d56ad8effc429
[220119-raw1]:    https://tests.stockfishchess.org/tests/stats/5c46dbef0ebc5902bb5d6b6f
[030219-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...6514500236
[030219-elo1]:    https://tests.stockfishchess.org/tests/view/5c5777a00ebc592015e0db3b
[030219-elo8]:    https://tests.stockfishchess.org/tests/view/5cf9eadf0ebc5925cf09264e
[030219-master]:  https://github.com/official-stockfish/Stockfish/commit/651450023619ddea590f301f040286151004df66
[030219-raw1]:    https://tests.stockfishchess.org/tests/stats/5c5777a00ebc592015e0db3b
[030219-raw8]:    https://tests.stockfishchess.org/tests/stats/5cf9eadf0ebc5925cf09264e
[120319-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...bad18bccb6
[120319-elo1]:    https://tests.stockfishchess.org/tests/view/5c8bbd6b0ebc5925cffed484
[120319-master]:  https://github.com/official-stockfish/Stockfish/commit/bad18bccb60c874410edd3f61624696d3abc3cbc
[120319-raw1]:    https://tests.stockfishchess.org/tests/stats/5c8bbd6b0ebc5925cffed484
[310319-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...82ad9ce9cf
[310319-elo1]:    https://tests.stockfishchess.org/tests/view/5ca294f90ebc5925cf000e4d
[310319-elo8]:    https://tests.stockfishchess.org/tests/view/5cba4ebd0ebc5925cf020fae
[310319-master]:  https://github.com/official-stockfish/Stockfish/commit/82ad9ce9cfb0eff33f1d781f329f7c5dc0b277eb
[310319-raw1]:    https://tests.stockfishchess.org/tests/stats/5ca294f90ebc5925cf000e4d
[310319-raw8]:    https://tests.stockfishchess.org/tests/stats/5cba4ebd0ebc5925cf020fae
[240419-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...6373fd56e9
[240419-elo1]:    https://tests.stockfishchess.org/tests/view/5cc0b7520ebc5925cf02af43
[240419-master]:  https://github.com/official-stockfish/Stockfish/commit/6373fd56e90bc6114230a70cacad804248d955e2
[240419-raw1]:    https://tests.stockfishchess.org/tests/stats/5cc0b7520ebc5925cf02af43
[050519-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...b6d11028bb
[050519-elo1]:    https://tests.stockfishchess.org/tests/view/5ccf55560ebc5925cf04273a
[050519-master]:  https://github.com/official-stockfish/Stockfish/commit/b6d11028bbb5e428cdbd709ba46d8b14bab17c88
[050519-raw1]:    https://tests.stockfishchess.org/tests/stats/5ccf55560ebc5925cf04273a
[150519-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...3a572ffb48
[150519-elo1]:    https://tests.stockfishchess.org/tests/view/5cdc33ac0ebc5925cf05b8bc
[150519-elo8]:    https://tests.stockfishchess.org/tests/view/5cdc35160ebc5925cf05b90e
[150519-master]:  https://github.com/official-stockfish/Stockfish/commit/3a572ffb4840bfea3c587c9c81a0008515f02a32
[150519-raw1]:    https://tests.stockfishchess.org/tests/stats/5cdc33ac0ebc5925cf05b8bc
[150519-raw8]:    https://tests.stockfishchess.org/tests/stats/5cdc35160ebc5925cf05b90e
[090619-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...2ead74d1e2
[090619-elo1]:    https://tests.stockfishchess.org/tests/view/5cfd00570ebc5925cf096317
[090619-master]:  https://github.com/official-stockfish/Stockfish/commit/2ead74d1e2b0c5edbb0da5887e56bbddb5b2a905
[090619-raw1]:    https://tests.stockfishchess.org/tests/stats/5cfd00570ebc5925cf096317
[200619-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...37ffacf209
[200619-elo1]:    https://tests.stockfishchess.org/tests/view/5d0b9f950ebc5925cf0a9c6b
[200619-elo8]:    https://tests.stockfishchess.org/tests/view/5d0ba0010ebc5925cf0a9c84
[200619-master]:  https://github.com/official-stockfish/Stockfish/commit/37ffacf2094594314346bf9c3d7d8a61911b34d5
[200619-raw1]:    https://tests.stockfishchess.org/tests/stats/5d0b9f950ebc5925cf0a9c6b
[200619-raw8]:    https://tests.stockfishchess.org/tests/stats/5d0ba0010ebc5925cf0a9c84
[270619-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...d889bb4718
[270619-elo1]:    https://tests.stockfishchess.org/tests/view/5d1479580ebc5925cf0b421f
[270619-master]:  https://github.com/official-stockfish/Stockfish/commit/d889bb47185e33012b45cab63359952247bc86e2
[270619-raw1]:    https://tests.stockfishchess.org/tests/stats/5d1479580ebc5925cf0b421f
[110719-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...4ae5a7b45a
[110719-elo1]:    https://tests.stockfishchess.org/tests/view/5d274ae90ebc5925cf0d3cd4
[110719-master]:  https://github.com/official-stockfish/Stockfish/commit/4ae5a7b45a430aea5f4b21f9455b4db74ed1c44a
[110719-raw1]:    https://tests.stockfishchess.org/tests/stats/5d274ae90ebc5925cf0d3cd4
[250719-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...acdda38b93
[250719-elo1]:    https://tests.stockfishchess.org/tests/view/5d395a840ebc5925cf0f075e
[250719-elo8]:    https://tests.stockfishchess.org/tests/view/5d3964d20ebc5925cf0f078b
[250719-master]:  https://github.com/official-stockfish/Stockfish/commit/acdda38b93361f10e331a6d951d6870577efdace
[250719-raw1]:    https://tests.stockfishchess.org/tests/stats/5d395a840ebc5925cf0f075e
[250719-raw8]:    https://tests.stockfishchess.org/tests/stats/5d3964d20ebc5925cf0f078b
[140819-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...66a3c2968b
[140819-elo1]:    https://tests.stockfishchess.org/tests/view/5d545fd20ebc5925cf10a1ee
[140819-master]:  https://github.com/official-stockfish/Stockfish/commit/66a3c2968b8552efce8c7e670d7ceabb28f9c1eb
[140819-raw1]:    https://tests.stockfishchess.org/tests/stats/5d545fd20ebc5925cf10a1ee
[260819-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...8fec883471
[260819-elo1]:    https://tests.stockfishchess.org/tests/view/5d6394260ebc5939d09f436c
[260819-elo8]:    https://tests.stockfishchess.org/tests/view/5d63961a0ebc5939d09f4382
[260819-master]:  https://github.com/official-stockfish/Stockfish/commit/8fec8834715a440ac18e24e130888c2c60bab352
[260819-raw1]:    https://tests.stockfishchess.org/tests/stats/5d6394260ebc5939d09f436c
[260819-raw8]:    https://tests.stockfishchess.org/tests/stats/5d63961a0ebc5939d09f4382
[120919-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...8aecf26981
[120919-elo1]:    https://tests.stockfishchess.org/tests/view/5d7a0b7c0ebc5902d385654a
[120919-master]:  https://github.com/official-stockfish/Stockfish/commit/8aecf2698184babce57ccfd2ba5948342e29c325
[120919-raw1]:    https://tests.stockfishchess.org/tests/stats/5d7a0b7c0ebc5902d385654a
[160919-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...a858defd33
[160919-elo1]:    https://tests.stockfishchess.org/tests/view/5d809d540ebc5971531d0b66
[160919-elo8]:    https://tests.stockfishchess.org/tests/view/5d80d2240ebc5971531d1e46
[160919-master]:  https://github.com/official-stockfish/Stockfish/commit/a858defd332bddd828c9280a9e326a0b750b3dda
[160919-raw1]:    https://tests.stockfishchess.org/tests/stats/5d809d540ebc5971531d0b66
[160919-raw8]:    https://tests.stockfishchess.org/tests/stats/5d80d2240ebc5971531d1e46
[240919-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...667d24f227
[240919-elo1]:    https://tests.stockfishchess.org/tests/view/5d8d2c030ebc590f3beac64d
[240919-master]:  https://github.com/official-stockfish/Stockfish/commit/667d24f22743959ceddda6af53718619ea5c551d
[240919-raw1]:    https://tests.stockfishchess.org/tests/stats/5d8d2c030ebc590f3beac64d
[051019-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...2e96c513ad
[051019-elo1]:    https://tests.stockfishchess.org/tests/view/5d99322f0ebc5902b6cef9fa
[051019-elo8]:    https://tests.stockfishchess.org/tests/view/5d9932830ebc5902b6cef9fc
[051019-master]:  https://github.com/official-stockfish/Stockfish/commit/2e96c513ad6113abb6bc4fdd4962cc1f6eed3d4a
[051019-raw1]:    https://tests.stockfishchess.org/tests/stats/5d99322f0ebc5902b6cef9fa
[051019-raw8]:    https://tests.stockfishchess.org/tests/stats/5d9932830ebc5902b6cef9fc
[181019-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...472de897cb
[181019-elo1]:    https://tests.stockfishchess.org/tests/view/5da9d8470ebc597ba8edbb52
[181019-master]:  https://github.com/official-stockfish/Stockfish/commit/472de897cb7efb66cb3518f3f4924716bd8abaee
[181019-raw1]:    https://tests.stockfishchess.org/tests/stats/5da9d8470ebc597ba8edbb52
[041119-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...3804effb34
[041119-elo1]:    https://tests.stockfishchess.org/tests/view/5dc0b9660ebc5904493b0107
[041119-elo8]:    https://tests.stockfishchess.org/tests/view/5dc0ba190ebc5904493b0110
[041119-master]:  https://github.com/official-stockfish/Stockfish/commit/3804effb341b3008326a1613923177eb83d02826
[041119-raw1]:    https://tests.stockfishchess.org/tests/stats/5dc0b9660ebc5904493b0107
[041119-raw8]:    https://tests.stockfishchess.org/tests/stats/5dc0ba190ebc5904493b0110
[141119-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...a00a336946
[141119-elo1]:    https://tests.stockfishchess.org/tests/view/5dcdb0170ebc590256324986
[141119-master]:  https://github.com/official-stockfish/Stockfish/commit/a00a336946fa9e6dcfa39f8b656413d2de032a89
[141119-raw1]:    https://tests.stockfishchess.org/tests/stats/5dcdb0170ebc590256324986
[211119-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...3f4191392c
[211119-elo1]:    https://tests.stockfishchess.org/tests/view/5dd888329b6a7a2aa0a9005a
[211119-elo8]:    https://tests.stockfishchess.org/tests/view/5dd888a09b6a7a2aa0a9005c
[211119-master]:  https://github.com/official-stockfish/Stockfish/commit/3f4191392c18f08011294aab880c31b15fc6f61c
[211119-raw1]:    https://tests.stockfishchess.org/tests/stats/5dd888329b6a7a2aa0a9005a
[211119-raw8]:    https://tests.stockfishchess.org/tests/stats/5dd888a09b6a7a2aa0a9005c
[021219-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...97a0e4e817
[021219-elo1]:    https://tests.stockfishchess.org/tests/view/5de59f7db407ee7bfda68a58
[021219-master]:  https://github.com/official-stockfish/Stockfish/commit/97a0e4e8170df33b927c48d734e0132e9ef8a22f
[021219-raw1]:    https://tests.stockfishchess.org/tests/stats/5de59f7db407ee7bfda68a58
[101219-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...b6482472a0
[101219-elo1]:    https://tests.stockfishchess.org/tests/view/5def70363cff9a249bb9e4c5
[101219-elo8]:    https://tests.stockfishchess.org/tests/view/5def70ae3cff9a249bb9e4c8
[101219-master]:  https://github.com/official-stockfish/Stockfish/commit/b6482472a03833287dc21bdaa783f156978ac63e
[101219-raw1]:    https://tests.stockfishchess.org/tests/stats/5def70363cff9a249bb9e4c5
[101219-raw8]:    https://tests.stockfishchess.org/tests/stats/5def70ae3cff9a249bb9e4c8
[070120-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...44f79bdf5a
[070120-elo1]:    https://tests.stockfishchess.org/tests/view/5e1472da61fe5f83a67dd84f
[070120-elo8]:    https://tests.stockfishchess.org/tests/view/5e14734d61fe5f83a67dd851
[070120-master]:  https://github.com/official-stockfish/Stockfish/commit/44f79bdf5a092c3acec0a8bf8f2c1440e5a9da90
[070120-raw1]:    https://tests.stockfishchess.org/tests/stats/5e1472da61fe5f83a67dd84f
[070120-raw8]:    https://tests.stockfishchess.org/tests/stats/5e14734d61fe5f83a67dd851
[170120-dif]:     https://github.com/official-stockfish/Stockfish/compare/b4c239b625...c3483fa9a7
[170120-elo1]:    https://tests.stockfishchess.org/tests/view/5e2258dd346e35ac603b7d8c
[170120-elo8]:    https://tests.stockfishchess.org/tests/view/5e22593d346e35ac603b7d8f
[170120-master]:  https://github.com/official-stockfish/Stockfish/commit/c3483fa9a7d7c0ffa9fcc32b467ca844cfb63790
[170120-raw1]:    https://tests.stockfishchess.org/tests/stats/5e2258dd346e35ac603b7d8c
[170120-raw8]:    https://tests.stockfishchess.org/tests/stats/5e22593d346e35ac603b7d8f
[Stockfish 11]:   https://github.com/official-stockfish/Stockfish/commit/c3483fa9a7d7c0ffa9fcc32b467ca844cfb63790
[SF11DP]:         https://user-images.githubusercontent.com/64992190/156415721-adef6287-f523-4cc4-b7e8-cc920bdd7bdc.png "Development Progress"
[SF11RN]:         https://stockfishchess.org/blog/2020/stockfish-11/ "Release Notes"
[280120-dif]:     https://github.com/official-stockfish/Stockfish/compare/c3483fa9a7...71e0b5385e
[280120-elo1]:    https://tests.stockfishchess.org/tests/view/5e307251ab2d69d58394fdb9
[280120-master]:  https://github.com/official-stockfish/Stockfish/commit/71e0b5385e2717679a57c6b77d8c7ac5fff3b89f
[280120-raw1]:    https://tests.stockfishchess.org/tests/stats/5e307251ab2d69d58394fdb9
[310120-dif]:     https://github.com/official-stockfish/Stockfish/compare/c3483fa9a7...f10498be40
[310120-elo1]:    https://tests.stockfishchess.org/tests/view/5e334851708b13464ceea33c
[310120-master]:  https://github.com/official-stockfish/Stockfish/commit/6ccb1cac5aaaf7337da8b1738448793be63fdfdb
[310120-raw1]:    https://tests.stockfishchess.org/tests/stats/5e334851708b13464ceea33c
[270220-dif]:     https://github.com/official-stockfish/Stockfish/compare/c3483fa9a7...09f53dbfa5
[270220-elo1]:    https://tests.stockfishchess.org/tests/view/5e5801a584a82b4acd414a28
[270220-elo8]:    https://tests.stockfishchess.org/tests/view/5e58020384a82b4acd414a2a
[270220-master]:  https://github.com/official-stockfish/Stockfish/commit/09f53dbfa5b55e761ca8070960345ab140baad04
[270220-raw1]:    https://tests.stockfishchess.org/tests/stats/5e5801a584a82b4acd414a28
[270220-raw8]:    https://tests.stockfishchess.org/tests/stats/5e58020384a82b4acd414a2a
[200320-dif]:     https://github.com/official-stockfish/Stockfish/compare/c3483fa9a7...6ecab03dee
[200320-elo1]:    https://tests.stockfishchess.org/tests/view/5e790d12e42a5c3b3ca2e9b7
[200320-master]:  https://github.com/official-stockfish/Stockfish/commit/6ecab03dee15fe30bc0237919180a2e51e0ce4b1
[200320-raw1]:    https://tests.stockfishchess.org/tests/stats/5e790d12e42a5c3b3ca2e9b7
[070420-dif]:     https://github.com/official-stockfish/Stockfish/compare/c3483fa9a7...195a4fec6d
[070420-elo1]:    https://tests.stockfishchess.org/tests/view/5e8ca31b0ffd2be7f15e54b3
[070420-elo8]:    https://tests.stockfishchess.org/tests/view/5e8ca37e0ffd2be7f15e54b5
[070420-master]:  https://github.com/official-stockfish/Stockfish/commit/195a4fec6d6bd1f9e43f5b3e83a3dcf57dc73744
[070420-raw1]:    https://tests.stockfishchess.org/tests/stats/5e8ca31b0ffd2be7f15e54b3
[070420-raw8]:    https://tests.stockfishchess.org/tests/stats/5e8ca37e0ffd2be7f15e54b5
[160420-dif]:     https://github.com/official-stockfish/Stockfish/compare/c3483fa9a7...345b2d153a
[160420-elo1]:    https://tests.stockfishchess.org/tests/view/5e98b9e130be947a14e9db1b
[160420-master]:  https://github.com/official-stockfish/Stockfish/commit/345b2d153a8092cff93ad660c9d107cd66fda43b
[160420-raw1]:    https://tests.stockfishchess.org/tests/stats/5e98b9e130be947a14e9db1b
[020520-dif]:     https://github.com/official-stockfish/Stockfish/compare/c3483fa9a7...c527c3ad44
[020520-elo1]:    https://tests.stockfishchess.org/tests/view/5eadc1526ffeed51f6e3277e
[020520-elo8]:    https://tests.stockfishchess.org/tests/view/5eadc2156ffeed51f6e32781
[020520-master]:  https://github.com/official-stockfish/Stockfish/commit/c527c3ad44f7465c79cef93f1e8cfebd998dc627
[020520-raw1]:    https://tests.stockfishchess.org/tests/stats/5eadc1526ffeed51f6e3277e
[020520-raw8]:    https://tests.stockfishchess.org/tests/stats/5eadc2156ffeed51f6e32781
[210520-dif]:     https://github.com/official-stockfish/Stockfish/compare/c3483fa9a7...09c6917d05
[210520-elo1]:    https://tests.stockfishchess.org/tests/view/5ec6c48ec23f5b0710632b04
[210520-master]:  https://github.com/official-stockfish/Stockfish/commit/09c6917d053582267a2960e8c375883e0d9461da
[210520-raw1]:    https://tests.stockfishchess.org/tests/stats/5ec6c48ec23f5b0710632b04
[060620-dif]:     https://github.com/official-stockfish/Stockfish/compare/c3483fa9a7...15e190e942
[060620-elo1]:    https://tests.stockfishchess.org/tests/view/5edf5ffdf29b40b0fc95ad62
[060620-elo8]:    https://tests.stockfishchess.org/tests/view/5edf6220f29b40b0fc95ad6e
[060620-master]:  https://github.com/official-stockfish/Stockfish/commit/15e190e9428b21fbfe29ce020c456077dc5fdd04
[060620-raw1]:    https://tests.stockfishchess.org/tests/stats/5edf5ffdf29b40b0fc95ad62
[060620-raw8]:    https://tests.stockfishchess.org/tests/stats/5edf6220f29b40b0fc95ad6e
[130620-dif]:     https://github.com/official-stockfish/Stockfish/compare/c3483fa9a7...42b7dbcb5e
[130620-elo1]:    https://tests.stockfishchess.org/tests/view/5ee5b14dca6c451633a9a06f
[130620-elo8]:    https://tests.stockfishchess.org/tests/view/5ee5b1c3ca6c451633a9a075
[130620-master]:  https://github.com/official-stockfish/Stockfish/commit/42b7dbcb5e20ae9015122601522be8b455787a4a
[130620-raw1]:    https://tests.stockfishchess.org/tests/stats/5ee5b14dca6c451633a9a06f
[130620-raw8]:    https://tests.stockfishchess.org/tests/stats/5ee5b1c3ca6c451633a9a075
[290620-dif]:     https://github.com/official-stockfish/Stockfish/compare/c3483fa9a7...69d3be42a1
[290620-elo1]:    https://tests.stockfishchess.org/tests/view/5efa336b020eec13834a975d
[290620-master]:  https://github.com/official-stockfish/Stockfish/commit/69d3be42a112645a9e599df615f730d61a5dca8c
[290620-raw1]:    https://tests.stockfishchess.org/tests/stats/5efa336b020eec13834a975d
[170720-dif]:     https://github.com/official-stockfish/Stockfish/compare/c3483fa9a7...d89730d5c8
[170720-elo1]:    https://tests.stockfishchess.org/tests/view/5f14adebda64229ef7dc1788
[170720-elo8]:    https://tests.stockfishchess.org/tests/view/5f14ae36da64229ef7dc178a
[170720-master]:  https://github.com/official-stockfish/Stockfish/commit/d89730d5c8dcf10eb9e1d91a81f903d9fc3c949a
[170720-raw1]:    https://tests.stockfishchess.org/tests/stats/5f14adebda64229ef7dc1788
[170720-raw8]:    https://tests.stockfishchess.org/tests/stats/5f14ae36da64229ef7dc178a
[310720-dif]:     https://github.com/official-stockfish/Stockfish/compare/c3483fa9a7...9587eeeb5e
[310720-elo1]:    https://tests.stockfishchess.org/tests/view/5f29002aa5abc164f05e4c4f
[310720-elo8]:    https://tests.stockfishchess.org/tests/view/5f291999a5abc164f05e4c67
[310720-master]:  https://github.com/official-stockfish/Stockfish/commit/9587eeeb5ed29f834d4f956b92e0e732877c47a7
[310720-raw1]:    https://tests.stockfishchess.org/tests/stats/5f29002aa5abc164f05e4c4f
[310720-raw8]:    https://tests.stockfishchess.org/tests/stats/5f291999a5abc164f05e4c67
[060820-dif]:     https://github.com/official-stockfish/Stockfish/compare/c3483fa9a7...84f3e86790
[060820-elo1]:    https://tests.stockfishchess.org/tests/view/5f2c5a25b3ebe5cbfee85b8e
[060820-elo8]:    https://tests.stockfishchess.org/tests/view/5f2c5a52b3ebe5cbfee85b91
[060820-master]:  https://github.com/official-stockfish/Stockfish/commit/84f3e867903f62480c33243dd0ecbffd342796fc
[060820-raw1]:    https://tests.stockfishchess.org/tests/stats/5f2c5a25b3ebe5cbfee85b8e
[060820-raw8]:    https://tests.stockfishchess.org/tests/stats/5f2c5a52b3ebe5cbfee85b91
[SFNNUERN]:       https://stockfishchess.org/blog/2020/introducing-nnue-evaluation/ "Release Notes"
[070820-dif]:     https://github.com/official-stockfish/Stockfish/compare/c3483fa9a7...84f3e86790
[080820-dif]:     https://github.com/official-stockfish/Stockfish/compare/c3483fa9a7...add890a10b
[080820-elo1]:    https://tests.stockfishchess.org/tests/view/5f2f0ff49081672066536b29
[080820-master]:  https://github.com/official-stockfish/Stockfish/commit/add890a10b8fe03e091520cd0af7383615c6c386
[080820-raw1]:    https://tests.stockfishchess.org/tests/stats/5f2f0ff49081672066536b29
[110820-dif]:     https://github.com/official-stockfish/Stockfish/compare/c3483fa9a7...ea6220f381
[110820-elo1]:    https://tests.stockfishchess.org/tests/view/5f32844966a893ef3a025dde
[110820-elo8]:    https://tests.stockfishchess.org/tests/view/5f32846e66a893ef3a025de0
[110820-master]:  https://github.com/official-stockfish/Stockfish/commit/ea6220f3813e5b76b444a02905eaf2c556bdb368
[110820-raw1]:    https://tests.stockfishchess.org/tests/stats/5f32844966a893ef3a025dde
[110820-raw8]:    https://tests.stockfishchess.org/tests/stats/5f32846e66a893ef3a025de0
[180820-dif]:     https://github.com/official-stockfish/Stockfish/compare/c3483fa9a7...fbae5614eb
[180820-elo1]:    https://tests.stockfishchess.org/tests/view/5f3b7ff8b38d442594aabebc
[180820-elo8]:    https://tests.stockfishchess.org/tests/view/5f3b8008b38d442594aabebe
[180820-master]:  https://github.com/official-stockfish/Stockfish/commit/fbae5614eb1e82bccd37fbcfb0d2ca388b7a9a7d
[180820-raw1]:    https://tests.stockfishchess.org/tests/stats/5f3b7ff8b38d442594aabebc
[180820-raw8]:    https://tests.stockfishchess.org/tests/stats/5f3b8008b38d442594aabebe
[300820-dif]:     https://github.com/official-stockfish/Stockfish/compare/c3483fa9a7...e0bafa1911
[300820-elo1]:    https://tests.stockfishchess.org/tests/view/5f4b9b24ba100690c5cc5c7f
[300820-master]:  https://github.com/official-stockfish/Stockfish/commit/e0bafa1911ede61b9268e0b461a5d8856d6cd6be
[300820-raw1]:    https://tests.stockfishchess.org/tests/stats/5f4b9b24ba100690c5cc5c7f
[020920-dif]:     https://github.com/official-stockfish/Stockfish/compare/c3483fa9a7...c306d83869
[020920-elo1]:    https://tests.stockfishchess.org/tests/view/5f4faef2ba100690c5cc5e79
[020920-elo8]:    https://tests.stockfishchess.org/tests/view/5f4faf0eba100690c5cc5e7b
[020920-master]:  https://github.com/official-stockfish/Stockfish/commit/c306d838697011da0a960758dde3f7ede6849060
[020920-raw1]:    https://tests.stockfishchess.org/tests/stats/5f4faef2ba100690c5cc5e79
[020920-raw8]:    https://tests.stockfishchess.org/tests/stats/5f4faf0eba100690c5cc5e7b
[Stockfish 12]:   https://github.com/official-stockfish/Stockfish/commit/c306d838697011da0a960758dde3f7ede6849060
[SF12DP]:         https://user-images.githubusercontent.com/64992190/156415498-30505e38-cfaa-4656-af7d-c5a007b168dd.png "Development Progress"
[SF12RN]:         https://stockfishchess.org/blog/2020/stockfish-12/ "Release Notes"
[080920-dif]:     https://github.com/official-stockfish/Stockfish/compare/c306d83869...0405f35403
[080920-elo1]:    https://tests.stockfishchess.org/tests/view/5f57f1762f5ee9c2a401eb7c
[080920-master]:  https://github.com/official-stockfish/Stockfish/commit/0405f3540366cc16245d51531881c55d3726c8b5
[080920-raw1]:    https://tests.stockfishchess.org/tests/stats/5f57f1762f5ee9c2a401eb7c
[210920-dif]:     https://github.com/official-stockfish/Stockfish/compare/c306d83869...485d517c68
[210920-elo1]:    https://tests.stockfishchess.org/tests/view/5f684d23ded68c240be72173
[210920-elo8]:    https://tests.stockfishchess.org/tests/view/5f684d42ded68c240be7217c
[210920-master]:  https://github.com/official-stockfish/Stockfish/commit/485d517c687a2d3cb0b88cc8c198483759eaf2c7
[210920-raw1]:    https://tests.stockfishchess.org/tests/stats/5f684d23ded68c240be72173
[210920-raw8]:    https://tests.stockfishchess.org/tests/stats/5f684d42ded68c240be7217c
[280920-dif]:     https://github.com/official-stockfish/Stockfish/compare/c306d83869...5af09cfda5
[280920-elo1]:    https://tests.stockfishchess.org/tests/view/5f724c7fc96941256e85618f
[280920-master]:  https://github.com/official-stockfish/Stockfish/commit/5af09cfda5b71f9470ef233298e0f4233651337d
[280920-raw1]:    https://tests.stockfishchess.org/tests/stats/5f724c7fc96941256e85618f
[181020-dif]:     https://github.com/official-stockfish/Stockfish/compare/c306d83869...560c776397
[181020-elo1]:    https://tests.stockfishchess.org/tests/view/5f8c3442e669321c019e509f
[181020-elo8]:    https://tests.stockfishchess.org/tests/view/5f8c346ae669321c019e50a1
[181020-master]:  https://github.com/official-stockfish/Stockfish/commit/560c776397483feaaa0deb5b666f46ff3f5b655f
[181020-raw1]:    https://tests.stockfishchess.org/tests/stats/5f8c3442e669321c019e509f
[181020-raw8]:    https://tests.stockfishchess.org/tests/stats/5f8c346ae669321c019e50a1
[011120-dif]:     https://github.com/official-stockfish/Stockfish/compare/c306d83869...dfc7f88650
[011120-elo1]:    https://tests.stockfishchess.org/tests/view/5f9e7c786a2c112b60691e39
[011120-master]:  https://github.com/official-stockfish/Stockfish/commit/dfc7f88650bf8bda4a381d36e209209cf63a9bcc
[011120-raw1]:    https://tests.stockfishchess.org/tests/stats/5f9e7c786a2c112b60691e39
[151120-dif]:     https://github.com/official-stockfish/Stockfish/compare/c306d83869...f9595828eb
[151120-elo1]:    https://tests.stockfishchess.org/tests/view/5fb11f8467cbf42301d6ab62
[151120-elo8]:    https://tests.stockfishchess.org/tests/view/5fb11fac67cbf42301d6ab64
[151120-master]:  https://github.com/official-stockfish/Stockfish/commit/f9595828eb7e5e970b0be3ee5f84ddd726845523
[151120-raw1]:    https://tests.stockfishchess.org/tests/stats/5fb11f8467cbf42301d6ab62
[151120-raw8]:    https://tests.stockfishchess.org/tests/stats/5fb11fac67cbf42301d6ab64
[291120-dif]:     https://github.com/official-stockfish/Stockfish/compare/c306d83869...7364006757
[291120-elo1]:    https://tests.stockfishchess.org/tests/view/5fc3ca3442a050a89f02c9bf
[291120-master]:  https://github.com/official-stockfish/Stockfish/commit/736400675746c6b84a0bdf131babce1b07ade0df
[291120-raw1]:    https://tests.stockfishchess.org/tests/stats/5fc3ca3442a050a89f02c9bf
[141220-dif]:     https://github.com/official-stockfish/Stockfish/compare/c306d83869...a88a38c3a9
[141220-elo1]:    https://tests.stockfishchess.org/tests/view/5fd70ce51ac1691201888628
[141220-elo8]:    https://tests.stockfishchess.org/tests/view/5fd70d211ac169120188862d
[141220-master]:  https://github.com/official-stockfish/Stockfish/commit/a88a38c3a91749181ffa5d6dc0af7314a70a1c41
[141220-raw1]:    https://tests.stockfishchess.org/tests/stats/5fd70ce51ac1691201888628
[141220-raw8]:    https://tests.stockfishchess.org/tests/stats/5fd70d211ac169120188862d
[311220-dif]:     https://github.com/official-stockfish/Stockfish/compare/c306d83869...d21e421ad7
[311220-elo1]:    https://tests.stockfishchess.org/tests/view/5fee0bee6019e097de3eea80
[311220-master]:  https://github.com/official-stockfish/Stockfish/commit/d21e421ad74cff3b157d156d6ea8fdee3634e75b
[311220-raw1]:    https://tests.stockfishchess.org/tests/stats/5fee0bee6019e097de3eea80
[130121-dif]:     https://github.com/official-stockfish/Stockfish/compare/c306d83869...6dddcecb09
[130121-elo1]:    https://tests.stockfishchess.org/tests/view/6000a2616019e097de3ef77d
[130121-elo8]:    https://tests.stockfishchess.org/tests/view/6000a2796019e097de3ef77f
[130121-master]:  https://github.com/official-stockfish/Stockfish/commit/6dddcecb09df268d93810a1a38deb116f97672af
[130121-raw1]:    https://tests.stockfishchess.org/tests/stats/6000a2616019e097de3ef77d
[130121-raw8]:    https://tests.stockfishchess.org/tests/stats/6000a2796019e097de3ef77f
[150221-dif]:     https://github.com/official-stockfish/Stockfish/compare/c306d83869...40cb0f076a
[150221-elo1]:    https://tests.stockfishchess.org/tests/view/602bcccf7f517a561bc49b11
[150221-elo8]:    https://tests.stockfishchess.org/tests/view/602bd7b27f517a561bc49b1e
[150221-master]:  https://github.com/official-stockfish/Stockfish/commit/40cb0f076a62115af030c4524825d9ba73d61023
[150221-raw1]:    https://tests.stockfishchess.org/tests/stats/602bcccf7f517a561bc49b11
[150221-raw8]:    https://tests.stockfishchess.org/tests/stats/602bd7b27f517a561bc49b1e
[Stockfish 13]:   https://github.com/official-stockfish/Stockfish/commit/3597f1942ec6f2cfbd50b905683739b0900ff5dd
[SF13DP]:         https://user-images.githubusercontent.com/64992190/156415393-f800b8c2-344b-4de1-b74a-c9f1715012d5.png "Development Progress"
[SF13RN]:         https://stockfishchess.org/blog/2021/stockfish-13/ "Release Notes"
[180221-dif]:     https://github.com/official-stockfish/Stockfish/compare/c306d83869...3597f1942e
[260221-dif]:     https://github.com/official-stockfish/Stockfish/compare/3597f1942e...0f3f5d85fb
[260221-elo1]:    https://tests.stockfishchess.org/tests/view/603c9ed1e8971688486fff85
[260221-master]:  https://github.com/official-stockfish/Stockfish/commit/0f3f5d85fb5c9f75199f27fbf7a725ff3e8bb4dc
[260221-raw1]:    https://tests.stockfishchess.org/tests/stats/603c9ed1e8971688486fff85
[240321-dif]:     https://github.com/official-stockfish/Stockfish/compare/3597f1942e...83eac08e75
[240321-elo1]:    https://tests.stockfishchess.org/tests/view/605c304bfa3cc97981cfaab7
[240321-master]:  https://github.com/official-stockfish/Stockfish/commit/83eac08e7562d93787f75eccd4b7781c4bd45dd3
[240321-raw1]:    https://tests.stockfishchess.org/tests/stats/605c304bfa3cc97981cfaab7
[150421-dif]:     https://github.com/official-stockfish/Stockfish/compare/3597f1942e...a7ab92ec25
[150421-elo1]:    https://tests.stockfishchess.org/tests/view/60795147162adf76afa5b7a1
[150421-elo8]:    https://tests.stockfishchess.org/tests/view/607951a5162adf76afa5b7a6
[150421-master]:  https://github.com/official-stockfish/Stockfish/commit/a7ab92ec25c91e8413630c52cfc2db6b4ecacf0c
[150421-raw1]:    https://tests.stockfishchess.org/tests/stats/60795147162adf76afa5b7a1
[150421-raw8]:    https://tests.stockfishchess.org/tests/stats/607951a5162adf76afa5b7a6
[220521-dif]:     https://github.com/official-stockfish/Stockfish/compare/3597f1942e...a2f01c07eb
[220521-elo1]:    https://tests.stockfishchess.org/tests/view/60a959adce8ea25a3ef04161
[220521-master]:  https://github.com/official-stockfish/Stockfish/commit/a2f01c07eb91524fc372bd82d6513ab058d3e043
[220521-raw1]:    https://tests.stockfishchess.org/tests/stats/60a959adce8ea25a3ef04161
[140621-dif]:     https://github.com/official-stockfish/Stockfish/compare/3597f1942e...f8c779dbe5
[140621-elo1]:    https://tests.stockfishchess.org/tests/view/60c70ba5457376eb8bcaaede
[140621-elo8]:    https://tests.stockfishchess.org/tests/view/60c711ab457376eb8bcaaef5
[140621-master]:  https://github.com/official-stockfish/Stockfish/commit/f8c779dbe538315aa6f65556d0acf11640558504
[140621-raw1]:    https://tests.stockfishchess.org/tests/stats/60c70ba5457376eb8bcaaede
[140621-raw8]:    https://tests.stockfishchess.org/tests/stats/60c711ab457376eb8bcaaef5
[180621-dif]:     https://github.com/official-stockfish/Stockfish/compare/3597f1942e...adfb23c029
[180621-elo1]:    https://tests.stockfishchess.org/tests/view/60cd9589457376eb8bcab62d
[180621-master]:  https://github.com/official-stockfish/Stockfish/commit/adfb23c029e54c7522aadca1adf3e0b15fdcebcd
[180621-raw1]:    https://tests.stockfishchess.org/tests/stats/60cd9589457376eb8bcab62d
[290621-dif]:     https://github.com/official-stockfish/Stockfish/compare/3597f1942e...2275923d3c
[290621-elo1]:    https://tests.stockfishchess.org/tests/view/60dae5363beab81350aca077
[290621-elo8]:    https://tests.stockfishchess.org/tests/view/60dae6033beab81350aca07b
[290621-master]:  https://github.com/official-stockfish/Stockfish/commit/2275923d3cbca85b433a4d16d40fae5c8de6784a
[290621-raw1]:    https://tests.stockfishchess.org/tests/stats/60dae5363beab81350aca077
[290621-raw8]:    https://tests.stockfishchess.org/tests/stats/60dae6033beab81350aca07b
[Stockfish 14]:   https://github.com/official-stockfish/Stockfish/commit/773dff020968f7a6f590cfd53e8fd89f12e15e36
[SF14DP]:         https://user-images.githubusercontent.com/64992190/156415128-ee9d81c9-7360-47b2-a800-d11a7518bbb1.png "Development Progress"
[SF14RN]:         https://stockfishchess.org/blog/2021/stockfish-14/ "Release Notes"
[020721-dif]:     https://github.com/official-stockfish/Stockfish/compare/3597f1942e...773dff0209
[260721-dif]:     https://github.com/official-stockfish/Stockfish/compare/773dff0209...237ed1ef8f
[260721-elo1]:    https://tests.stockfishchess.org/tests/view/60fe4fa2d8a6b65b2f3a7a59
[260721-master]:  https://github.com/official-stockfish/Stockfish/commit/237ed1ef8fddea77779e7fdcde8e4195d92f123b
[260721-raw1]:    https://tests.stockfishchess.org/tests/stats/60fe4fa2d8a6b65b2f3a7a59
[150821-dif]:     https://github.com/official-stockfish/Stockfish/compare/773dff0209...d61d38586e
[150821-elo1]:    https://tests.stockfishchess.org/tests/view/6118e9ae4977aa1525c9c746
[150821-elo8]:    https://tests.stockfishchess.org/tests/view/6118e9f04977aa1525c9c748
[150821-master]:  https://github.com/official-stockfish/Stockfish/commit/d61d38586ee35fd4d93445eb547e4af27cc86e6b
[150821-raw1]:    https://tests.stockfishchess.org/tests/stats/6118e9ae4977aa1525c9c746
[150821-raw8]:    https://tests.stockfishchess.org/tests/stats/6118e9f04977aa1525c9c748
[310821-dif]:     https://github.com/official-stockfish/Stockfish/compare/773dff0209...2807dcfab6
[310821-elo1]:    https://tests.stockfishchess.org/tests/view/612e0b9fbb4956d8b78eb635
[310821-master]:  https://github.com/official-stockfish/Stockfish/commit/2807dcfab671bfc7a1bea79f5639dbbd505703ad
[310821-raw1]:    https://tests.stockfishchess.org/tests/stats/612e0b9fbb4956d8b78eb635
[150921-dif]:     https://github.com/official-stockfish/Stockfish/compare/773dff0209...723f48dec0
[150921-elo1]:    https://tests.stockfishchess.org/tests/view/6142172c7315e7c73204a614
[150921-elo8]:    https://tests.stockfishchess.org/tests/view/614217467315e7c73204a616
[150921-master]:  https://github.com/official-stockfish/Stockfish/commit/723f48dec0eb05204b51cace54b033a5a85a66b9
[150921-raw1]:    https://tests.stockfishchess.org/tests/stats/6142172c7315e7c73204a614
[150921-raw8]:    https://tests.stockfishchess.org/tests/stats/614217467315e7c73204a616
[061021-dif]:     https://github.com/official-stockfish/Stockfish/compare/773dff0209...54a989930e
[061021-elo1]:    https://tests.stockfishchess.org/tests/view/615dcb711a32f4036ac7fc47
[061021-elo8]:    https://tests.stockfishchess.org/tests/view/615dcb871a32f4036ac7fc49
[061021-master]:  https://github.com/official-stockfish/Stockfish/commit/54a989930ebed200c3278c725151e26a2c0da37a
[061021-raw1]:    https://tests.stockfishchess.org/tests/stats/615dcb711a32f4036ac7fc47
[061021-raw8]:    https://tests.stockfishchess.org/tests/stats/615dcb871a32f4036ac7fc49
[181021-dif]:     https://github.com/official-stockfish/Stockfish/compare/773dff0209...67d0616483
[181021-elo1]:    https://tests.stockfishchess.org/tests/view/616ddbf44f95b438f7a860af
[181021-master]:  https://github.com/official-stockfish/Stockfish/commit/67d06164833857d3497010e952fd0d2c5f00c095
[181021-raw1]:    https://tests.stockfishchess.org/tests/stats/616ddbf44f95b438f7a860af
[231021-dif]:     https://github.com/official-stockfish/Stockfish/compare/773dff0209...2c86ae196d
[231021-elo1]:    https://tests.stockfishchess.org/tests/view/6175c320af70c2be1788fa2b
[231021-elo8]:    https://tests.stockfishchess.org/tests/view/6175c334af70c2be1788fa2d
[231021-master]:  https://github.com/official-stockfish/Stockfish/commit/2c86ae196df8b2a1197e0de1853a6458e404a976
[231021-raw1]:    https://tests.stockfishchess.org/tests/stats/6175c320af70c2be1788fa2b
[231021-raw8]:    https://tests.stockfishchess.org/tests/stats/6175c334af70c2be1788fa2d
[Stockfish 14.1]: https://github.com/official-stockfish/Stockfish/commit/7262fd5d14810b7b495b5038e348a448fda1bcc3
[SF141RN]:        https://stockfishchess.org/blog/2021/stockfish-14-1/ "Release Notes"
[281021-dif]:     https://github.com/official-stockfish/Stockfish/compare/773dff0209...7262fd5d14
[051121-dif]:     https://github.com/official-stockfish/Stockfish/compare/773dff0209...a0259d8ab9
[051121-elo1]:    https://tests.stockfishchess.org/tests/view/6185b066d7a085ad008eefdf
[051121-master]:  https://github.com/official-stockfish/Stockfish/commit/a0259d8ab9661b7f625474d2cbe18481ef69bbf2
[051121-raw1]:    https://tests.stockfishchess.org/tests/stats/6185b066d7a085ad008eefdf
[231121-dif]:     https://github.com/official-stockfish/Stockfish/compare/773dff0209...092b27a6d0
[231121-elo1]:    https://tests.stockfishchess.org/tests/view/619d4e89c0a4ea18ba95a3b8
[231121-elo8]:    https://tests.stockfishchess.org/tests/view/619d4ea9c0a4ea18ba95a3ba
[231121-master]:  https://github.com/official-stockfish/Stockfish/commit/092b27a6d0174f619fff9a53099ac9fdc5c2cb4e
[231121-raw1]:    https://tests.stockfishchess.org/tests/stats/619d4e89c0a4ea18ba95a3b8
[231121-raw8]:    https://tests.stockfishchess.org/tests/stats/619d4ea9c0a4ea18ba95a3ba
[281121-dif]:     https://github.com/official-stockfish/Stockfish/compare/773dff0209...af050e5eed
[281121-elo1]:    https://tests.stockfishchess.org/tests/view/61a385323ce29cae572b920f
[281121-master]:  https://github.com/official-stockfish/Stockfish/commit/af050e5eed43f2d360bc6d38a9d9ef64b6ce6ad8
[281121-raw1]:    https://tests.stockfishchess.org/tests/stats/61a385323ce29cae572b920f
[071221-dif]:     https://github.com/official-stockfish/Stockfish/compare/773dff0209...b82d93ece4
[071221-elo1]:    https://tests.stockfishchess.org/tests/view/61af497356fcf33bce7dd428
[071221-elo8]:    https://tests.stockfishchess.org/tests/view/61af49ae56fcf33bce7dd430
[071221-master]:  https://github.com/official-stockfish/Stockfish/commit/b82d93ece484f833c994b40d9eddd959ba20ef92
[071221-raw1]:    https://tests.stockfishchess.org/tests/stats/61af497356fcf33bce7dd428
[071221-raw8]:    https://tests.stockfishchess.org/tests/stats/61af49ae56fcf33bce7dd430
[141221-dif]:     https://github.com/official-stockfish/Stockfish/compare/773dff0209...c6edf33f53
[141221-elo1]:    https://tests.stockfishchess.org/tests/view/61b896f8dffbe89a358145cb
[141221-master]:  https://github.com/official-stockfish/Stockfish/commit/c6edf33f539f160d4a7009f3aac25e7ec5668eda
[141221-raw1]:    https://tests.stockfishchess.org/tests/stats/61b896f8dffbe89a358145cb
[221221-dif]:     https://github.com/official-stockfish/Stockfish/compare/773dff0209...7d82f0d1f4
[221221-elo1]:    https://tests.stockfishchess.org/tests/view/61c2f921a66b89b0007fff35
[221221-elo8]:    https://tests.stockfishchess.org/tests/view/61c2f986a66b89b0007fff54
[221221-master]:  https://github.com/official-stockfish/Stockfish/commit/7d82f0d1f4e25892e1901d25cf5cf6f6a2606c2a
[221221-raw1]:    https://tests.stockfishchess.org/tests/stats/61c2f921a66b89b0007fff35
[221221-raw8]:    https://tests.stockfishchess.org/tests/stats/61c2f986a66b89b0007fff54
[100122-dif]:     https://github.com/official-stockfish/Stockfish/compare/773dff0209...44b1ba89a9
[100122-elo1]:    https://tests.stockfishchess.org/tests/view/61dc7d27aad48d052737b7a4
[100122-master]:  https://github.com/official-stockfish/Stockfish/commit/44b1ba89a95f394f3e180eb508f2d7798417c86e
[100122-raw1]:    https://tests.stockfishchess.org/tests/stats/61dc7d27aad48d052737b7a4
[290122-dif]:     https://github.com/official-stockfish/Stockfish/compare/773dff0209...90d051952f
[290122-elo1]:    https://tests.stockfishchess.org/tests/view/61f4f474f7fba9f1a4f17837
[290122-elo8]:    https://tests.stockfishchess.org/tests/view/61f4f485f7fba9f1a4f1783c
[290122-master]:  https://github.com/official-stockfish/Stockfish/commit/90d051952f4fce415f09f316e24e1701aafa7a92
[290122-raw1]:    https://tests.stockfishchess.org/tests/stats/61f4f474f7fba9f1a4f17837
[290122-raw8]:    https://tests.stockfishchess.org/tests/stats/61f4f485f7fba9f1a4f1783c
[100222-dif]:     https://github.com/official-stockfish/Stockfish/compare/773dff0209...cb9c2594fc
[100222-elo1]:    https://tests.stockfishchess.org/tests/view/620562ffd71106ed12a449a6
[100222-elo8]:    https://tests.stockfishchess.org/tests/view/620822bed71106ed12a4af70
[100222-master]:  https://github.com/official-stockfish/Stockfish/commit/cb9c2594fcedc881ae8f8bfbfdf130cf89840e4c
[100222-raw1]:    https://tests.stockfishchess.org/tests/stats/620562ffd71106ed12a449a6
[100222-raw8]:    https://tests.stockfishchess.org/tests/stats/620822bed71106ed12a4af70
[170222-dif]:     https://github.com/official-stockfish/Stockfish/compare/773dff0209...84b1940fca
[170222-elo1]:    https://tests.stockfishchess.org/tests/view/6210f2e5b1792e8985f86e01
[170222-elo8]:    https://tests.stockfishchess.org/tests/view/62115f93b1792e8985f87eb3
[170222-master]:  https://github.com/official-stockfish/Stockfish/commit/84b1940fcae95bb0a641dda9e85cb96f8c21cd22
[170222-raw1]:    https://tests.stockfishchess.org/tests/stats/6210f2e5b1792e8985f86e01
[170222-raw8]:    https://tests.stockfishchess.org/tests/stats/62115f93b1792e8985f87eb3
[190322-dif]:     https://github.com/official-stockfish/Stockfish/compare/773dff0209...e31f97e3ba
[190322-elo1]:    https://tests.stockfishchess.org/tests/view/6235d03aceed04483e6f16d8
[190322-master]:  https://github.com/official-stockfish/Stockfish/commit/e31f97e3baa52042fe60d6f4eeb50fe0d9e61013
[190322-raw1]:    https://tests.stockfishchess.org/tests/stats/6235d03aceed04483e6f16d8
[170422-dif]:     https://github.com/official-stockfish/Stockfish/compare/773dff0209...df2f7e7527
[170422-elo1]:    https://tests.stockfishchess.org/tests/view/625d156dff677a888877d1be
[170422-elo1uho]: https://tests.stockfishchess.org/tests/view/625d2400ff677a888877d3df
[170422-elo8]:    https://tests.stockfishchess.org/tests/view/625d1586ff677a888877d1c5
[170422-master]:  https://github.com/official-stockfish/Stockfish/commit/df2f7e75276cc93a8cb8c70057903ab0edbd92bd
[170422-raw1]:    https://tests.stockfishchess.org/tests/stats/625d156dff677a888877d1be
[170422-raw1uho]: https://tests.stockfishchess.org/tests/stats/625d2400ff677a888877d3df
[170422-raw8]:    https://tests.stockfishchess.org/tests/stats/625d1586ff677a888877d1c5
[Stockfish 15]:   https://github.com/official-stockfish/Stockfish/commit/e6e324eb28fd49c1fc44b3b65784f85a773ec61c
[SF15DP]:         https://user-images.githubusercontent.com/64992190/163892421-aa025052-53ab-4a53-9162-4043b6f021b0.png "Development Progress"
[SF15RN]:         https://stockfishchess.org/blog/2022/stockfish-15/ "Release Notes"
[180422-dif]:     https://github.com/official-stockfish/Stockfish/compare/773dff0209...e6e324eb28
[140522-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...5372f81cc8
[140522-elo1]:    https://tests.stockfishchess.org/tests/view/627f9a5c56be8ced122d7df7
[140522-elo8]:    https://tests.stockfishchess.org/tests/view/627f9a7356be8ced122d7dfe
[140522-master]:  https://github.com/official-stockfish/Stockfish/commit/5372f81cc81d5be3040db6f2dbfff108c460baf9
[140522-raw1]:    https://tests.stockfishchess.org/tests/stats/627f9a5c56be8ced122d7df7
[140522-raw8]:    https://tests.stockfishchess.org/tests/stats/627f9a7356be8ced122d7dfe
[160622-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...6edc29d720
[160622-elo1]:    https://tests.stockfishchess.org/tests/view/62aac16750949cfc241b0f15
[160622-master]:  https://github.com/official-stockfish/Stockfish/commit/6edc29d720b43383a04bd2208e9666a6f3173a64
[160622-raw1]:    https://tests.stockfishchess.org/tests/stats/62aac16750949cfc241b0f15
[130722-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...4b4b7d1209
[130722-elo1]:    https://tests.stockfishchess.org/tests/view/62ceecfc877d5077fe6e4714
[130722-elo8]:    https://tests.stockfishchess.org/tests/view/62ceed0e877d5077fe6e4718
[130722-master]:  https://github.com/official-stockfish/Stockfish/commit/4b4b7d1209259811537634c68555d2a8f4af197c
[130722-raw1]:    https://tests.stockfishchess.org/tests/stats/62ceecfc877d5077fe6e4714
[130722-raw8]:    https://tests.stockfishchess.org/tests/stats/62ceed0e877d5077fe6e4718
[120822-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...1054a483ca
[120822-elo1]:    https://tests.stockfishchess.org/tests/view/62f64a886f0a08af9f7767aa
[120822-elo1uho]: https://tests.stockfishchess.org/tests/view/62f9d9e623d42b50a8daf3b2
[120822-elo8]:    https://tests.stockfishchess.org/tests/view/62f64a9c6f0a08af9f7767ae
[120822-master]:  https://github.com/official-stockfish/Stockfish/commit/1054a483ca0c560d30fb61617c0192cb4cd31528
[120822-raw1]:    https://tests.stockfishchess.org/tests/stats/62f64a886f0a08af9f7767aa
[120822-raw1uho]: https://tests.stockfishchess.org/tests/stats/62f9d9e623d42b50a8daf3b2
[120822-raw8]:    https://tests.stockfishchess.org/tests/stats/62f64a9c6f0a08af9f7767ae
[070922-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...5eeb96d0e7
[070922-elo1]:    https://tests.stockfishchess.org/tests/view/631835ed37f41b13973d7d81
[070922-elo8]:    https://tests.stockfishchess.org/tests/view/6318361537f41b13973d7d8a
[070922-master]:  https://github.com/official-stockfish/Stockfish/commit/5eeb96d0e7d54686376305029c477c42478aa1d5
[070922-raw1]:    https://tests.stockfishchess.org/tests/stats/631835ed37f41b13973d7d81
[070922-raw8]:    https://tests.stockfishchess.org/tests/stats/6318361537f41b13973d7d8a
[051022-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...da937e219e
[051022-elo1]:    https://tests.stockfishchess.org/tests/view/633df173fb7ccb2ea9bd732a
[051022-elo8]:    https://tests.stockfishchess.org/tests/view/633df17efb7ccb2ea9bd732c
[051022-master]:  https://github.com/official-stockfish/Stockfish/commit/da937e219ee7981966ac29fc11c43470a505ff18
[051022-raw1]:    https://tests.stockfishchess.org/tests/stats/633df173fb7ccb2ea9bd732a
[051022-raw8]:    https://tests.stockfishchess.org/tests/stats/633df17efb7ccb2ea9bd732c
[301022-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...d09653df0d
[301022-elo1]:    https://tests.stockfishchess.org/tests/view/635e9692a7c06f6479d40009
[301022-elo1uho]: https://tests.stockfishchess.org/tests/view/635efedba7c06f6479d40ae6
[301022-elo8]:    https://tests.stockfishchess.org/tests/view/635e96b4a7c06f6479d4000c
[301022-master]:  https://github.com/official-stockfish/Stockfish/commit/d09653df0d1bfec0af05ab2e8975e0d8e5cccba8
[301022-raw1]:    https://tests.stockfishchess.org/tests/stats/635e9692a7c06f6479d40009
[301022-raw1uho]: https://tests.stockfishchess.org/tests/stats/635efedba7c06f6479d40ae6
[301022-raw8]:    https://tests.stockfishchess.org/tests/stats/635e96b4a7c06f6479d4000c
[021222-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...d60f5de967
[021222-elo1]:    https://tests.stockfishchess.org/tests/view/638a4dd7d2b9c924c4c6297b
[021222-elo1uho]: https://tests.stockfishchess.org/tests/view/638a5275d2b9c924c4c62a3c
[021222-elo8]:    https://tests.stockfishchess.org/tests/view/638a4ddfd2b9c924c4c6297e
[021222-master]:  https://github.com/official-stockfish/Stockfish/commit/d60f5de9670cc84ba7940b5815bc3e128da9423f
[021222-raw1]:    https://tests.stockfishchess.org/tests/stats/638a4dd7d2b9c924c4c6297b
[021222-raw1uho]: https://tests.stockfishchess.org/tests/stats/638a5275d2b9c924c4c62a3c
[021222-raw8]:    https://tests.stockfishchess.org/tests/stats/638a4ddfd2b9c924c4c6297e
[Stockfish 15.1]: https://github.com/official-stockfish/Stockfish/commit/758f9c9350abee36a5865ec701560db8ea62004d
[SF151RN]:        https://stockfishchess.org/blog/2022/stockfish-15-1/ "Release Notes"
[041222-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...758f9c9350
[191222-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...c2d507005c
[191222-elo1]:    https://tests.stockfishchess.org/tests/view/63a0c0d3586179db6eb3fce6
[191222-master]:  https://github.com/official-stockfish/Stockfish/commit/c2d507005c51145211a7963af7c41026bd759d08
[191222-raw1]:    https://tests.stockfishchess.org/tests/stats/63a0c0d3586179db6eb3fce6
[010123-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...be9bc420af
[010123-elo1]:    https://tests.stockfishchess.org/tests/view/63b16fcc9b0bd9e1091ceab3
[010123-elo1uho]: https://tests.stockfishchess.org/tests/view/63cd134d344bb01c191b48ae
[010123-elo8]:    https://tests.stockfishchess.org/tests/view/63b16fd69b0bd9e1091ceab9
[010123-master]:  https://github.com/official-stockfish/Stockfish/commit/be9bc420afa11314c886c0aede4c4ae3d76f8a50
[010123-raw1]:    https://tests.stockfishchess.org/tests/stats/63b16fcc9b0bd9e1091ceab3
[010123-raw1uho]: https://tests.stockfishchess.org/tests/stats/63cd134d344bb01c191b48ae
[010123-raw8]:    https://tests.stockfishchess.org/tests/stats/63b16fd69b0bd9e1091ceab9
[230123-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...596a528c6a
[230123-elo1]:    https://tests.stockfishchess.org/tests/view/63ce238dc93e8828d0f03aaa
[230123-elo1uho]: https://tests.stockfishchess.org/tests/view/63ce23bcc93e8828d0f03ab6
[230123-elo8]:    https://tests.stockfishchess.org/tests/view/63ce2398c93e8828d0f03ab0
[230123-master]:  https://github.com/official-stockfish/Stockfish/commit/596a528c6a9ace6fb1a8407c86d972d96653418d
[230123-raw1]:    https://tests.stockfishchess.org/tests/stats/63ce238dc93e8828d0f03aaa
[230123-raw1uho]: https://tests.stockfishchess.org/tests/stats/63ce23bcc93e8828d0f03ab6
[230123-raw8]:    https://tests.stockfishchess.org/tests/stats/63ce2398c93e8828d0f03ab0
[090223-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...05dea2ca46
[090223-elo1]:    https://tests.stockfishchess.org/tests/view/63e498e6b5f425d71f771dbc
[090223-elo1uho]: https://tests.stockfishchess.org/tests/view/63e49921b5f425d71f771dc7
[090223-elo8]:    https://tests.stockfishchess.org/tests/view/63e498f0b5f425d71f771dbe
[090223-master]:  https://github.com/official-stockfish/Stockfish/commit/05dea2ca4657dec10637bb53c4ad583f680e0677
[090223-raw1]:    https://tests.stockfishchess.org/tests/stats/63e498e6b5f425d71f771dbc
[090223-raw1uho]: https://tests.stockfishchess.org/tests/stats/63e49921b5f425d71f771dc7
[090223-raw8]:    https://tests.stockfishchess.org/tests/stats/63e498f0b5f425d71f771dbe
[180223-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...037ef3e18d
[180223-elo1]:    https://tests.stockfishchess.org/tests/view/63f0d381e74a12625bcc61e5
[180223-elo1uho]: https://tests.stockfishchess.org/tests/view/63f0d392e74a12625bcc61eb
[180223-master]:  https://github.com/official-stockfish/Stockfish/commit/037ef3e18dc7f5455cc671995ae38d5b4d1fce4a
[180223-raw1]:    https://tests.stockfishchess.org/tests/stats/63f0d381e74a12625bcc61e5
[180223-raw1uho]: https://tests.stockfishchess.org/tests/stats/63f0d392e74a12625bcc61eb
[240223-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...472e726bff
[240223-elo1]:    https://tests.stockfishchess.org/tests/view/63f90ecee74a12625bcdd191
[240223-elo1uho]: https://tests.stockfishchess.org/tests/view/63f90edce74a12625bcdd197
[240223-elo8]:    https://tests.stockfishchess.org/tests/view/63f90ee7e74a12625bcdd19c
[240223-master]:  https://github.com/official-stockfish/Stockfish/commit/472e726bff0d0e496dc8359cc071726a76317a72
[240223-raw1]:    https://tests.stockfishchess.org/tests/stats/63f90ecee74a12625bcdd191
[240223-raw1uho]: https://tests.stockfishchess.org/tests/stats/63f90edce74a12625bcdd197
[240223-raw8]:    https://tests.stockfishchess.org/tests/stats/63f90ee7e74a12625bcdd19c
[190323-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...02e4697055
[190323-elo1]:    https://tests.stockfishchess.org/tests/view/6416e54965775d3b539ebf93
[190323-elo1uho]: https://tests.stockfishchess.org/tests/view/6416e57365775d3b539ebf9e
[190323-elo8]:    https://tests.stockfishchess.org/tests/view/6416e55265775d3b539ebf96
[190323-master]:  https://github.com/official-stockfish/Stockfish/commit/02e4697055519ed206fa76e4ef9abb9f156cd1a0
[190323-raw1]:    https://tests.stockfishchess.org/tests/stats/6416e54965775d3b539ebf93
[190323-raw1uho]: https://tests.stockfishchess.org/tests/stats/6416e57365775d3b539ebf9e
[190323-raw8]:    https://tests.stockfishchess.org/tests/stats/6416e55265775d3b539ebf96
[010423-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...6a6e32dfc8
[010423-elo1]:    https://tests.stockfishchess.org/tests/view/6428409fdb43ab2ba6fa2e8d
[010423-elo1uho]: https://tests.stockfishchess.org/tests/view/642840b9db43ab2ba6fa2e97
[010423-elo8]:    https://tests.stockfishchess.org/tests/view/642840a8db43ab2ba6fa2e93
[010423-master]:  https://github.com/official-stockfish/Stockfish/commit/6a6e32dfc80488dfdcd6c23e6001063b47729e890
[010423-raw1]:    https://tests.stockfishchess.org/tests/stats/6428409fdb43ab2ba6fa2e8d
[010423-raw1uho]: https://tests.stockfishchess.org/tests/stats/642840b9db43ab2ba6fa2e97
[010423-raw8]:    https://tests.stockfishchess.org/tests/stats/642840a8db43ab2ba6fa2e93
[220423-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...ba06c480a7
[220423-elo1]:    https://tests.stockfishchess.org/tests/view/6443a560bc6f5930d1d36ba4
[220423-elo1uho]: https://tests.stockfishchess.org/tests/view/6443a581bc6f5930d1d36baa
[220423-elo8]:    https://tests.stockfishchess.org/tests/view/6443a569bc6f5930d1d36ba6
[220423-master]:  https://github.com/official-stockfish/Stockfish/commit/ba06c480a752458a8159db0c9110bd3b7e34145a
[220423-raw1]:    https://tests.stockfishchess.org/tests/stats/6443a560bc6f5930d1d36ba4
[220423-raw1uho]: https://tests.stockfishchess.org/tests/stats/6443a581bc6f5930d1d36baa
[220423-raw8]:    https://tests.stockfishchess.org/tests/stats/6443a569bc6f5930d1d36ba6
[070523-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...65e2150501
[070523-elo1]:    https://tests.stockfishchess.org/tests/view/64580c878ab4042ca7893e81
[070523-elo1uho]: https://tests.stockfishchess.org/tests/view/64580ca68ab4042ca7893e86
[070523-elo8]:    https://tests.stockfishchess.org/tests/view/64580c8e8ab4042ca7893e83
[070523-master]:  https://github.com/official-stockfish/Stockfish/commit/65e2150501b87e6ce00fae4e3f056444f39462fd
[070523-raw1]:    https://tests.stockfishchess.org/tests/stats/64580c878ab4042ca7893e81
[070523-raw1uho]: https://tests.stockfishchess.org/tests/stats/64580ca68ab4042ca7893e86
[070523-raw8]:    https://tests.stockfishchess.org/tests/stats/64580c8e8ab4042ca7893e83
[040623-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...8dea070538
[040623-elo1]:    https://tests.stockfishchess.org/tests/view/647d01b97cf638f0f53fa028
[040623-elo1uho]: https://tests.stockfishchess.org/tests/view/647d01c97cf638f0f53fa02b
[040623-elo8]:    https://tests.stockfishchess.org/tests/view/647d01db7cf638f0f53fa02e
[040623-master]:  https://github.com/official-stockfish/Stockfish/commit/8dea070538dcad790de3c5b9720bdbb836a32440
[040623-raw1]:    https://tests.stockfishchess.org/tests/stats/647d01b97cf638f0f53fa028
[040623-raw1uho]: https://tests.stockfishchess.org/tests/stats/647d01c97cf638f0f53fa02b
[040623-raw8]:    https://tests.stockfishchess.org/tests/stats/647d01db7cf638f0f53fa02e
[120623-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...38e61663d8
[120623-elo1]:    https://tests.stockfishchess.org/tests/view/64876b43713491385c8030ec
[120623-elo1uho]: https://tests.stockfishchess.org/tests/view/64876b6b713491385c8030f6
[120623-elo8]:    https://tests.stockfishchess.org/tests/view/64876b51713491385c8030f0
[120623-master]:  https://github.com/official-stockfish/Stockfish/commit/38e61663d836e062af0bc002814ad5149c4b7729
[120623-raw1]:    https://tests.stockfishchess.org/tests/stats/64876b43713491385c8030ec
[120623-raw1uho]: https://tests.stockfishchess.org/tests/stats/64876b6b713491385c8030f6
[120623-raw8]:    https://tests.stockfishchess.org/tests/stats/64876b51713491385c8030f0
[220623-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...a49b3ba7ed
[220623-elo1]:    https://tests.stockfishchess.org/tests/view/6494094adc7002ce609c99a4
[220623-elo1uho]: https://tests.stockfishchess.org/tests/view/6494097ddc7002ce609c99b7
[220623-elo8]:    https://tests.stockfishchess.org/tests/view/64940956dc7002ce609c99a7
[220623-master]:  https://github.com/official-stockfish/Stockfish/commit/a49b3ba7ed5d9be9151c8ceb5eed40efe3387c75
[220623-raw1]:    https://tests.stockfishchess.org/tests/stats/6494094adc7002ce609c99a4
[220623-raw1uho]: https://tests.stockfishchess.org/tests/stats/6494097ddc7002ce609c99b7
[220623-raw8]:    https://tests.stockfishchess.org/tests/stats/64940956dc7002ce609c99a7

[Stockfish 16]:   https://github.com/official-stockfish/Stockfish/commit/68e1e9b381
[SF16DP]:         https://github.com/official-stockfish/Stockfish/assets/63931154/5297318e-89fb-407f-a8a8-9e4278d90eda "Development Progress"
[SF16RN]:         https://stockfishchess.org/blog/2023/stockfish-16/ "Release Notes"
[290623-dif]:     https://github.com/official-stockfish/Stockfish/compare/e6e324eb28...68e1e9b381

[190723-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...5ea1cbc778
[190723-elo1]:    https://tests.stockfishchess.org/tests/view/64b83cd1dc56e1650abad318
[190723-elo8]:    https://tests.stockfishchess.org/tests/view/64b83cdbdc56e1650abad31a
[190723-master]:  https://github.com/official-stockfish/Stockfish/commit/5ea1cbc778508a9a7b720becaf22dd96a4472826
[190723-raw1]:    https://tests.stockfishchess.org/tests/stats/64b83cd1dc56e1650abad318
[190723-raw8]:    https://tests.stockfishchess.org/tests/stats/64b83cdbdc56e1650abad31a
[130823-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...9b80897657
[130823-elo1]:    https://tests.stockfishchess.org/tests/view/64d8af545b17f7c21c0e854c
[130823-elo8]:    https://tests.stockfishchess.org/tests/view/64d8af655b17f7c21c0e854f
[130823-master]:  https://github.com/official-stockfish/Stockfish/commit/9b80897657bde99cfb6568d8bd3386c3999f22c4
[130823-raw1]:    https://tests.stockfishchess.org/tests/stats/64d8af545b17f7c21c0e854c
[130823-raw8]:    https://tests.stockfishchess.org/tests/stats/64d8af655b17f7c21c0e854f
[110923-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...b9319c4fa4
[110923-elo1]:    https://tests.stockfishchess.org/tests/view/64ff804d2cd016da89ab747f
[110923-elo8]:    https://tests.stockfishchess.org/tests/view/64ff80602cd016da89ab7484
[110923-master]:  https://github.com/official-stockfish/Stockfish/commit/b9319c4fa4f42438f484d144be9a1306765cf998
[110923-raw1]:    https://tests.stockfishchess.org/tests/stats/64ff804d2cd016da89ab747f
[110923-raw8]:    https://tests.stockfishchess.org/tests/stats/64ff80602cd016da89ab7484
[220923-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...70ba9de85c
[220923-elo1]:    https://tests.stockfishchess.org/tests/view/650dcf1bfb151d43ae6d704f
[220923-elo8]:    https://tests.stockfishchess.org/tests/view/650dcf25fb151d43ae6d7052
[220923-master]:  https://github.com/official-stockfish/Stockfish/commit/70ba9de85cddc5460b1ec53e0a99bee271e26ece
[220923-raw1]:    https://tests.stockfishchess.org/tests/stats/650dcf1bfb151d43ae6d704f
[220923-raw8]:    https://tests.stockfishchess.org/tests/stats/650dcf25fb151d43ae6d7052
[081023-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...7a4de96159
[081023-elo1]:    https://tests.stockfishchess.org/tests/view/652244f53125598fc7eb225b
[081023-elo8]:    https://tests.stockfishchess.org/tests/view/652245013125598fc7eb225d
[081023-master]:  https://github.com/official-stockfish/Stockfish/commit/7a4de96159f76f2465d474d76e08a1c8ca3383b8
[081023-raw1]:    https://tests.stockfishchess.org/tests/stats/652244f53125598fc7eb225b
[081023-raw8]:    https://tests.stockfishchess.org/tests/stats/652245013125598fc7eb225d
[231023-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...49ece9f791
[231023-elo1]:    https://tests.stockfishchess.org/tests/view/6536be80cc309ae83955ad1a
[231023-elo8]:    https://tests.stockfishchess.org/tests/view/6536be88cc309ae83955ad1d
[231023-master]:  https://github.com/official-stockfish/Stockfish/commit/49ece9f791b84a261f2a8865d2de51c20a520bc6
[231023-raw1]:    https://tests.stockfishchess.org/tests/stats/6536be80cc309ae83955ad1a
[231023-raw8]:    https://tests.stockfishchess.org/tests/stats/6536be88cc309ae83955ad1d
[031123-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...b4b704e686
[031123-elo1]:    https://tests.stockfishchess.org/tests/view/65456b94136acbc573523e28
[031123-elo8]:    https://tests.stockfishchess.org/tests/view/65456b9e136acbc573523e2c
[031123-master]:  https://github.com/official-stockfish/Stockfish/commit/b4b704e6866bde21c69cd53457a6a91a15182b36
[031123-raw1]:    https://tests.stockfishchess.org/tests/stats/65456b94136acbc573523e28
[031123-raw8]:    https://tests.stockfishchess.org/tests/stats/65456b9e136acbc573523e2c
[021223-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...08cdbca56f
[021223-elo1]:    https://tests.stockfishchess.org/tests/view/656b4e3a136acbc573556df1
[021223-elo8]:    https://tests.stockfishchess.org/tests/view/656b4e3e136acbc573556df3
[021223-master]:  https://github.com/official-stockfish/Stockfish/commit/08cdbca56fac98513481683a92eb1ecdc00d3f6e
[021223-raw1]:    https://tests.stockfishchess.org/tests/stats/656b4e3a136acbc573556df1
[021223-raw8]:    https://tests.stockfishchess.org/tests/stats/656b4e3e136acbc573556df3
[311223-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...3cfaef7431
[311223-elo1]:    https://tests.stockfishchess.org/tests/view/6591bf1a79aa8af82b958776
[311223-elo8]:    https://tests.stockfishchess.org/tests/view/6591bf2c79aa8af82b95877a
[311223-master]:  https://github.com/official-stockfish/Stockfish/commit/3cfaef74311e943298a9a82bce5717d272338e66
[311223-raw1]:    https://tests.stockfishchess.org/tests/stats/6591bf1a79aa8af82b958776
[311223-raw8]:    https://tests.stockfishchess.org/tests/stats/6591bf2c79aa8af82b95877a
[070124-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...7c5e3f2865
[070124-elo1]:    https://tests.stockfishchess.org/tests/view/659b0cee79aa8af82b963dab
[070124-elo8]:    https://tests.stockfishchess.org/tests/view/659b0cf179aa8af82b963dae
[070124-master]:  https://github.com/official-stockfish/Stockfish/commit/7c5e3f28655607288a980645e6b2ce600a627b11
[070124-raw1]:    https://tests.stockfishchess.org/tests/stats/659b0cee79aa8af82b963dab
[070124-raw8]:    https://tests.stockfishchess.org/tests/stats/659b0cf179aa8af82b963dae
[210124-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...a6fd17f27d
[210124-elo1]:    https://tests.stockfishchess.org/tests/view/65ad061879aa8af82b979da1
[210124-elo8]:    https://tests.stockfishchess.org/tests/view/65ad061f79aa8af82b979da3
[210124-master]:  https://github.com/official-stockfish/Stockfish/commit/a6fd17f27d7675332166e9e6ea8210237281fc77
[210124-raw1]:    https://tests.stockfishchess.org/tests/stats/65ad061879aa8af82b979da1
[210124-raw8]:    https://tests.stockfishchess.org/tests/stats/65ad061f79aa8af82b979da3
[110224-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...7ccde25baf
[110224-elo1]:    https://tests.stockfishchess.org/tests/view/65c9391b1d8e83c78bfcdd46
[110224-elo8]:    https://tests.stockfishchess.org/tests/view/65c939221d8e83c78bfcdd48
[110224-master]:  https://github.com/official-stockfish/Stockfish/commit/7ccde25baf03e77926644b282fed68ba0b5ddf95
[110224-raw1]:    https://tests.stockfishchess.org/tests/stats/65c9391b1d8e83c78bfcdd46
[110224-raw8]:    https://tests.stockfishchess.org/tests/stats/65c939221d8e83c78bfcdd48
[170224-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...fc41f64dfd
[170224-elo1]:    https://tests.stockfishchess.org/tests/view/65d666051d8e83c78bfddbd6
[170224-elo8]:    https://tests.stockfishchess.org/tests/view/65d666051d8e83c78bfddbd8
[170224-master]:  https://github.com/official-stockfish/Stockfish/commit/fc41f64dfd8a61d0e275ddbecec292833458b86a
[170224-raw1]:    https://tests.stockfishchess.org/tests/stats/65d666051d8e83c78bfddbd6
[170224-raw8]:    https://tests.stockfishchess.org/tests/stats/65d666051d8e83c78bfddbd8

[Stockfish 16.1]: https://github.com/official-stockfish/Stockfish/commit/e67cc979fd2c0e66dfc2b2f2daa0117458cfc462
[SF161RN]:        https://stockfishchess.org/blog/2024/stockfish-16-1/ "Release Notes"
[240224-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...e67cc979fd

[120324-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...627974c99f
[120324-elo1]:    https://tests.stockfishchess.org/tests/view/65f0798e0ec64f0526c463e5
[120324-elo8]:    https://tests.stockfishchess.org/tests/view/65f079910ec64f0526c463e7
[120324-master]:  https://github.com/official-stockfish/Stockfish/commit/627974c99fcd5a3dcbd5a8e0eb12f2afeb2d0a9a
[120324-raw1]:    https://tests.stockfishchess.org/tests/stats/65f0798e0ec64f0526c463e5
[120324-raw8]:    https://tests.stockfishchess.org/tests/stats/65f079910ec64f0526c463e7
[290324-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...e13e4cfb83
[290324-elo1]:    https://tests.stockfishchess.org/tests/view/660688190ec64f0526c59e5a
[290324-elo8]:    https://tests.stockfishchess.org/tests/view/660688240ec64f0526c59e5c
[290324-master]:  https://github.com/official-stockfish/Stockfish/commit/e13e4cfb8340cdb26a00679681a0f163c6b4f0a9
[290324-raw1]:    https://tests.stockfishchess.org/tests/stats/660688190ec64f0526c59e5a
[290324-raw8]:    https://tests.stockfishchess.org/tests/stats/660688240ec64f0526c59e5c
[110424-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...249eec6715
[110424-elo1]:    https://tests.stockfishchess.org/tests/view/66184ce85a4693796d966cba
[110424-elo8]:    https://tests.stockfishchess.org/tests/view/66184cf15a4693796d966cbc
[110424-master]:  https://github.com/official-stockfish/Stockfish/commit/249eec67152d334d76c0f981907a6f5787289443
[110424-raw1]:    https://tests.stockfishchess.org/tests/stats/66184ce85a4693796d966cba
[110424-raw8]:    https://tests.stockfishchess.org/tests/stats/66184cf15a4693796d966cbc
[240424-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...49ef4c935a
[240424-elo1]:    https://tests.stockfishchess.org/tests/view/66293d2a3fe04ce4cefc7a5f
[240424-elo8]:    https://tests.stockfishchess.org/tests/view/66293d2e3fe04ce4cefc7a61
[240424-master]:  https://github.com/official-stockfish/Stockfish/commit/49ef4c935a5cb0e4d94096e6354caa06b36b3e3c
[240424-raw1]:    https://tests.stockfishchess.org/tests/stats/66293d2a3fe04ce4cefc7a5f
[240424-raw8]:    https://tests.stockfishchess.org/tests/stats/66293d2e3fe04ce4cefc7a61
[050524-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...070e564c38
[050524-elo1]:    https://tests.stockfishchess.org/tests/view/663787949819650825aa6773
[050524-elo8]:    https://tests.stockfishchess.org/tests/view/663787959819650825aa6777
[050524-master]:  https://github.com/official-stockfish/Stockfish/commit/070e564c389eb2c263f3982060ab5899b67d0a62
[050524-raw1]:    https://tests.stockfishchess.org/tests/stats/663787949819650825aa6773
[050524-raw8]:    https://tests.stockfishchess.org/tests/stats/663787959819650825aa6777
[130524-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...e608eab8dd
[130524-elo1]:    https://tests.stockfishchess.org/tests/view/6641a8bef9f4e8fc783cb991
[130524-elo8]:    https://tests.stockfishchess.org/tests/view/6641a8c8f9f4e8fc783cb993
[130524-master]:  https://github.com/official-stockfish/Stockfish/commit/e608eab8dd9f7bd68f192d56d742f621674b8fa8
[130524-raw1]:    https://tests.stockfishchess.org/tests/stats/6641a8bef9f4e8fc783cb991
[130524-raw8]:    https://tests.stockfishchess.org/tests/stats/6641a8c8f9f4e8fc783cb993
[180524-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...99f1bacfd6
[180524-elo1]:    https://tests.stockfishchess.org/tests/view/6648e29e02679895021d0594
[180524-elo8]:    https://tests.stockfishchess.org/tests/view/6648e2a602679895021d0596
[180524-master]:  https://github.com/official-stockfish/Stockfish/commit/99f1bacfd6864afca86ae74f33232b9cdfb3828c
[180524-raw1]:    https://tests.stockfishchess.org/tests/stats/6648e29e02679895021d0594
[180524-raw8]:    https://tests.stockfishchess.org/tests/stats/6648e2a602679895021d0596
[280524-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...a169c78b6d
[280524-elo1]:    https://tests.stockfishchess.org/tests/view/6656c2f46b0e318cefa8bbd8
[280524-elo8]:    https://tests.stockfishchess.org/tests/view/6656c30a6b0e318cefa8bbdb
[280524-master]:  https://github.com/official-stockfish/Stockfish/commit/a169c78b6d3b082068deb49a39aaa1fd75464c7f
[280524-raw1]:    https://tests.stockfishchess.org/tests/stats/6656c2f46b0e318cefa8bbd8
[280524-raw8]:    https://tests.stockfishchess.org/tests/stats/6656c30a6b0e318cefa8bbdb
[080624-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...e271059e08
[080624-elo1]:    https://tests.stockfishchess.org/tests/view/6664d56822234461cef58e71
[080624-elo8]:    https://tests.stockfishchess.org/tests/view/6664d56b22234461cef58e73
[080624-master]:  https://github.com/official-stockfish/Stockfish/commit/e271059e08c6258420af12897367ea2149220171
[080624-raw1]:    https://tests.stockfishchess.org/tests/stats/6664d56822234461cef58e71
[080624-raw8]:    https://tests.stockfishchess.org/tests/stats/6664d56b22234461cef58e73
[010724-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...6138a0fd0e
[010724-elo1]:    https://tests.stockfishchess.org/tests/view/6683a08cc4f539faa03268e3
[010724-elo8]:    https://tests.stockfishchess.org/tests/view/6683a096c4f539faa03268e5
[010724-master]:  https://github.com/official-stockfish/Stockfish/commit/6138a0fd0e43753a86e4a170a5f6e2b7b6752677
[010724-raw1]:    https://tests.stockfishchess.org/tests/stats/6683a08cc4f539faa03268e3
[010724-raw8]:    https://tests.stockfishchess.org/tests/stats/6683a096c4f539faa03268e5
[090724-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...362a77a345
[090724-elo1]:    https://tests.stockfishchess.org/tests/view/668d79a65034141ae5999e43
[090724-elo8]:    https://tests.stockfishchess.org/tests/view/668d79ae5034141ae5999e45
[090724-master]:  https://github.com/official-stockfish/Stockfish/commit/362a77a3450335e1940020c080bf3b7b361c594a
[090724-raw1]:    https://tests.stockfishchess.org/tests/stats/668d79a65034141ae5999e43
[090724-raw8]:    https://tests.stockfishchess.org/tests/stats/668d79ae5034141ae5999e45
[230724-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...b55217fd02
[230724-elo1]:    https://tests.stockfishchess.org/tests/view/669feadf4ff211be9d4ecaf4
[230724-elo8]:    https://tests.stockfishchess.org/tests/view/669feae74ff211be9d4ecaf6
[230724-master]:  https://github.com/official-stockfish/Stockfish/commit/b55217fd02d8e5bc0754e5f27bc84df7b01479a6
[230724-raw1]:    https://tests.stockfishchess.org/tests/stats/669feadf4ff211be9d4ecaf4
[230724-raw8]:    https://tests.stockfishchess.org/tests/stats/669feae74ff211be9d4ecaf6
[200824-dif]:     https://github.com/official-stockfish/Stockfish/compare/68e1e9b381...9fb58328e3
[200824-elo1]:    https://tests.stockfishchess.org/tests/view/66c4f20021503a509c13b8b7
[200824-elo8]:    https://tests.stockfishchess.org/tests/view/66c4f21721503a509c13b8b9
[200824-master]:  https://github.com/official-stockfish/Stockfish/commit/9fb58328e363d84e3cf720b018e639b139ba95c2
[200824-raw1]:    https://tests.stockfishchess.org/tests/stats/66c4f20021503a509c13b8b7
[200824-raw8]:    https://tests.stockfishchess.org/tests/stats/66c4f21721503a509c13b8b9

[graph-current]:  https://docs.google.com/spreadsheets/u/2/d/e/2PACX-1vQqw86SXD_-zzP39DzfjBQ1eLBGyZMPyVLPuZDTY7zSNxBvxxj9CUXpd_AHRKy1aCpCCXGsznolmMVs/pubchart?oid=429149495&format=image
[graph-elo1]:     https://docs.google.com/spreadsheets/d/e/2PACX-1vQqw86SXD_-zzP39DzfjBQ1eLBGyZMPyVLPuZDTY7zSNxBvxxj9CUXpd_AHRKy1aCpCCXGsznolmMVs/pubchart?oid=1631702142&format=image
[graph-elo8]:     https://docs.google.com/spreadsheets/d/e/2PACX-1vQqw86SXD_-zzP39DzfjBQ1eLBGyZMPyVLPuZDTY7zSNxBvxxj9CUXpd_AHRKy1aCpCCXGsznolmMVs/pubchart?oid=991230633&format=image
[graph-nelo1]:    https://docs.google.com/spreadsheets/d/e/2PACX-1vQqw86SXD_-zzP39DzfjBQ1eLBGyZMPyVLPuZDTY7zSNxBvxxj9CUXpd_AHRKy1aCpCCXGsznolmMVs/pubchart?oid=1045014049&format=image
[graph-nelo8]:    https://docs.google.com/spreadsheets/d/e/2PACX-1vQqw86SXD_-zzP39DzfjBQ1eLBGyZMPyVLPuZDTY7zSNxBvxxj9CUXpd_AHRKy1aCpCCXGsznolmMVs/pubchart?oid=1302996667&format=image
[graph-gpr1]:     https://docs.google.com/spreadsheets/d/e/2PACX-1vQqw86SXD_-zzP39DzfjBQ1eLBGyZMPyVLPuZDTY7zSNxBvxxj9CUXpd_AHRKy1aCpCCXGsznolmMVs/pubchart?oid=65689441&format=image
[graph-gpr8]:     https://docs.google.com/spreadsheets/d/e/2PACX-1vQqw86SXD_-zzP39DzfjBQ1eLBGyZMPyVLPuZDTY7zSNxBvxxj9CUXpd_AHRKy1aCpCCXGsznolmMVs/pubchart?oid=1638166821&format=image
[graph-dve1]:     https://docs.google.com/spreadsheets/d/e/2PACX-1vQqw86SXD_-zzP39DzfjBQ1eLBGyZMPyVLPuZDTY7zSNxBvxxj9CUXpd_AHRKy1aCpCCXGsznolmMVs/pubchart?oid=699890902&format=image
[graph-dve8]:     https://docs.google.com/spreadsheets/d/e/2PACX-1vQqw86SXD_-zzP39DzfjBQ1eLBGyZMPyVLPuZDTY7zSNxBvxxj9CUXpd_AHRKy1aCpCCXGsznolmMVs/pubchart?oid=2097713806&format=image
[graph-thirty1]:  https://docs.google.com/spreadsheets/d/e/2PACX-1vQqw86SXD_-zzP39DzfjBQ1eLBGyZMPyVLPuZDTY7zSNxBvxxj9CUXpd_AHRKy1aCpCCXGsznolmMVs/pubchart?oid=291372362&format=image
[graph-thirty8]:  https://docs.google.com/spreadsheets/d/e/2PACX-1vQqw86SXD_-zzP39DzfjBQ1eLBGyZMPyVLPuZDTY7zSNxBvxxj9CUXpd_AHRKy1aCpCCXGsznolmMVs/pubchart?oid=1969585471&format=image
[graph-total]:    https://docs.google.com/spreadsheets/d/e/2PACX-1vQqw86SXD_-zzP39DzfjBQ1eLBGyZMPyVLPuZDTY7zSNxBvxxj9CUXpd_AHRKy1aCpCCXGsznolmMVs/pubchart?oid=2059970959&format=image