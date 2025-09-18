/*
  Stockfish, a UCI chess playing engine derived from Glaurung 2.1
  Copyright (C) 2004-2024 The Stockfish developers (see AUTHORS file)

  Stockfish is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  Stockfish is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

#include "bitboard.h"

#include <algorithm>
#include <bitset>
#include <initializer_list>

#include "misc.h"

namespace Stockfish {

uint8_t PopCnt16[1 << 16];
uint8_t SquareDistance[SQUARE_NB][SQUARE_NB];

Bitboard LineBB[SQUARE_NB][SQUARE_NB];
Bitboard BetweenBB[SQUARE_NB][SQUARE_NB];
Bitboard PseudoAttacks[PIECE_TYPE_NB][SQUARE_NB];
Bitboard PawnAttacks[COLOR_NB][SQUARE_NB];

Magic RookMagics[SQUARE_NB];
Magic BishopMagics[SQUARE_NB];

namespace {

Bitboard RookTable[0x19000];   // To store rook attacks
Bitboard BishopTable[0x1480];  // To store bishop attacks

void init_magics(PieceType pt, Bitboard table[], Magic magics[]);

// Returns the bitboard of target square for the given step
// from the given square. If the step is off the board, returns empty bitboard.
Bitboard safe_destination(Square s, int step) {
    Square to = Square(s + step);
    return is_ok(to) && distance(s, to) <= 2 ? square_bb(to) : Bitboard(0);
}
}

// Returns an ASCII representation of a bitboard suitable
// to be printed to standard output. Useful for debugging.
std::string Bitboards::pretty(Bitboard b) {

    std::string s = "+---+---+---+---+---+---+---+---+\n";

    for (Rank r = RANK_8; r >= RANK_1; --r)
    {
        for (File f = FILE_A; f <= FILE_H; ++f)
            s += b & make_square(f, r) ? "| X " : "|   ";

        s += "| " + std::to_string(1 + r) + "\n+---+---+---+---+---+---+---+---+\n";
    }
    s += "  a   b   c   d   e   f   g   h\n";

    return s;
}


// Initializes various bitboard tables. It is called at
// startup and relies on global objects to be already zero-initialized.
void Bitboards::init() {

    for (unsigned i = 0; i < (1 << 16); ++i)
        PopCnt16[i] = uint8_t(std::bitset<16>(i).count());

    for (Square s1 = SQ_A1; s1 <= SQ_H8; ++s1)
        for (Square s2 = SQ_A1; s2 <= SQ_H8; ++s2)
            SquareDistance[s1][s2] = std::max(distance<File>(s1, s2), distance<Rank>(s1, s2));

    init_magics(ROOK, RookTable, RookMagics);
    init_magics(BISHOP, BishopTable, BishopMagics);

    for (Square s1 = SQ_A1; s1 <= SQ_H8; ++s1)
    {
        PawnAttacks[WHITE][s1] = pawn_attacks_bb<WHITE>(square_bb(s1));
        PawnAttacks[BLACK][s1] = pawn_attacks_bb<BLACK>(square_bb(s1));

        for (int step : {-9, -8, -7, -1, 1, 7, 8, 9})
            PseudoAttacks[KING][s1] |= safe_destination(s1, step);

        for (int step : {-17, -15, -10, -6, 6, 10, 15, 17})
            PseudoAttacks[KNIGHT][s1] |= safe_destination(s1, step);

        PseudoAttacks[QUEEN][s1] = PseudoAttacks[BISHOP][s1] = attacks_bb<BISHOP>(s1, 0);
        PseudoAttacks[QUEEN][s1] |= PseudoAttacks[ROOK][s1]  = attacks_bb<ROOK>(s1, 0);

        for (PieceType pt : {BISHOP, ROOK})
            for (Square s2 = SQ_A1; s2 <= SQ_H8; ++s2)
            {
                if (PseudoAttacks[pt][s1] & s2)
                {
                    LineBB[s1][s2] = (attacks_bb(pt, s1, 0) & attacks_bb(pt, s2, 0)) | s1 | s2;
                    BetweenBB[s1][s2] =
                      (attacks_bb(pt, s1, square_bb(s2)) & attacks_bb(pt, s2, square_bb(s1)));
                }
                BetweenBB[s1][s2] |= s2;
            }
    }
}

namespace {

Bitboard sliding_attack(PieceType pt, Square sq, Bitboard occupied) {

    Bitboard  attacks             = 0;
    Direction RookDirections[4]   = {NORTH, SOUTH, EAST, WEST};
    Direction BishopDirections[4] = {NORTH_EAST, SOUTH_EAST, SOUTH_WEST, NORTH_WEST};

    for (Direction d : (pt == ROOK ? RookDirections : BishopDirections))
    {
        Square s = sq;
        while (safe_destination(s, d))
        {
            attacks |= (s += d);
            if (occupied & s)
            {
                break;
            }
        }
    }

    return attacks;
}


// Computes all rook and bishop attacks at startup. Magic
// bitboards are used to look up attacks of sliding pieces. As a reference see
// www.chessprogramming.org/Magic_Bitboards. In particular, here we use the so
// called "fancy" approach.
void init_magics(PieceType pt, Bitboard table[], Magic magics[]) {

    // Optimal PRNG seeds to pick the correct magics in the shortest time
    int seeds[][RANK_NB] = {{8977, 44560, 54343, 38998, 5731, 95205, 104912, 17020},
                            {728, 10316, 55013, 32803, 12281, 15100, 16645, 255}};

    Bitboard occupancy[4096], reference[4096], edges, b;
    int      epoch[4096] = {}, cnt = 0, size = 0;

    for (Square s = SQ_A1; s <= SQ_H8; ++s)
    {
        // Board edges are not considered in the relevant occupancies
        edges = ((Rank1BB | Rank8BB) & ~rank_bb(s)) | ((FileABB | FileHBB) & ~file_bb(s));

        // Given a square 's', the mask is the bitboard of sliding attacks from
        // 's' computed on an empty board. The index must be big enough to contain
        // all the attacks for each possible subset of the mask and so is 2 power
        // the number of 1s of the mask. Hence we deduce the size of the shift to
        // apply to the 64 or 32 bits word to get the index.
        Magic& m = magics[s];
        m.mask   = sliding_attack(pt, s, 0) & ~edges;
        m.shift  = (Is64Bit ? 64 : 32) - popcount(m.mask);

        // Set the offset for the attacks table of the square. We have individual
        // table sizes for each square with "Fancy Magic Bitboards".
        m.attacks = s == SQ_A1 ? table : magics[s - 1].attacks + size;

        // Use Carry-Rippler trick to enumerate all subsets of masks[s] and
        // store the corresponding sliding attack bitboard in reference[].
        b = size = 0;
        do
        {
            occupancy[size] = b;
            reference[size] = sliding_attack(pt, s, b);

            if (HasPext)
                m.attacks[pext(b, m.mask)] = reference[size];

            size++;
            b = (b - m.mask) & m.mask;
        } while (b);

        if (HasPext)
            continue;

        PRNG rng(seeds[Is64Bit][rank_of(s)]);

        // Find a magic for square 's' picking up an (almost) random number
        // until we find the one that passes the verification test.
        for (int i = 0; i < size;)
        {
            for (m.magic = 0; popcount((m.magic * m.mask) >> 56) < 6;)
                m.magic = rng.sparse_rand<Bitboard>();

            // A good magic must map every possible occupancy to an index that
            // looks up the correct sliding attack in the attacks[s] database.
            // Note that we build up the database for square 's' as a side
            // effect of verifying the magic. Keep track of the attempt count
            // and save it in epoch[], little speed-up trick to avoid resetting
            // m.attacks[] after every failed attempt.
            for (++cnt, i = 0; i < size; ++i)
            {
                unsigned idx = m.index(occupancy[i]);

                if (epoch[idx] < cnt)
                {
                    epoch[idx]     = cnt;
                    m.attacks[idx] = reference[i];
                }
                else if (m.attacks[idx] != reference[i])
                    break;
            }
        }
    }
}
}

}  // namespace Stockfish
