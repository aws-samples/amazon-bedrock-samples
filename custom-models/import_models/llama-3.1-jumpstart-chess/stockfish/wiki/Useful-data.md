
## Depth vs. TC

Newer and older results showing the average depth for games at fishtest conditions

|                                                              New                                                             |                                                             Old                                                             |
|:----------------------------------------------------------------------------------------------------------------------------:|:---------------------------------------------------------------------------------------------------------------------------:|
| <img src="https://user-images.githubusercontent.com/4202567/168158280-898935eb-8213-4ef5-9474-3cc590af23bf.png" width="400"> | <img src="https://user-images.githubusercontent.com/4202567/47263897-1d6f7380-d50b-11e8-871a-ff21d83e3f6c.png" width="400"> |



---

## Elo cost of small Hash

We measure the influence of Hash on the playing strength, using games of SF15.1 at LTC (60+0.6s) and VLTC (240+2.4s) on the UHO book.
Hash is varied between 1 and 64 MB and 256MB in powers of two, leading to as average hashfull between 100 and 950 per thousand.
The data suggests that keeping hashfull below 30% is best to maintain strength.

<img src="https://user-images.githubusercontent.com/4202567/207459494-5fe1c0c0-b06d-420b-8415-0ea8bfb1bac0.png" width="800">


<details>
  <summary><code>Raw data for the above graph</code></summary><br>

| Hash | Hashfull |    Elo | Elo-err |
|-----:|:--------:|-------:|:-------:|
|   64 |    109   |   0.00 |   0.00  |
|   32 |    199   |  -3.80 |  13.00  |
|   16 |    336   |   0.70 |  12.80  |
|    8 |    513   | -10.70 |  11.00  |
|    4 |    689   | -21.50 |  13.30  |
|    2 |    825   | -29.50 |  13.10  |
|    1 |    902   | -47.80 |   8.80  |

| Hash | Hashfull |    Elo | Elo-err |
|-----:|:--------:|-------:|:-------:|
|  256 |    131   |   0.00 |   0.00  |
|  128 |    239   |  -1.00 |   7.50  |
|   64 |    397   |  -0.80 |   6.60  |
|   32 |    591   | -12.10 |   6.10  |
|   16 |    766   | -21.40 |   7.30  |
|    8 |    865   | -32.30 |   4.20  |
|    4 |    931   | -52.40 |   6.20  |
|    2 |    943   | -67.40 |   5.70  |
|    1 |    947   | -95.20 |   6.60  |

</details>

---

## Elo cost of using MultiPV

MultiPV provides the N best moves, and their associated principal variation. This is a great tool to understand the options available in a given position. However, this information does not come for free, and the computational cost computing it reducing the quality of the bestmove found relative to a search that only needs to find a single line.

| MultiPV |    Elo | Elo-err |
|--------:|-------:|:-------:|
|       1 | 0.0    |   0.0   |
|       2 | -97.2  |   2.1   |
|       3 | -156.7 |   2.8   |
|       4 | -199.3 |   2.9   |
|       5 | -234.5 |   2.8   |

Engine: Stockfish 15.1  
Time control: 60s+0.6s  
Book: UHO

---

## Elo gain using MultiPV at fixed depth

| MultiPV |  Elo | Elo-err |  Points | Played |
|--------:|-----:|:-------:|--------:|-------:|
|       1 | 0.0  |         | 13496.5 |  30614 |
|       2 | 45.7 |   3.1   | 15388.0 |  30697 |
|       3 | 53.9 |   3.5   | 15732.5 |  30722 |
|       4 | 59.5 |   3.2   | 15862.5 |  30479 |
|       5 | 63.7 |   3.6   | 16078.5 |  30604 |

Time control: 580s+5.8s  
Depth: 18

---

## Elo gain using syzygy

### TB6 testing for various versions of SF

Consistent measurement of Elo gain (syzygy 6men vs none) for various SF versions:

<img src="https://user-images.githubusercontent.com/4202567/204077584-aa99d324-4a35-4a88-92fb-567ec00b6551.png" width="800">

