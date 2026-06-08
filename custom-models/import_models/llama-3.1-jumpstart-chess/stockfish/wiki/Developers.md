## Stockfish Development Setup

### Windows

<details>
<summary>Show more</summary>

#### Installing a compiler
1. https://www.msys2.org/
2. Download the installer

In the MSYS2 Installer change the installation folder to:
`C:\tools\msys64`

In the `URTC64` Shell run:
`pacman -S --needed base-devel mingw-w64-ucrt-x86_64-toolchain`

#### clang-format

Download [LLVM 17](https://github.com/llvm/llvm-project/releases/download/llvmorg-17.0.3/LLVM-17.0.3-win64.exe)

Run the executable and in the installer choose:
`Add LLVM to the system PATH for current user`

#### Video Setup

_There's a much higher quality version of this available on our [Discord](https://discord.com/channels/435943710472011776/1032922913499783169/1191837643256901732)._

https://github.com/official-stockfish/Stockfish/assets/45608332/d0323339-21f1-4d1d-aa86-183a7e10ed06

_More in depth information about various compilers can be found [here](https://github.com/official-stockfish/Stockfish/wiki/Compiling-from-source#windows)._

</details>

### Ubuntu

<details>
<summary>Show more</summary>

#### Installing a compiler

On Unix-like systems you will most likely have all the tools installed,  
which are required to build Stockfish. Expect `clang-format` which we use to format our codebase.

```bash
sudo apt install build-essential git
```

#### clang-format

```bash
sudo apt install clang-format-17
```

</details>

### MacOS

<details>
<summary>Show more</summary>

#### Installing a compiler

On MacOS you will need to install the Xcode Command Line Tools.  
It is enough to run the following command in your terminal, instead of installing the full Xcode.

```bash
sudo xcode-select --install
``` 

#### clang-format

```bash
brew install clang-format@17
```

</details>

## Participating in the project

Stockfish's improvement over the last decade has been a great community effort.
Nowadays most development talk takes place on [Discord](https://discord.gg/GWDRS3kU6R).

There are many ways to contribute to Stockfish:

- [Stockfish](#stockfish) (C++)
- [Fishtest](#fishtest) (Python)
- [nnue-pytorch](#nnue-pytorch) (C++ and Python)
- [Donating hardware](#donating-hardware)

### Stockfish

If you want to contribute to Stockfish directly, you can do so in a couple of ways.  
Follow the steps described in our [Fishtest wiki](https://github.com/official-stockfish/fishtest/wiki/Creating-my-first-test) to create your first test.  
__It is advised to first follow the [development setup](https://github.com/official-stockfish/Stockfish/wiki/Developers#stockfish-development-setup) steps for your platform__

New commits to stockfish can mostly be categorised in 2 categories:

#### Non functional changes

These are changes that don't change the search behaviour and can be directly
submitted as pull requests.

#### Functional changes

These change the search behaviour and lead to a different search tree.  
Every functional patch (commit) has to be verified by
[Fishtest](https://tests.stockfishchess.org/tests), our testing framework.

### NNUE Pytorch

NNUE Pytorch is the trainer for Stockfish's neural network.  
Usually changes here are tested by training a new network and testing it against the current network via Fishtest.

### Donating hardware

Improving Stockfish requires a massive amount of testing.  
You can donate your hardware resources by installing the [Fishtest Worker](https://github.com/official-stockfish/fishtest/wiki/Running-the-worker) and view the current tests on [Fishtest](https://tests.stockfishchess.org/tests).

## Using Stockfish in your own project

First of all, you should **read our [Terms of Use](#terms-of-use)** and follow them carefully.

Stockfish is a UCI chess engine, but what does that mean? It means that Stockfish follows the UCI protocol, which you find explained [here](https://backscattering.de/chess/uci/) in great detail. This is the usual way of communicating with Stockfish, so you do not need to write any C++!

Your next step is probably gonna be researching how you can open an executable in your programming language. You will need to write to `stdin` and listen to `stdout`, that is where Stockfish's output will end up.

### Examples

- Python: https://python-chess.readthedocs.io/en/latest/engine.html
- NodeJS: You can follow [this guide](https://blog.logrocket.com/using-stdout-stdin-stderr-node-js/) on how to communicate with a program.
- C++: [Boost.Process](https://www.boost.org/doc/libs/1_64_0/doc/html/process.html) can be used for easy process communication.
- Rust: Examine the documentation on [how to spawn a Command](https://doc.rust-lang.org/std/process/struct.Command.html).

### Limitations

> I want Stockfish to comment on the move it made, what do I need to do?

That is not possible. You will have to write your own logic to create such a feature.

> I want to get an evaluation of the current position.

While Stockfish has an [`eval`](Commands#eval) command, it only statically evaluates positions without performing any search. A more precise evaluation is available after you use the [`go`](Commands#go) command together with a specified limit.

### Other resources

- [Commands](UCI-&-Commands)
- [Advanced topics](Advanced-topics)
- [Useful data](Useful-data)

### Terms of use

Stockfish is free and distributed under the [**GNU General Public License version 3**](https://github.com/official-stockfish/Stockfish/blob/master/Copying.txt) (GPL v3). Essentially, this means you are **free to do almost exactly what you want** with the program, including **distributing it** among your friends, **making it available for download** from your website, **selling it** (either by itself or as part of some bigger software package), or **using it as the starting point** for a software project of your own. This also means that you can distribute Stockfish [alongside your proprietary system](https://www.gnu.org/licenses/gpl-faq.html#GPLInProprietarySystem), but to do this validly, you must make sure that Stockfish and your program communicate at arm's length, that they are not combined in a way that would make them effectively a single program.

The only real limitation is that whenever you distribute Stockfish in some way, **you MUST always include the license and the full source code** (or a pointer to where the source code can be found) to generate the exact binary you are distributing. If you make any changes to the source code, these changes must also be made available under GPL v3.

## Git Hooks

Place the following file into `.git/hooks/pre-push` and make it executable.
`chmod +x .git/hooks/pre-push`. This will prevent you from pushing commits that
do not contain a Bench or 'No functional change' in the commit message.

Only really useful for maintainers.

```bash
#!/bin/bash

if ! which clang-format-18 >/dev/null; then
    CLANG_FORMAT=clang-format
else
    CLANG_FORMAT=clang-format-18
fi

# Extracted from the Makefile
SRCS=$(awk '/^SRCS = /{flag=1; sub(/^SRCS = /,""); print} /^$/{flag=0} flag && !/^SRCS = /{print}' ./src/Makefile | tr -d '\\' | xargs echo | tr ' ' '\n' | sed 's|^|./src/|')
HEADERS=$(awk '/^HEADERS = /{flag=1; sub(/^HEADERS = /,""); print} /^$/{flag=0} flag && !/^HEADERS = /{print}' ./src/Makefile | tr -d '\\' | xargs echo | tr ' ' '\n' | sed 's|^|./src/|')

while read local_ref local_sha remote_ref remote_sha; do
    if [[ "$remote_ref" == "refs/heads/master" ]]; then
        # Check open diffs
        if [[ -n $(git status --porcelain) ]]; then
            echo "Please commit or stash your changes before pushing."
            exit 1
        fi

        # Check formatting
        if ! $CLANG_FORMAT --dry-run -Werror -style=file $SRCS $HEADERS; then
            echo "Please run 'make format' to fix formatting issues and rebase the last commit."
            exit 1
        fi

        # Iterate through commits
        for commit in $(git rev-list --no-merges $remote_sha..$local_sha); do
            commit_msg=$(git log --format=%B -n 1 $commit)

            # bench regex as defined in ci
            # check for the existence of a bench in the commit message
            bench_regex='\b[Bb]ench[ :]+[1-9][0-9]{5,7}\b'
            if echo "$commit_msg" | grep -m 1 -o -x -E "$bench_regex" >/dev/null; then
                continue
            fi

            # check for the existence of "No functional change" in the commit message
            no_functional_change_regex='\b[Nn]o[[:space:]][Ff]unctional[[:space:]][Cc]hange\b'
            if echo "$commit_msg" | grep -o -x -E "$no_functional_change_regex" >/dev/null; then
                continue
            fi

            echo "Commit $commit does not contain a Bench or 'No functional change'."
            exit 1
        done
    fi
done

exit 0
```