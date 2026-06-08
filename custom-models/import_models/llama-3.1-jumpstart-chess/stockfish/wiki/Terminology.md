## General terms

### Threads

Also known as "cores", "CPUs" or "vCPUs".
The amount of CPU threads that the engine will use, usually the higher the better.
Note that a modern CPU will have multiple cores, that typically can run two threads each.

### Hash

Also known as "memory".
The amount of Hash is the amount of RAM that the engine will use to store positions in the game tree.
This information can be reused during the analysis, for example after a transposition, 
which means usually [the higher the Hash the better](Useful-data#elo-cost-of-small-hash). See also [Transposition Table](#transposition-table).

### Depth

Counter of [iterative deepening](#iterative-deepening) loop at the root of the game tree, thus also known as rootDepth. Regardless of the name, there is no simple connection to the actual depth searched in the game tree. The deepest lines searched are usually quite a bit deeper than the rootDepth. See also [a discussion on rootDepth vs depth](https://github.com/official-stockfish/Stockfish/discussions/3888).

### Selective Depth

Also known as "seldepth".
Is the depth of the deepest principal variation line in the search.

### Multiple PVs

Also known as "number of lines" or "multiple lines".
The top N moves and their [principal variations](#principal-variation) can be computed. This gives additional insight in the options of the position. However, in Stockfish, this weakens the quality of the best move computed, as resources are used to compute other moves.

### Transposition Table

Also known as "TT".
A database / hash table that stores results of previously performed searches. See also [Hash](#hash).

### Lazy Symmetric Multiprocessing

Also known as "Lazy SMP".
The idea of executing the search function on N many threads and share the Transposition table. This allows for faster filling of the transposition table, resulting in a faster and wider search.
This approach to parallelism is [known to scale well](Useful-data#threading-efficiency-and-elo-gain), especially with longer searches.

### Iterative deepening

The idea of performing consecutive searches at higher depths each time.

### Null Move

Also known as "passing move". TODO

### Time Control

Also known as "TC". How the time limits are set for playing a game. For chess engine testing, Stockfish uses 10+0.1s (10 seconds for the game, 0.1 seconds for every move), and 60+0.6s. These TCs are known as STC (short TC) and LTC (long TC).

## Principal Variation Search

### Principal Variation

Also known as "PV".
The sequence of moves that the engine considers best and therefore expects to be played.

### Pruning

The idea of ignoring certain parts of the search tree in order to reduce the amount of time it takes to execute a search.

### Null Move Pruning

Based on the assumption that, if we can reach beta by not making a move at lower depths, we will most likely be able to reach it anyway.

### Futility Pruning

The idea that quiet moves don't tend to improve positions significantly, therefore we can safely prune quiet moves in positions where the current position is evaluated to be below alpha by a margin.

### Late Move Pruning

Also known as "LMP".
The idea that all quiet moves can be pruned after searching the first few given by the move ordering algorithm.

### Late Move Reductions

Also known as "LMR".
A way of proving if a move is lower than alpha quickly. This is done by searching moves that are expected to underperform at a lower depth.

## Extensions

The idea of extending certain moves, usually by one ply, to try to find better moves faster.

### Check Extensions

They can have two distinct forms: one of them extends when giving check, the other when evading it. The reason behind check extension is that we are in a forcing sequence, so that it is desirable to know its outcome with more certainty.

### Move Ordering

In order to maximize the efficiency of alpha-beta search, we optimally want to try the best moves first.

### Quiescence Search

Also known as "qSearch".
Performed at the end of the main search, the purpose of this search is to only evaluate "quiet" positions, or positions where there are no winning tactical moves to be made.

## Evaluation

### Handcrafted Evaluation

Also known as "classic", "classical" or "HCE". 

This is the older evaluation method that is generally not used today. It uses various heuristics and rules (e.g. material, pawn structure, king safety, mobility, etc.) to assign the evaluation. Although it is slightly faster than NNUE evaluation, it is much less accurate, and is not used most of the time.

### Efficiently Updatable Neural Network

Also known as "NNUE". The first NNUE implementation was added in Stockfish 12, and evaluates positions using a neural network, which is trained on a large set of training data. NNUE is typically much more accurate than classical evaluation, gaining hundreds of Elo.