TB are in RAM (so fast access), TC is 10+0.1s (STC), book UHO_XXL_+0.90_+1.19.epd. No adjudication. The introduction of NNUE (with SF12) is clearly visible. With SF15, there is just 2.7 Elo gain.

<details>
  <summary><code>Raw data for the above graph</code></summary><br>

| SF |  Elo | Elo-err |
|---:|-----:|--------:|
|  6 | 14.5 |     1.4 |
|  7 | 15.6 |     1.3 |
|  8 | 15.8 |     1.3 |
|  9 | 16.5 |     1.5 |
| 10 | 16.2 |     1.5 |
| 11 | 15.8 |     1.5 |
| 12 |  7.2 |     1.4 |
| 13 | 11.1 |     1.4 |
| 14 |  7.3 |     1.4 |
| 15 |  2.7 |     1.4 |

</details>

### Testing depending on number of pieces and TC

Tested at 10+0.1, with all syzygy WDL files on tmpfs (i.e. RAM), testing using none(0), 4, 5, and 6 man TB in a round-robin tournament (SF10dev).

| Rank | Name    | Elo | +/- | Games | Score | Draws |
|-----:|---------|----:|:---:|:-----:|:-----:|:-----:|
|    1 | syzygy6 |  13 |  2  | 82591 | 51.8% | 59.5% |
|    2 | syzygy5 |   2 |  2  | 82590 | 50.3% | 59.4% |
|    3 | syzygy4 |  -7 |  2  | 82591 | 49.0% | 59.3% |
|    4 | syzygy0 |  -7 |  2  | 82592 | 48.9% | 59.4% |

Tested at 60+0.6, with all syzygy WDL files on tmpfs (i.e. RAM), testing using none(0) against 6 man TB:

Score of syzygy6 vs syzygy0: 4084 - 3298 - 18510  [0.515] 25892
Elo difference: 10.55 +/- 2.25

---

## Threading efficiency and Elo gain.

### Efficiency

Here we look at the threading efficiency of the lazySMP parallelization scheme. To focus on the algorithm we play games with a given budget of nodes rather than at a given TC. In principle, lazySMP has excellent scaling of the nps with cores, but practical measurement is influenced by e.g. frequency adjustments, SMT/hyperthreading, and sometimes hardware limitation.

#### Equivalent nodestime

In these tests, matches are played at a fixed nodes budget (using the nodestime feature of SF), and equivalence in strength between the serial player and the threaded player (for x threads in the graph below) is found by adjusting the number of nodes given to the threaded player (e.g. with 16 threads, the threaded player might need 200% of the nodes of the serial player to match the strength of the serial player). This 'equivalent nodestime' is determined for various number of threads and various nodes budgets (60+0.6Mnodes/game is somewhat similar to our usual LTC at 60+0.6s/game, if we assume 1Mnps).

<img src="https://user-images.githubusercontent.com/4202567/202908179-38d2440e-8344-4a3f-ab61-93b68ed7df7a.png" width="800">

The interesting observation one can make immediately is that this 'equivalent nodestime' grows with the number of threads, but not too steeply, and further more that the 'equivalent nodestime' decreases with increasing nodes budget. The data shows that with 64 threads, the equivalent nodestime is about 200% for a node budget of 240+2.4Mn, i.e. despite such games being much faster than STC (10+0.1s), efficiency is still around 50%.

The curves are sufficiently smooth to be fitted with a model having 1 parameter that is different between the curves (`f(x)`, parameter `a`, see caption). A smaller value of `a` means a higher efficiency.

#### A fit for the `a` parameter, and extrapolation to long TCs.

The above parameter `a` from the model, can be fit as a function of nodes budget, this allows for extrapolating the parameter, and to arrive at and estimate for the 'equivalent nodestime' at large TC / nodes budgets:

<img src="https://user-images.githubusercontent.com/4202567/202909097-701cb0cc-b162-4c11-81c5-5f222086a908.png" width="800">

