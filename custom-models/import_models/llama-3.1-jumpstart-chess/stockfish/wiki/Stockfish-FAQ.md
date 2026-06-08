Table of Contents

- [Interpretation of the Stockfish evaluation](#interpretation-of-the-stockfish-evaluation)
- [Optimal settings](#optimal-settings)
  - [Threads](#threads)
  - [Hash](#hash)
  - [MultiPV](#multipv)
- [The Elo rating of Stockfish](#the-elo-rating-of-stockfish)
  - [Background information](#background-information)
  - [Caveats](#caveats)
  - [Conclusion](#conclusion)
- [Stockfish crashed](#stockfish-crashed)
- [Does Stockfish support chess variants?](#does-stockfish-support-chess-variants)
- [Can Stockfish use my GPU?](#can-stockfish-use-my-gpu)
- [Executing Stockfish opens a CMD window](#executing-stockfish-opens-a-cmd-window)
  - [User-friendly experience](#user-friendly-experience)
  - [Available commands](#available-commands)
- [What is depth?](#what-is-depth)
  - [Minimax](#minimax)
  - [Pruning](#pruning)
  - [Extensions](#extensions)
  - [Conclusion](#conclusion-1)

## Interpretation of the Stockfish evaluation

The evaluation of a position that results from search has traditionally been measured in `pawns` or `centipawns` (1 pawn = 100 centipawns). A value of 1, implied a 1 pawn advantage. However, with engines being so strong, and the NNUE evaluation being much less tied to material value, a new scheme was needed. The new normalized evaluation is now linked to the probability of winning, with a 1.0 pawn advantage being a 0.5 (that is 50%) win probability. An evaluation of 0.0 means equal chances for a win or a loss, but also nearly 100% chance of a draw.

Some GUIs will be able to show the win/draw/loss probabilities directly when the `UCI_ShowWDL` engine option is set to `True`.

The full plots of win, loss, and draw probability are given below. From these probabilities, one can also obtain the expected match score.

|                                                         Probabilities                                                        |                                                     Expected match score                                                     |
|:----------------------------------------------------------------------------------------------------------------------------:|:----------------------------------------------------------------------------------------------------------------------------:|
| <img src="https://user-images.githubusercontent.com/4202567/206894542-a5039063-09ff-4f4d-9bad-6e850588cac9.png" width="400"> | <img src="https://user-images.githubusercontent.com/4202567/206895934-f861a6a8-2e60-4592-a8f1-89d9aad8dac4.png" width="400"> |

The probability of winning or drawing a game, of course, depends on the opponent and the time control. With bullet games, the draw rate will be lower, and against a weak opponent, even a negative evaluation could result in a win. These graphs have been generated from a model derived from Fishtest data for Stockfish playing against Stockfish (so an equally strong opponent), at 60+0.6s per game. The curves are expected to evolve, i.e. as the engines get stronger, an evaluation of 0.0 will approach the 100% draw limit. These curves are for SF15.1 (Dec 2022).

## Optimal settings

To get the best possible evaluation or the strongest move for a given position, the key is to let Stockfish analyze long enough, using a recent release (or development version), properly selected for the CPU architecture.

The following settings are important as well:

### Threads

**Set it to the maximum - (1 or 2 threads).**

Set the number of threads to the maximum available, possibly leaving 1 or 2 threads free for other tasks. SMT or Hyper-threading is beneficial, so normally the number of threads available is twice the number of cores available. Consumer hardware typically has at least 4-8 threads, Stockfish supports hundreds of threads.

[More detailed results](Useful-data#threading-efficiency-and-elo-gain) on the efficiency of threading are available.

### Hash

**Set it to the maximum - (1 or 2 GiB RAM).**

Set the hash to nearly the maximum amount of memory (RAM) available, leaving some memory free for other tasks. The Hash can be any value, not just powers of two. The value is specified in MiB, and typical consumer hardware will have GiB of RAM. For a system with 8GiB of RAM, one could use 6000 as a reasonable value for the Hash.

[More detailed results](Useful-data#elo-cost-of-small-hash) on the cost of too little hash are available.

### MultiPV

**Set it to 1.**

A value higher than 1 weakens the quality of the best move computed, as resources are used to compute other moves.

[More detailed results](Useful-data#elo-cost-of-using-multipv) on the cost of MultiPV are available.

## The Elo rating of Stockfish

"What is the Elo of Stockfish?": A seemingly simple question, with no easy answer. First, the obvious: it is higher than any human Elo, and when SF 15.1 ranked with more than 4000 Elo on some rating lists, [YouTube knew](https://www.youtube.com/watch?v=wFALbm4gFoc). To answer the question in more detail, some background information is needed.

### Background information

In its simplest form, the [Elo rating system](https://en.wikipedia.org/wiki/Elo_rating_system) predicts the score of a match between two players, and conversely, a match between two players gives information about the Elo difference between them.

The Elo difference depends on the conditions of the match. For human players, time control (blitz vs. classical TC) or variant (standard chess vs. Fischer random chess) are well-known factors that influence the Elo difference between two players.

Finally, given an Elo difference between two players, one needs to know the Elo rating of one of them to know the Elo rating of the other. More generally, you need an anchor or reference within a group of opponents, and if that reference is different in different groups, the Elo value cannot be compared.

### Caveats

The same observations apply to the calculation of Stockfish's Elo rating, with the caveat that top engines play at an extremely high level and, from the starting position or any balanced opening, have achieved a draw rate approaching 100% against other engines of similar strength, especially at rapid or longer time controls, and even more so on powerful hardware. This results in small Elo differences between top engines, e.g. +19 -2 =79 is a convincing win, but a small Elo difference.

Carefully constructed books of starting positions with a clear advantage for one side can significantly reduce this draw rate and increase Elo differences. The book used in the match is therefore an important factor in the computed Elo difference.

Similarly, the pool of opponents and their rankings has a large impact on the Elo rating, and Elo ratings computed with different pools of opponents are difficult to compare, especially if weaker (but different) engines are part of that pool.

Finally, to accurately compute Elo differences at this level, a very large number of games (typically tens of thousands of games) are needed, as small samples of games (regardless of time control) will lead to large relative errors.

Having introduced all these caveats, accurately measuring Elo differences is central to the development of Stockfish, and our Fishtest framework constantly measures with great precision the Elo difference of Stockfish and its proposed improvements. These performance improvements are accurately tracked over time on the [regression testing](Regression-Tests) wiki page. The same page also links to [various external websites](Regression-Tests#external-links) that rank Stockfish against a wide range of other engines.

### Conclusion

Rating Stockfish on a human scale (e.g. FIDE Elo) has become an almost impossible task, as the difference in strength between it and humans is now so large that this difference can hardly be measured. This would require a human to play Stockfish long enough to have at least a handful of draws and wins.

## Stockfish crashed

Stockfish may crash if fed incorrect fens, or fens with illegal positions. Full validation code is complex to write, and within the UCI protocol, there is no established mechanism to communicate such an error back to the GUI. Therefore Stockfish is written with the expectation that the input fen is correct.

On the other hand, the GUI must carefully check fens. If you find a GUI through which you can crash Stockfish or any other engine, then by all means report it to that GUI's developers.

## Does Stockfish support chess variants?

The official Stockfish engine only supports standard chess and Chess960 or Fischer Random Chess (FRC). However, various forks based on Stockfish support variants, most notably the [Fairy-Stockfish project](https://github.com/ianfab/Fairy-Stockfish).

## Can Stockfish use my GPU?

No, Stockfish is a chess engine that uses the CPU only for chess evaluation. Its NNUE evaluation ([see this in-depth description](https://github.com/official-stockfish/nnue-pytorch/blob/master/docs/nnue.md)) is very effective on CPUs. With extremely short inference times (sub-micro-second), this network can not be efficiently evaluated on GPUs, in particular with the alpha-beta search that Stockfish employs. However, for training networks, Stockfish employs GPUs with effective code that is part of the [NNUE pytorch trainer](https://github.com/official-stockfish/nnue-pytorch). Other chess engines require GPUs for effective evaluation, as they are based on large convolutional or transformer networks, and use a search algorithm that allows for batching evaluations. See also the [Leela Chess Zero (Lc0) project](https://github.com/LeelaChessZero/lc0).

## Executing Stockfish opens a CMD window

<img src="https://github.com/official-stockfish/Stockfish/assets/63931154/505b3c0c-916e-49e9-ba86-0bdcca9ba856" width="300">

Stockfish is a command line program, when you execute it, you might notice that it simply opens a Command Prompt (CMD) window. **This behavior is intentional** and serves as the interface for interacting with the engine.

### User-friendly experience

If you prefer a **more user-friendly experience** with a **chessboard and additional features**, you can consider using a graphical user interface (GUI) alongside Stockfish. To set up a GUI, you can visit the [Download and Usage](Download-and-usage#download-a-chess-gui) page.

### Available commands

The CMD window allows you to input various commands and receive corresponding outputs from Stockfish. If you want to explore the available commands and their explanations, you can refer to the [Commands](UCI-&-Commands) page but this is **only recommended for advanced users and developers**.

## What is depth?

First, we need to understand how minimax search works. We will go with the vanilla one because explaining what Alpha-beta is does not do much.

### Minimax

**Each player tries to maximize the score in their favor**. White wants the evaluation to be as positive as it can, and Black as negative as it can - we do this all the time when we play chess. Search works in a similar way - you explore your moves, explore the opponent's replies, assign a value called evaluation to each resulting board position (which is not precise but tries to be), and find a sequence where White plays some move that has the maximum evaluation for the best opponent's reply.

Then you search one ply (half-move) deeper - exploring your reply to the last opponent's replies. This process is called iterative deepening - you explore a position up to depth 1, then to depth 2, then to depth 3, and so on - you deepen your search with each iteration and this is why it is called this way.

So, for now, "depth" is a perfect thing - it means you fully calculated the search tree up to this "depth" and you know everything that can happen within it. For a mate in 5, you will need depth 9 to see it (because depth is written in half-moves). But chess has a lot of possible moves, 20 from the starting position and usually many more from any middlegame position. Even if you can evaluate millions of positions per second as engines like Stockfish do, you will still hit a wall in what depths you can realistically reach, and it would not be that high - depth 8, maybe 10.

### Pruning

How to combat this? With a thing called pruning. Pruning splits into quite a lot of different heuristics, but they mostly serve one purpose - **remove branches in search that do not look too desirable**, to re-explore them later when iterative deepening depth goes higher. So this is where "depth" starts to mean less - because you do not search the entire game tree and modern engines prune large percentages of branches.

### Extensions

But then there is also a thing called "**extensions**" which is more or less the opposite of pruning. With extensions, you start by **searching "important" branches deeper** (for example, checks) than what is needed to complete the iterative deepening iteration.

### Conclusion

With all of this, instead of a search tree that is strictly cut off at this "depth", you have **most of the branches ending really early and a lot of branches searched deeper** than the given "depth". Stockfish is the most aggressive engine in both pruning and extensions, so its search tree looks nothing like what you usually see on [Wikipedia](https://en.wikipedia.org/wiki/Minimax).

Coming back to how much Stockfish prunes, there is some data [here](Useful-data#branching-factor-of-stockfish). The branching factor indicates how many moves you calculate on average per depth increase, calculated as $nodes^{\frac{1}{depth}}$. Stockfish 15.1 with higher depths goes all the way down to 1.5, so at depth 50 considers approximately 1.5 moves per ply from the full 20-30-40 moves we usually have. And this is why it [misses some short mates up to high depths](https://www.reddit.com/r/chess/comments/1028i0e/stockfishs_search_tree_trying_to_find_a_mate_in_2/) while vanilla minimax would have found them at lower ones. It just throws away 90%+ of the moves.