The fit is again fairly good. Taking a leap of faith, these measurements at up to 240+2.4Mn can be extrapolated to node budgets typical of TCEC or CCC (up to 500Gn). This allows us to predict speedup and/or efficiency.

|                                                            Speedup                                                           |                                                          Efficiency                                                          |
|:----------------------------------------------------------------------------------------------------------------------------:|:----------------------------------------------------------------------------------------------------------------------------:|
| <img src="https://user-images.githubusercontent.com/4202567/202909354-b5684563-ee5e-4d22-8f7f-c664271bc05e.png" width="400"> | <img src="https://user-images.githubusercontent.com/4202567/202909324-0d9739a7-d24e-4985-acad-ddde5c23c319.png" width="400"> |

These extrapolations suggest that even at thread counts of >300, at TCEC TCs efficiency could be 80% or higher, provided the nps scales with the number of threads.

### Elo results (older)

### LTC
Playing 8 threads vs 1 thread at LTC (60+0.6, 8moves_v3.pgn):

```
Score of t8 vs seq: 476 - 3 - 521  [0.737] 1000
Elo difference: 178.6 +/- 14.0, LOS: 100.0 %, DrawRatio: 52.1 %
```

Playing 1 thread at 8xLTC (480+4.8) vs (60+0.6) (8moves_v3.pgn):

```
Score of seq8 vs seq: 561 - 5 - 434  [0.778] 1000
Elo difference: 217.9 +/- 15.8, LOS: 100.0 %, DrawRatio: 43.4 %
```

Which is roughly 82% efficiency (178/218).

#### STC
Playing 8 threads vs 1 thread at STC (10+0.1):

```
Score of threads vs serial: 1606 - 15 - 540  [0.868] 2161
Elo difference: 327.36 +/- 14.59
```

Playing 8 threads @ 10+0.1 vs 1 thread @ 80+0.8:

```
Score of threads vs time: 348 - 995 - 2104  [0.406] 3447
Elo difference: -66.00 +/- 7.15
```

So, 1 -> 8 threads has about 83% scaling efficiency (327 / (327 + 66)) using this test.

---

## Elo from speedups

<img src="https://user-images.githubusercontent.com/4202567/77511220-ea07e580-6e70-11ea-9c25-1c3bfeca7b31.png" width="800">

For small speedups (<~5%) the linear estimate can be used that gives Elo gain as a function of speedup percentage (x) as:

```
Elo_stc(x) = 2.10 x
Elo_ltc(x) = 1.43 x
```

To have 50% passing chance at STC<-0.5,1.5>, we need a 0.24% speedup, while at LTC<0.25,1.75> we need 0.70% speedup. A 1% speedup has nearly 85% passing chance at LTC.

Raw data:
```
tc 10+0.1:
16   32.42  3.06
 8   13.67  3.05
 4    8.99  3.04
 2    3.52  3.05

tc 60+0.6:
16   20.85  2.59
 8   12.20  2.57
 4    4.67  2.57
```

_Note: Numbers will depend on the precise hardware. The model was verified quite accurately on fishtest see https://github.com/locutus2/Stockfish-old/commit/82958c97214b6d418e5bc95e3bf1961060cd6113#commitcomment-38646654_

---

## Distribution of lengths of games at LTC (60+0.6) on fishtest

In a collection of a few million games, the longest was [902 plies](https://github.com/protonspring/Stockfish/files/4532568/long.pgn.txt).

<img src="https://user-images.githubusercontent.com/4202567/217919261-d3575d01-4aba-449f-9cf1-b5148afc7da2.png" width="800">

---

## Win-Draw-Loss statistics of LTC games on fishtest

The following graph gives information on the Win-Draw-Loss (WDL) statistics, relating them to score and material count. It answers the question 'What fraction of positions that have a given score (and material count) in fishtest LTC, have a Win or a Draw or a Loss ?'.

[<img src="https://raw.githubusercontent.com/official-stockfish/WDL_model/master/WDL_model_summary.png" width="800">](https://raw.githubusercontent.com/official-stockfish/WDL_model/master/WDL_model_summary.png)

This model is used when Stockfish provides WDL statistics during analysis with the `UCI_ShowWDL` option set to True, as well as for the normalization of Stockfish's evaluation that ensures that a score of "100 centipawns" means the engine has a 50% probability to win from this position in selfplay at fishtest LTC time control. For details see the [WDL model repo](https://github.com/official-stockfish/WDL_model).

---
## Equivalent time odds and normalized game pair Elo

<img src="https://github.com/user-attachments/assets/2aca2bb1-26e5-40a4-99fa-eca19a1233e9" width="800">

A suitable measure to define the Elo difference between two engines is `normalized game pair Elo` as defined from the pentanomial statistics by:

```python
def normalized_game_pair_elo(row):
    return -100 * np.log10((2 * row['pntl0'] + row['pntl1']) / (2 * row['pntl4'] + row['pntl3']))
```

It is nearly book independent, and thus a good measure of relative strength of two engines at a given TC. To express more clearly what a given strength difference implies. We use 'equivalent time odds', i.e. the TC factor needed to have equivalent strength, i.e. zero Elo difference in a match between two engines (which is independent of the definition of Elo used).

We see that at STC the equivalent time odds is about 6x for SF14 vs SF17, while at LTC this time odds factor has become 16x.


<details>
  <summary><code>Raw data for the above graph</code></summary><br>

```
=======================================  UHO_Lichess_4852_v1 =======================================
   engine1        tc1    engine2        tc2        elo  pntl0  pntl1  pntl2  pntl3  pntl4    ngp_Elo
      sf17     10+0.1       sf14   10.0+0.1     165.29     10    432   6509  25598   3291     185.24
      sf17     10+0.1       sf14   40.0+0.4      41.74    251   5110  16632  13516    331      40.25
      sf17     10+0.1       sf14   60.0+0.6       7.47    395   7724  17826   9736    159       7.22
      sf17     10+0.1       sf14   80.0+0.8     -17.52    569  10075  17691   7408     97     -16.88
=======================================          noob_3moves =======================================
   engine1        tc1    engine2        tc2        elo  pntl0  pntl1  pntl2  pntl3  pntl4    ngp_Elo
      sf17     10+0.1       sf14   10.0+0.1     108.47      6    610  16073  16012   3139     155.43
      sf17     10+0.1       sf14   40.0+0.4      10.85    100   3004  27471   5089    176      23.00
      sf17     10+0.1       sf14   60.0+0.6      -4.87    165   4048  28312   3257     58     -11.33
      sf17     10+0.1       sf14   80.0+0.8     -15.02    219   4892  28520   2184     25     -37.76
=======================================  UHO_Lichess_4852_v1 =======================================
   engine1        tc1    engine2        tc2        elo  pntl0  pntl1  pntl2  pntl3  pntl4    ngp_Elo
      sf17     60+0.6       sf14   60.0+0.6     163.96      1    194   5269  29060   1316     220.87
      sf17     60+0.6       sf14  240.0+2.4      88.09     25   2021  14134  19482    178      98.13
      sf17     60+0.6       sf14  360.0+3.6      63.06     41   3212  16546  15938    103      69.03
      sf17     60+0.6       sf14  480.0+4.8      46.39     72   4243  17703  13760     62      50.03
=======================================          noob_3moves =======================================
   engine1        tc1    engine2        tc2        elo  pntl0  pntl1  pntl2  pntl3  pntl4    ngp_Elo
      sf17     60+0.6       sf14   60.0+0.6      71.55      0    131  22234  12279   1196     204.92
      sf17     60+0.6       sf14  240.0+2.4      19.23      0    436  31090   4231     83     100.37
      sf17     60+0.6       sf14  360.0+3.6      11.51      3    616  32255   2938     28      68.25
      sf17     60+0.6       sf14  480.0+4.8       7.08      6    716  32949   2149     20      47.81
```

</details>

---

## Elo gain with time odds

See also: https://github.com/official-stockfish/Stockfish/discussions/3402

|                                                              New                                                              |                                                              Old                                                             |
|:-----------------------------------------------------------------------------------------------------------------------------:|:----------------------------------------------------------------------------------------------------------------------------:|
| <img src="https://user-images.githubusercontent.com/98367568/178650687-10cf2d3b-9e5d-4385-b622-b33aaf8a163d.png" width="400"> | <img src="https://user-images.githubusercontent.com/4202567/111422950-d5f76c80-86ef-11eb-8aed-29b4a0e842b2.png" width="400"> |

---

## One year of NNUE speed improvements

Presents nodes per second (nps) measurements for all SF version between the first NNUE commit (SF_NNUE, Aug 2th 2020) and end of July 2021 on a AMD Ryzen 9 3950X compiled with `make -j ARCH=x86-64-avx2 profile-build`. The last nps reported for a depth 22 search from startpos using NNUE (best over about 20 measurements) is shown in the graph. For reference, the last classical evaluation (SF_classical, July 30 2020) has 2.30 Mnps.

<img src="https://user-images.githubusercontent.com/4202567/126898745-599895e6-08b3-4a3f-8e73-bb5e354ede19.png" width="800">

---

## The impact of efficient (incremental) updates (NNUE)

As measured with SF17dev (dev-20230824-4c4cb185), disabling the update_accumulator_incremental() functionality.

Speedup:
```
Result of  10 runs
==================
base (./stockfish.master       ) =    1287575  +/- 8703
test (./stockfish.patch        ) =     696064  +/- 3451
diff                             =    -591511  +/- 7318

speedup        = -0.4594
P(speedup > 0) =  0.0000

CPU: 16 x AMD Ryzen 9 3950X 16-Core Processor
```

Which corresponds to [-67.55 ± 9.5 Elo on fishtest](https://tests.stockfishchess.org/tests/view/64e8f64085e3e95030fd80bf) with the UHO book at LTC.

---
## Round-robin tournament with SF releases, impact of book and time odds

Measured playing games of 5+0.05s, with SF 7 - 15, using the three different books. Each version plays once with the base TC, and once with 20% time odds.

<img src="https://user-images.githubusercontent.com/4202567/192138711-5f93a117-795a-4479-b7ad-a6da718537f2.png" width="800">

<details>
  <summary><code>Raw data for the above graph</code></summary><br>


### UHO

|   SF |   Elo | 20%-odds | Elo-err | Odds-err |
|-----:|------:|---------:|--------:|---------:|
|  SF7 |   0.0 |     38.1 |     0.0 |      4.1 |
|  SF8 |  95.8 |     40.3 |     4.2 |      5.9 |
|  SF9 | 142.3 |     38.8 |     3.9 |      5.5 |
| SF10 | 199.5 |     38.2 |     4.0 |      5.7 |
| SF11 | 231.2 |     40.5 |     4.3 |      5.7 |
| SF12 | 405.6 |     37.5 |     4.0 |      5.9 |
| SF13 | 476.5 |     28.4 |     4.2 |      6.0 |
| SF14 | 553.4 |     27.8 |     4.5 |      6.3 |
| SF15 | 627.6 |     24.5 |     4.6 |      6.7 |

### noob

|   SF |   Elo | 20%-odds | Elo-err | Odds-err |
|-----:|------:|---------:|--------:|---------:|
|  SF7 |   0.0 |     37.8 |     0.0 |      3.8 |
|  SF8 |  97.2 |     39.8 |     4.3 |      5.9 |
|  SF9 | 146.8 |     40.5 |     3.9 |      5.9 |
| SF10 | 211.1 |     39.3 |     4.3 |      6.2 |
| SF11 | 241.8 |     43.0 |     4.4 |      6.0 |
| SF12 | 458.4 |     32.1 |     4.3 |      6.2 |
| SF13 | 536.2 |     31.9 |     4.2 |      6.3 |
| SF14 | 611.3 |     29.1 |     4.5 |      6.5 |
| SF15 | 660.9 |     24.8 |     4.3 |      6.2 |

### 8moves

|   SF |   Elo | 20%-odds | Elo-err | Odds-err |
|-----:|------:|---------:|--------:|---------:|
|  SF7 |   0.0 |     33.0 |     0.0 |      4.2 |
|  SF8 |  86.7 |     32.2 |     4.2 |      5.8 |
|  SF9 | 126.7 |     37.3 |     4.0 |      5.6 |
| SF10 | 182.3 |     33.7 |     4.3 |      5.6 |
| SF11 | 206.5 |     42.6 |     4.0 |      5.4 |
| SF12 | 380.7 |     31.6 |     4.1 |      5.6 |
| SF13 | 445.8 |     25.0 |     4.0 |      5.7 |
| SF14 | 512.4 |     23.8 |     4.1 |      5.9 |
| SF15 | 554.5 |     26.4 |     4.1 |      5.9 |

</details>

---

## Branching factor of Stockfish

The branching factor (bf) of Stockfish is defined here such that `nodes = bf ** rootDepth` or equivalently `bf = exp(log(nodes)/rootDepth)`. Here, this has been measured with a single search from the starting position.

<img src="https://user-images.githubusercontent.com/4202567/209304926-ce6d0f9a-62be-4e3e-aa78-a93e4900027c.png" width="800">

The trend is the deeper one searches the lower the branching factor, and newer versions of SF have a lower branching factor. A small difference in branching factor leads to very large differences in number of nodes searched. For example, SF10 needs about 143x more nodes than SF15.1 to reach depth 49.

---

## Contempt measurements

Older SF (around SF10) had contempt that worked rather well. This data shows the dependence of Elo difference between SFdev of October 2018 and older versions of Stockfish depending on contempt value (The SFdev used is approx. 40Elo above SF9).
Upper and lower bounds represent value with maximum error.

| Opponent |                           STC                           |                           LTC                           |
|:--------:|:-------------------------------------------------------:|:-------------------------------------------------------:|
|     7    | <img src="https://i.imgur.com/hnckGJO.png" width="400"> | <img src="https://i.imgur.com/0zRWEEF.png" width="400"> |
|     8    | <img src="https://i.imgur.com/O7krCsC.png" width="400"> | <img src="https://i.imgur.com/IjAUWDc.png" width="400"> |
|     9    | <img src="https://i.imgur.com/B1w9N05.png" width="400"> | <img src="https://i.imgur.com/pdYUcP0.png" width="400"> |

Full data with values https://docs.google.com/spreadsheets/d/1R_eopD8_ujlBbt_Q0ygZMvuMsP1sc4UyO3Md4qL1z5M/edit#gid=1878521689

---

## Elo change with respect to TC

Here is the result of some scaling tests with the 2moves book. 40000 games each (STC=10+0.1, LTC=60+0.6)

|         |  SF7 -> SF8  |  SF8 -> SF9 | SF9 -> SF10 |
|:-------:|:------------:|:-----------:|:-----------:|
| Elo STC |  95.91 +-2.3 | 58.28 +-2.3 | 71.03 +-2.4 |
| Elo LTC | 100.40 +-2.1 | 68.55 +-2.1 | 65.55 +-2.2 |

So we see that the common wisdom that increased TC causes elo compression is not always true.

See https://github.com/official-stockfish/Stockfish/issues/1859#issuecomment-449624976

---

## TC dependence of certain terms in search

Discussed here https://github.com/official-stockfish/Stockfish/pull/2401#issuecomment-552768526

<img src="https://user-images.githubusercontent.com/4202567/68650355-17d53900-0525-11ea-9d5d-b2482e7e73cf.png" width="800">

---

## Elo contributions from various evaluation terms

See spreadsheet at: https://github.com/official-stockfish/Stockfish/files/3828738/Stockfish.Feature.s.Estimated.Elo.worth.1.xlsx

_Note: The estimated elo worth for various features might be outdated, or might get outdated soon._
