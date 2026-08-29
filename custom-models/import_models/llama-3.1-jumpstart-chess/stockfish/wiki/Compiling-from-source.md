## General

`make target [ARCH=arch] [COMP=compiler] [COMPCXX=cxx]`

### Targets

```
help                    > Display architecture details
profile-build           > standard build with profile-guided optimization
build                   > skip profile-guided optimization
net                     > Download the default nnue net
strip                   > Strip executable
install                 > Install executable
clean                   > Clean up
```

### Archs

```
native                  > select the best architecture for the host processor (default)
x86-64-vnni512          > x86 64-bit with vnni 512bit support
x86-64-vnni256          > x86 64-bit with vnni 512bit support, limit operands to 256bit wide
x86-64-avx512           > x86 64-bit with avx512 support
x86-64-avxvnni          > x86 64-bit with vnni 256bit support
x86-64-bmi2             > x86 64-bit with bmi2 support
x86-64-avx2             > x86 64-bit with avx2 support
x86-64-sse41-popcnt     > x86 64-bit with sse41 and popcnt support
x86-64-modern           > deprecated, currently x86-64-sse41-popcnt
x86-64-ssse3            > x86 64-bit with ssse3 support
x86-64-sse3-popcnt      > x86 64-bit with sse3 and popcnt support
x86-64                  > x86 64-bit generic (with sse2 support)
x86-32-sse41-popcnt     > x86 32-bit with sse41 and popcnt support
x86-32-sse2             > x86 32-bit with sse2 support
x86-32                  > x86 32-bit generic (with mmx and sse support)
ppc-64                  > PPC 64-bit
ppc-32                  > PPC 32-bit
armv7                   > ARMv7 32-bit
armv7-neon              > ARMv7 32-bit with popcnt and neon
armv8                   > ARMv8 64-bit with popcnt and neon
armv8-dotprod           > ARMv8 64-bit with popcnt, neon and dot product support
e2k                     > Elbrus 2000
apple-silicon           > Apple silicon ARM64
general-64              > unspecified 64-bit
general-32              > unspecified 32-bit
riscv64                 > RISC-V 64-bit
```

### Compilers

```
gcc                     > GNU compiler (default)
mingw                   > GNU compiler with MinGW under Windows
clang                   > LLVM Clang compiler
icc                     > Intel compiler
ndk                     > Google NDK to cross-compile for Android
```

### Simple examples

If you don't know what to do, you likely want to run:

Fast compile for most common modern CPUs
```bash
make -j build
```
Slow compile for 64-bit systems
```bash
make -j build ARCH=x86-64
```
Slow compile for 32-bit systems
```bash
make -j build ARCH=x86-32
```

### Advanced examples

For experienced users looking for performance:

```bash
# Providing no ARCH so it will try to find the best ARCH for you
make -j profile-build
```
```bash
make -j profile-build ARCH=x86-64-bmi2
```
```bash
make -j profile-build ARCH=x86-64-bmi2 COMP=gcc COMPCXX=g++-9.0
```
```bash
make -j build ARCH=x86-64-ssse3 COMP=clang
```

_See also: [How to lower compilation time](#lower-compilation-time) and [How to optimize for your CPU](#optimize-for-your-cpu)._

---

## Linux

On Unix-like systems, it should be easy to compile Stockfish directly from the source code with the included Makefile in the folder `src`.

In general it is recommended to run `make help` to see a list of make targets with corresponding descriptions.

```bash
cd src
make help
make -j profile-build ARCH=x86-64-avx2
```

---

## Windows

### About MSYS2 & MinGW-w64

MSYS2 is a software distribution and building platform for Windows. It provides a Unix-like environment, a command line interface, and a software repository, making it easy to install software on Windows or build software on Windows with either the GCC compiler or the Clang/LLVM compiler and using the Microsoft Visual C++ Runtime (mvscrt, shipped with all Windows versions) or the newer Microsoft Universal C Runtime (ucrt, shipped by default starting with Windows 10).

MSYS2 consists of several subsystems, `msys2`, `mingw32`, and `mingw64`:
* The `mingw32` and `mingw64` subsystems are native Windows applications that use either the mvscrt or the ucrt.
* The `msys2` subsystem provides an emulated mostly-POSIX-compliant environment based on Cygwin.

Each subsystem has an associated "terminal/shell", which is essentially a set of environment variables that allows the subsystems to co-operate properly:
* `MSYS2 MinGW x64`, to build Windows-native 64-bit applications with GCC compiler using mvscrt.
* `MSYS2 MinGW x86`, to build Windows-native 32-bit applications using GCC compiler using mvscrt.
* `MSYS2 MSYS`, to build POSIX applications using the Cygwin compatibility layer.
* `MSYS2 MinGW UCRT x64`, to build Windows-native 64-bit applications with GCC compiler using ucrt.
* `MSYS2 MinGW Clang x64`, to build Windows-native 64-bit applications with Clang/LLVM compiler using ucrt.

Refer to the [MSYS2 homepage](https://www.msys2.org/) for more detailed information on the MSYS2 subsystems and terminals/shells.

### Installing MSYS2

### Install MSYS2 with Chocolatey
[Chocolatey](https://chocolatey.org/) is a command line package manager for Windows, always run Chocolatey commands in a powershell/cmd with administrator rights (right click on `Start` menu, select `Windows Powershell (Admin)` or `Command Prompt (Admin)`):
1. Open a powershell (admin) (not a cmd) and copy the official [Chocolatey install command](https://chocolatey.org/install) to install Chocolatey
2. In a powershell/cmd (admin) execute the command `choco install msys2 -y`

As alternative write this text file `install_choco_msys2.cmd`, right click and select `Run as administrator`:
<details><summary>Click to view</summary>

```cmd
@echo off
::https://chocolatey.org/install
::https://chocolatey.org/courses/installation/installing?method=installing-chocolatey?quiz=true

::download and run install.ps1
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -InputFormat None -ExecutionPolicy Bypass -Command "[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))" && SET "PATH=%PATH%;%ALLUSERSPROFILE%\chocolatey\bin"
::install msys2
choco install msys2 -y
```
</details>

### Install MSYS2 with the official installer
1. Download and start the [one-click installer for MSYS2](https://www.msys2.org/). It's suggested to choose `C:\tools\msys64` as installation folder to be compatible with fishtest framework. MSYS2 no longer support an installer for Windows 32-bit, the [latest provided](https://github.com/msys2/msys2-installer/releases/tag/2020-05-17) is not able to install packages.
2. The installer runs a `MSYS2 MSYS` shell as a last step. Update the core packages by typing and executing `pacman -Syuu`. When finished, close the `MSYS2 MSYS` shell.

With MSYS2 installed to `C:\tools\msys64` your home directory will be `C:\tools\msys64\home\<your_username>`. Note that within the MSYS2 shell, paths are written in Unix-like way:

* Windows path: `C:\tools\msys64`
* Unix-like path: `/c/tools/msys64`
* Windows path: `C:\tools\msys64\home`
* Unix-like path: `/home` or `/c/tools/msys64/home`

_Note: You can also use `ls` to list the files and folders in a directory, similar to how you would use `dir` in Windows._

### GCC
This works with all the Windows versions.

1. Using your favorite text editor, copy and paste the following bash script, calling it `makefish.sh`:

<details><summary>64-bit Windows</summary>

```bash
#!/bin/bash
# makefish.sh

# install packages if not already installed
pacman -S --noconfirm --needed unzip make mingw-w64-x86_64-gcc

branch='master'
github_user='official-stockfish'

# download the Stockfish source code
wget -O ${branch}.zip https://github.com/${github_user}/Stockfish/archive/refs/heads/${branch}.zip
unzip -o ${branch}.zip
cd Stockfish-${branch}/src
file_nnue=$(grep 'define.*EvalFileDefaultName' evaluate.h | grep -Ewo 'nn-[a-z0-9]{12}.nnue')
ls *.nnue | grep -v ${file_nnue} | xargs -d '\n' -r rm --

# check all given flags
check_flags () {
    for flag; do
        printf '%s\n' "$flags" | grep -q -w "$flag" || return 1
    done
}

# find the CPU architecture
output=$(g++ -Q -march=native --help=target)
flags=$(printf '%s\n' "$output" | awk '/\[enabled\]/ {print substr($1, 3)}' | tr '\n' ' ')
arch=$(printf '%s\n' "$output" | awk '/march/ {print $NF; exit}' | tr -d '[:space:]')

if check_flags 'avx512vnni' 'avx512dq' 'avx512f' 'avx512bw' 'avx512vl'; then
  arch_cpu='x86-64-vnni256'
elif check_flags 'avx512f' 'avx512bw'; then
  arch_cpu='x86-64-avx512'
elif check_flags 'bmi2' && [ $arch != 'znver1' ] && [ $arch != 'znver2' ]; then
  arch_cpu='x86-64-bmi2'
elif check_flags 'avx2'; then
  arch_cpu='x86-64-avx2'
elif check_flags 'sse4.1' 'popcnt'; then
  arch_cpu='x86-64-sse41-popcnt'
elif check_flags 'ssse3'; then
  arch_cpu='x86-64-ssse3'
elif check_flags 'sse3' 'popcnt'; then
  arch_cpu='x86-64-sse3-popcnt'
else
  arch_cpu='x86-64'
fi

# build the fastest Stockfish executable
make -j profile-build ARCH=${arch_cpu} COMP=mingw
make strip
mv stockfish.exe ../../stockfish_${arch_cpu}.exe
make clean
cd
```
</details>

<details><summary>32-bit Windows</summary>

```bash
#!/bin/bash
# makefish.sh

# install packages if not already installed
pacman -S --noconfirm --needed unzip make mingw-w64-i686-gcc

branch='master'
github_user='official-stockfish'

# download the Stockfish source code
wget -O ${branch}.zip https://github.com/${github_user}/Stockfish/archive/refs/heads/${branch}.zip
unzip -o ${branch}.zip
cd Stockfish-${branch}/src
file_nnue=$(grep 'define.*EvalFileDefaultName' evaluate.h | grep -Ewo 'nn-[a-z0-9]{12}.nnue')
ls *.nnue | grep -v ${file_nnue} | xargs -d '\n' -r rm --

# find the CPU architecture
gcc_enabled=$(g++ -Q -march=native --help=target | grep "\[enabled\]")
gcc_arch=$(g++ -Q -march=native --help=target | grep "march")

if [[ "${gcc_enabled}" =~ "-mpopcnt " && "${gcc_enabled}" =~ "-msse4.1 " ]] ; then
  arch_cpu="x86-32-sse41-popcnt"
elif [[ "${gcc_enabled}" =~ "--msse2 " ]] ; then
  arch_cpu="x86-32-sse2"
else
  arch_cpu="x86-32"
fi

# build the fastest Stockfish executable
make -j profile-build ARCH=${arch_cpu} COMP=mingw
make strip
mv stockfish.exe ../../stockfish_${arch_cpu}.exe
make clean
cd
```
</details>

2. Start a `MSYS2 MinGW x64` shell (not a `MSYS2 MSYS` one), `C:\tools\msys64\mingw64.exe`, or start a `MSYS2 MinGW x86` shell, `C:\tools\msys64\mingw32.exe`, to build a 32 bit application.
3. Navigate to wherever you saved the script (e.g. type and execute `cd '/d/Program Files/Stockfish'` to navigate to `D:\Program Files\Stockfish`).
4. Run the script by typing and executing `bash makefish.sh`.

### Clang/LLVM
With Windows version older than Windows 10 you could need to install the Microsoft Windows Universal C Runtime.

1. Using your favorite text editor, copy and paste the following bash script, calling it `makefish.sh`:

<details><summary>64-bit Windows</summary>

```bash
#!/bin/bash
# makefish.sh

# install packages if not already installed
pacman -S --noconfirm --needed unzip make mingw-w64-clang-x86_64-clang

branch='master'
github_user='official-stockfish'

# download the Stockfish source code
wget -O ${branch}.zip https://github.com/${github_user}/Stockfish/archive/refs/heads/${branch}.zip
unzip -o ${branch}.zip
cd Stockfish-${branch}/src
file_nnue=$(grep 'define.*EvalFileDefaultName' evaluate.h | grep -Ewo 'nn-[a-z0-9]{12}.nnue')
ls *.nnue | grep -v ${file_nnue} | xargs -d '\n' -r rm --

# check all given flags
check_flags () {
    for flag; do
        printf '%s\n' "$flags" | grep -q -w "$flag" || return 1
    done
}

# find the CPU architecture
output=$(clang++ -E - -march=native -### 2>&1)
flags=$(printf '%s\n' "$output" | grep -o '"-target-feature" "[^"]*"' | cut -d '"' -f 4 | grep '^\+' | cut -c 2- | tr '\n' ' ')
arch=$(printf '%s\n' "$output" | grep -o '"-target-cpu" "[^"]*"' | cut -d '"' -f 4)

if check_flags 'avx512vnni' 'avx512dq' 'avx512f' 'avx512bw' 'avx512vl'; then
  arch_cpu='x86-64-vnni256'
elif check_flags 'avx512f' 'avx512bw'; then
  arch_cpu='x86-64-avx512'
elif check_flags 'bmi2' && [ $arch != 'znver1' ] && [ $arch != 'znver2' ]; then
  arch_cpu='x86-64-bmi2'
elif check_flags 'avx2'; then
  arch_cpu='x86-64-avx2'
elif check_flags 'sse4.1' 'popcnt'; then
  arch_cpu='x86-64-sse41-popcnt'
elif check_flags 'ssse3'; then
  arch_cpu='x86-64-ssse3'
elif check_flags 'sse3' 'popcnt'; then
  arch_cpu='x86-64-sse3-popcnt'
else
  arch_cpu='x86-64'
fi

# build the fastest Stockfish executable
make -j profile-build ARCH=${arch_cpu} COMP=clang
make strip COMP=clang
mv stockfish.exe ../../stockfish_${arch_cpu}.exe
make clean COMP=clang
cd
```
</details>

2. Start a `MSYS2 MinGW Clang x64` shell, `C:\tools\msys64\clang64.exe`.
3. Navigate to wherever you saved the script (e.g. type and execute `cd '/d/Program Files/Stockfish'` to navigate to `D:\Program Files\Stockfish`).
4. Run the script by typing and executing `bash makefish.sh`.

### Microsoft Visual Studio

_Note: Building Stockfish with Visual Studio is **not officially supported**._

It is required to explicitly set the stack reserve to avoid crashes. See point 5. below.

If you want to use MSVC to get a "optimized" build, you can change these settings in the IDE:

1. Add "NDEBUG;USE_POPCNT;USE_PEXT" to preprocessor definitions. Optionally, depending on your processor's support, add one of the following definitions: USE_AVX512 / USE_AVX2 / USE_SSSE3 / USE_SSE2 / USE_MMX. Also, if your processor supports VNNI instructions, add the USE_AVXVNNI definition. For a 64-bit target, if your CPU supports AVX or later extensions set one of the following: /arch:AVX or /arch:AVX2 or /arch:AVX512.
2. Optimization flags: /O2, /Oi, /Ot, /Oy, /GL
3. Static link with runtime: /MT.
4. Disable stack cookies: /GS-.
5. Set stack reserve to 8388608 in under Linker -> System or use the linker option /STACK:reserve=8388608. 
6. Disable debugging information in compiler/linker.
7. (VS 2017 only): Make a PGO instrument build(set under General), it should depend on "pgort140.dll" and it probably won't start.
8. (VS 2017 only): Copy pgort140.dll from "C:\Program Files (x86)\Microsoft Visual Studio\2017\Community\VC\Tools\MSVC\14.16.27023\bin\Hostx64\x64" to the output folder.
9. Run bench with the instrument build(very slow) and quit, it should generate "Stockfish.pgd" and "Stockfish!1.pgc".
10. Make a PGO optimized build(set under General), should show something like:

```
1>0 of 0 ( 0.0%) original invalid call sites were matched.
1>0 new call sites were added.
1>54 of 4076 (  1.32%) profiled functions will be compiled for speed, and the rest of the functions will be compiled for size
1>18615 of 46620 inline instances were from dead/cold paths
1>4076 of 4076 functions (100.0%) were optimized using profile data
1>14499840744 of 14499840744 instructions (100.0%) were optimized using profile data
```

11. Enjoy, local tests show comparable speed to GCC builds.

### Troubleshooting

If this tutorial will not work on your pc, you may try to change the `Windows Security` settings in via `Windows Security` >> `App & Browser Control` >> `Exploit Protection Settings`:
 1. Try to turn off _"Force randomization for images (Mandatory ASLR)"_, if this not solve the problem then,
 2. Try to turn off also _"Randomize memory allocations (Bottom-up ASLR)"_ .

### Using other MinGW-w64 with MSYS2

To use with MSYS2 a MinGW-w64 built by other projects, simply follow these instructions (Windows 64 bit):
1. Download another version of MinGW-w64, e.g. [MinGW-w64 (64-bit) GCC 8.1.0](https://www.msys2.org/), extract the *mingw64* folder renaming it to *mingw64-810*, copy the folder into *C:\msys64*, check to have the directory *C:\msys64\mingw64-810\bin*

2. Build Stockfish writing and executing this bash script
<details><summary>Click to view</summary>

```bash
#!/bin/bash
# makefish.sh

# set PATH to use GCC 8.1.0
if [ -d "/mingw64-810/bin" ] ; then
  PATH="/mingw64-810/bin:${PATH}"
else
  echo "folder error"
  exit 1
fi

branch='master'
github_user='official-stockfish'

# download the Stockfish source code
wget -O ${branch}.zip https://github.com/${github_user}/Stockfish/archive/refs/heads/${branch}.zip
unzip ${branch}.zip
cd Stockfish-${branch}/src

# find the CPU architecture
# CPU without popcnt and bmi2 instructions (e.g. older than Intel Sandy Bridge)
arch_cpu=x86-64
# CPU with bmi2 instruction (e.g. Intel Haswell or newer)
if [ "$(g++ -Q -march=native --help=target | grep mbmi2 | grep enabled)" ] ; then
  # CPU AMD zen
  if [ "$(g++ -Q -march=native --help=target | grep march | grep 'znver[12]')" ] ; then
    arch_cpu=x86-64-avx2
  else
    arch_cpu=x86-64-bmi2
  fi
# CPU with popcnt instruction (e.g. Intel Sandy Bridge)
elif [ "$(g++ -Q -march=native --help=target | grep mpopcnt | grep enabled)" ] ; then
  arch_cpu=x86-64-sse41-popcnt
fi

# build the Stockfish executable
make profile-build ARCH=${arch_cpu} COMP=mingw
make strip
mv stockfish.exe ../../stockfish_${arch_cpu}.exe
make clean 
cd
```
</details>

To use the compiler in the CLI write and run the script `use_gcc810.sh` in the user home folder
```bash
# set PATH to use GCC 8.1.0
# use this command: source use_gcc810.sh
if [ -d "/mingw64-810/bin" ] ; then
  PATH="/mingw64-810/bin:${PATH}"
else
  echo "folder error"
fi
```

---

## macOS

On macOS 10.14 or higher, it is possible to use the Clang compiler provided by Apple
to compile Stockfish out of the box, and this is the method used by default
in our Makefile (the Makefile sets the macosx-version-min=10.14 flag to select
the right libc++ library for the Clang compiler with recent c++17 support).

But it is quite possible to compile and run Stockfish on older versions of macOS! Below
we describe a method to install a recent GNU compiler on these Macs, to get
the c++17 support. We have tested the following procedure to install gcc10 on
machines running macOS 10.7, macOS 10.9 and macOS 10.13.

1) Install Xcode for your machine.

2) Install Apple command-line developer tools for Xcode, by typing the following
   command in a Terminal:

    ```bash
    sudo xcode-select --install
    ```

3) Go to the Stockfish "src" directory, then try a default build and run Stockfish:

    ```bash
    make clean
    make build
    make net
    ./stockfish
    ```

4) If step 3 worked, congrats! You have a compiler recent enough on your Mac
to compile Stockfish. If not, continue with step 5 to install GNU gcc10 :-)

5) Install the MacPorts package manager (https://www.macports.org/install.php),
for instance using the fast method in the "macOS Package (.pkg) Installer"
section of the page.

6) Use the "port" command to install the gcc10 package of MacPorts by typing the
following command:

    ```bash
    sudo port install gcc10
    ```

With this step, MacPorts will install the gcc10 compiler under the name "g++-mp-10"
in the /opt/local/bin directory:

```
which g++-mp-10

/opt/local/bin/g++-mp-10       <--- answer
```

7) You can now go back to the "src" directory of Stockfish, and try to build
Stockfish by pointing at the right compiler:

    ```bash
    make clean
    make build COMP=gcc COMPCXX=/opt/local/bin/g++-mp-10
    make net
    ./stockfish
    ```

8) Enjoy Stockfish on macOS!

See [this pull request](https://github.com/official-stockfish/Stockfish/pull/3049) for further discussion.

---

## For Android

You can build Stockfish for your ARM CPU based mobile Android device,
using the Stockfish supplied Makefile.

Supported architectures are:
- **armv7**: 32 bit ARM CPUs without Neon extension
- **armv7-neon**: 32 bit ARM CPUs with Neon SIMD Instruction Set Extension
- **armv8**: 64 bit ARM CPUs, with Neon extension

As most modern Android smartphones and tablets nowadays use armv8 64 bit CPUs,
we will cover these in this example. Before you try to build Stockfish, make sure
that you know what kind of CPU architecture your device uses. You will have to specify
one of the three mentioned architectures later on in the MAKE command by giving the
`"ARCH=..."` variable on the command line.

Furthermore you should be aware of the fact that Stockfish is just the chess engine.
You cannot use it stand-alone, rather you need a host program, i.e. a Chess GUI that
displays the chess board, takes your moves etc. on the one hand, and on the other hand
"talks" to the Stockfish chess engine so that it analyses the chess position in a game
and calculates its moves or variations, and gives that back to the GUI for display.

The Chess GUI which is probably used most often on Android is Droidfish, so we will
cover this here. You can get it from the [F-Droid](https://f-droid.org/repository/browse/?fdid=org.petero.droidfish) alternative app store.


To build Stockfish, you need:

1. The Android Native Development Kit (NDK), which contains a C/C++ compiler toolchain
   and all required headers and libraries to build native software for Android.

2. POSIX compatible build enviroment with GNU `coreutils`, `fileutils`and the `make`, `git`,
   `expect` (if you want to run the testsuite) and either `wget` or `curl` utilities.

   On Linux, install those tools using the package manager of your Linux distribution.

   On Windows, you can use MSYS2. We will assume further down in this example that
   you installed it to "C:\msys64". Adapt the instructions accordingly, if you installed
   it elsewhere.

   Please see [how to compile on Windows](#windows)
   for more details about MSYS2, but _**please note**_ that you ONLY need to install the basic
   MSYS environment and the package groups `base-devel`, `expect` and `git` with this command:
   ```bash
   pacman -S --noconfirm --needed base-devel expect git wget curl
   ```
   You do NOT need any of the MINGW64, MINGW32 nor the CLANG64 compiler toolchain for an Android build.
   We will use the Android NDK compiler toolchain instead.


To get the Android NDK, you have two options:

a) If you already have Android Studio installed, use its built-in SDK manager to download
   and install the NDK, as follows:

   - On the "Welcome to Android Studio" start page of the IDE, click "Customize" on the left pane,
     then click "All Settings..." on the bottom. This should open the "Android SDK" maintenance dialog.
   - Click on the "SDK Tools" tab on top of the list window.
   - Click and select the "NDK (Side by Side)" option and then click on "OK"
     This will download and install the latest NDK version under the directory
     of the "Android SDK Location" directory.
     
     In this example, for the Windows environment we will assume that Android Studio is installed
     in "C:\Android\Android Studio", and that the Android SDK is installed in "C:\Android\Sdk".
     The NDK will then have been installed in "C:\Android\Sdk\ndk" by the above installation process.

b) If you do NOT have Android Studio installed, don't worry! You don't need it.
   To download just the Android NDK, go to https://developer.android.com/ndk/downloads
   and pick the latest version for your platform. In this example we will stick to either Windows
   or Linux, but the Mac version should be not much different to use.

_Note: The latest LTS version is r23b (23.1.7779620). This will work fine. The minimum version you need is r21e (21.4.7075529), so if you already have that, you are all set._

If you downloaded it directly, unzip it to "C:\Android\Sdk\ndk\", or if you are on Linux, inside your home
directory to /home/(your user name)/Android/Sdk/ndk

When the installation is finished, locate the NDK compiler toolchain directory.

On Windows, this should be something like:
"C:\Android\Sdk\ndk\23.1.7779620\toolchains\llvm\prebuilt\windows-x86_64"

On Linux, the path might look like:
/home/johndoe/Android/Sdk/ndk/23.1.7779620/toolchains/llvm/prebuilt/linux-x86_64

On Linux, we are now almost ready to go. On Windows however, to simplify its use with MSYS2, we will
now create a symbolic link to that directory inside the MSYS2 installation directory.
To do that, open a CMD.EXE command prompt with Administrator privileges, and use the Windows command MKLINK as follows:
```cmd
mklink /D "C:\msys64\Android" "C:\Android\Sdk\ndk\23.1.7779620\toolchains\llvm\prebuilt\windows-x86_64"
```
Now the Android NDK compiler toolchain is available from inside an MSYS environment terminal session
in the same way as the MINGW64 toolchain would be, and we don't have to type such long path names anymore.

On Windows, you should now start the MSYS environment launcher. This will give you a terminal session
with the Bash (1) shell. The PATH environment variable DOES NOT include a compiler toolchain yet. Verify this by entering:

```bash
$ echo $PATH
/usr/local/bin:/usr/bin:/bin:/opt/bin:/c/Windows/System32:/c/Windows:/c/Windows/System32/Wbem:/c/Windows/System32/WindowsPowerShell/v1.0/:/usr/bin/site_perl:/usr/bin/vendor_perl:/usr/bin/core_perl
```

On Linux, you can just open a plain terminal session.

Now we prepend the NDK compiler toolchain bin/ subdirectory to our PATH:

On Windows:
```bash
$ export PATH=/Android/bin:$PATH
```

On Linux:
```bash
$ export PATH=/home/johndoe/Android/Sdk/ndk/23.1.7779620/toolchains/llvm/prebuilt/linux-x86_64/bin:$PATH
```

_Note: These PATH settings are in effect only for your current session._

Now you should be able to call the compiler we will use from the command line.
Let's check which version we have, this example output is from Windows, the Linux output should be quite similar.

```bash
$ aarch64-linux-android21-clang++ --version
Android (7019983 based on r365631c3) clang version 9.0.9 (https://android.googlesource.com/toolchain/llvm-project a2a1e703c0edb03ba29944e529ccbf457742737b) (based on LLVM 9.0.9svn)
Target: aarch64-unknown-linux-android21
Thread model: posix
InstalledDir: C:\msys64\Android\bin
$
```

If you get an error message that the command "aarch64-linux-android21-clang++" could not be found, please go back
and check that you have got all the path names correct in the above steps.

Now we will checkout the Stockfish source code with git, and start the build. The steps for Windows in the MSYS environment
session and for Linux are now basically the same. In your home directory, make subdirectories for the git checkout:

```bash
$ mkdir -p ~/repos/official-stockfish
$ cd ~/repos/official-stockfish
$ git clone https://github.com/official-stockfish/Stockfish.git
.
.
.
$ cd Stockfish/src
```

Now lets start the build. First we can display a help page with all the supported make targets (and ignore them :-)

```bash
$ make help
```

Next we download the NNUE neural network that powers Stockfish's evaluation. By default, it will be embedded into the
compiled `stockfish` executable.

```bash
$ make net
```

This should download `<some hex hash code...>.nnue` file. If you get an error message that neither `curl`
nor `wget` are installed, then please install one of these tools and repeat.

Now we are ready to build. You now need to know your architecture (see the start of this documentation).
We will use armv8 as an example here. Issue the command:

```bash
$ make -j build ARCH=armv8 COMP=ndk
```

After a short amount of time (or a minute, or two, depending on the speed of your machine) the compilation and
linking should complete with messages like this:

```bash
.
.
aarch64-linux-android21-clang++ -o stockfish benchmark.o bitbase.o bitboard.o endgame.o evaluate.o main.o material.o misc.o movegen.o movepick.o pawns.o position.o psqt.o search.o thread.o timeman.o tt.o uci.o ucioption.o tune.o tbprobe.o evaluate_nnue.o half_ka_v2_hm.o  -static-libstdc++ -pie -lm -latomic -Wall -Wcast-qual -fno-exceptions -std=c++17  -stdlib=libc++ -fPIE -DUSE_PTHREADS -DNDEBUG -O3 -fexperimental-new-pass-manager -DIS_64BIT -DUSE_POPCNT -DUSE_NEON=8 -flto
make[1]: Leaving directory '/home/johndoe/repos/official-stockfish/Stockfish/src'
```

You will now have a binary file called `stockfish` in your current directory. Check with the file command that
it is indeed an ARM binary for Android:

```bash
$ file stockfish
stockfish: ELF 64-bit LSB shared object, ARM aarch64, version 1 (SYSV), dynamically linked, interpreter /system/bin/linker64, with debug_info, not stripped
```

To make it smaller and run faster, we should strip the symbol table from the executable; this is not needed for running it, only for debugging.
Issue the command:

```bash
$ make strip ARCH=armv8 COMP=ndk
aarch64-linux-android-strip stockfish
```

Issuing the file command again shows that it has been stripped:

```bash
$ file stockfish
stockfish: ELF 64-bit LSB shared object, ARM aarch64, version 1 (SYSV), dynamically linked, interpreter /system/bin/linker64, stripped
```

It is a good idea to rename the binary:

```bash
$ mv stockfish stockfish_DEV_armv8
```

So in Droidfish you will be able to see that you are running your self compiled DEVelopment version of Stockfish, and not the built-in
version, which is substantially older.

Voilà: you have your Android build of Stockfish. What is now left to do is to copy it over to your smartphone or tablet,
to the "uci" subdirectory of your Droidfish installation. You can find the Droidfish documentation here:
https://github.com/peterosterlund2/droidfish/tree/master/doc

To do this, the easiest possibility is to have your build machine and your Android device on the same network,
create a Windows network share, copy the Stockfish binary into that share directory, and then on your Android
device use the File Manager app to connect to that network share and copy the Stockfish binary over to the
Droidfish uci (engines) directory.

In Droidfish, open the left menu, find the Engines management submenu, pick the `stockfish_DEV_armv8` binary,
and in the configuration menu adjust its UCI parameter settings. Depending on the CPU power of your device
and the available memory, you should probably give it more than the default one Thread, and more than the default
16 MB of Hash memory. A good start would be to try 2 Threads, and 512 MB for the Hash tables, and see if you can beat it ;-)

_Note: As Stockfish is a very computation-intense program, you should probably not give it as many threads as
your device CPU has processor cores. Especially in Analysis mode, when Stockfish is thinking permanently, and for
extended amounts of time, this might suck your device battery empty quite quickly._

Enjoy!

---

## Cross compilation

### For Windows in Ubuntu

The script works with Ubuntu 18.04, Ubuntu 21.10 and Ubuntu 22.04, other versions could still have a packaging bug.

<details><summary>Click to view</summary>

```bash
#!/bin/bash
# functions to build Stockfish
_build_sf () {
make build ARCH=x86-64$1 COMP=mingw -j
make strip COMP=mingw
mv stockfish.exe ../../stockfish-x64${1}.exe
make clean COMP=mingw
}

_build_sf_pgo () {
make profile-build ARCH=x86-64$1 COMP=mingw PGOBENCH="wine ./stockfish.exe bench" -j
make strip COMP=mingw
mv stockfish.exe ../../stockfish-x64${1}-pgo.exe
make clean COMP=mingw
}

# full-upgrade and install required packages
sudo apt update && sudo apt full-upgrade -y && sudo apt autoremove -y && sudo apt clean
sudo apt install -y \
  make \
  mingw-w64 \
  git \
  wine64 \
  binutils

# clone Stockfish source code
git clone --single-branch --branch master https://github.com/official-stockfish/Stockfish.git
cd Stockfish/src

# build Stockfish executables
# to speedup the building process you can keep only the section fitting your CPU architecture

# build the binary for CPUs without popcnt and bmi2 instructions (e.g. older than Intel Sandy Bridge)
_build_sf_pgo
  
# build the binary for CPU with popcnt instruction (e.g. Intel Sandy Bridge)
if [ "$(x86_64-w64-mingw32-c++-posix -Q -march=native --help=target | grep mpopcnt | grep enabled)" ] ; then
  _build_sf_pgo -sse41-popcnt
else
  _build_sf -sse41-popcnt
fi
  
# build the binary for CPU with bmi2 instruction (e.g. Intel Haswell or newer)
if [ "$(x86_64-w64-mingw32-c++-posix -Q -march=native --help=target | grep mbmi2 | grep enabled)" ] ; then
  _build_sf_pgo -bmi2
else
  _build_sf -bmi2
fi
```
</details>

### For all platforms using Zig

[Zig](https://ziglang.org/) is a programming language in early development stage that is binary compatible with C.
The Zig toolchain, based on LLVM, ships the source code of all the required libraries to easily cross compile Zig/C/C++ code for several CPU Architecture and OS combinations. All the work required is to set as target the proper supported [triple \<arch-os-abi\>](https://github.com/ziglang/zig-bootstrap#supported-triples) (eg `x86_64-windows-gnu`, `aarch64-linux-musl`).

You can use Zig:
* installing Zig with a [package manager](https://github.com/ziglang/zig/wiki/Install-Zig-from-a-Package-Manager) for your OS, or
* unzipping the [Zig archive](https://ziglang.org/download/) (~50 Mbi) and setting the PATH for the shell with `export PATH=/home/username/zig:$PATH`

Note: `snap` does not work on WSL, download the archive. 

Here is a script to cross compile from a clean Ubuntu a static build of Stockfish targeting an armv8 or armv7 CPU running on Linux or Android:

<details><summary>Click to view</summary>

```bash
# Use a clean Ubuntu to cross compile
# a static build for armv8 and armv7 on Linux/Android

# one time configuration
sudo apt update && sudo apt install -y make git
sudo snap install zig --classic --edge
sudo apt install -y qemu-user

# armv8 static build with musl libc
git clone https://github.com/official-stockfish/Stockfish.git
cd Stockfish/src
make -j build ARCH=armv8 COMP=gcc CXX="zig c++ -target aarch64-linux-musl"

# test: qemu's magic at work
qemu-aarch64 stockfish compiler
qemu-aarch64 stockfish bench

# armv7 static build with musl libc
# comment out "-latomic" flag in Makefile
make clean
make -j build ARCH=armv7 COMP=gcc CXX="zig c++ -target arm-linux-musleabihf"

# test: qemu's magic at work
qemu-arm stockfish compiler
qemu-arm stockfish bench

```
</details>

Here is a script to cross compile from a msys2 msys/mingw-w64 shell a static build of Stockfish targeting an armv8 or armv7 CPU running on Linux or Android:

<details><summary>Click to view</summary>

```bash
# Use msys2 to cross compile
# a static build for armv8 and armv7 on Linux/Android

# one time configuration
pacman -S --noconfirm --needed git make unzip
wget https://ziglang.org/builds/zig-windows-x86_64-0.10.0-dev.2220+802f22073.zip
unzip zig-windows-x86_64-0.10.0-dev.2220+802f22073.zip
PATH=$(pwd)/zig-windows-x86_64-0.10.0-dev.2220+802f22073:${PATH}

# armv8 static build with musl libc
git clone https://github.com/official-stockfish/Stockfish.git
cd Stockfish/src
make -j build ARCH=armv8 COMP=gcc CXX="zig c++ -target aarch64-linux-musl"
mv stockfish.exe stockfish_armv8
```
</details>

---

## Lower compilation time

It is possible to lower the compile time on cpu multi core using make with the flag *-j \<n_jobs\>*, where \<n_jobs\> is the number of jobs (commands) to run simultaneously. The flag *-j* enables one job for each logical CPU core. 

```bash
make -j <n_jobs> profile-build ARCH=x86-64-avx2 COMP=mingw
```

---

## Optimize for your CPU

To get the max speedup for your CPU (1.5% on Ivy Bridge) simply prepend the shell variable `CXXFLAGS='-march=native'` to the `make` command. At example, for a CPU Sandy/Ivy Bridge use this command:

```bash
CXXFLAGS='-march=native' make -j profile-build ARCH=x86-64-avx2 COMP=gcc
```

To view the compiler flags for your CPU: 

```
# for gcc
gcc -Q -march=native --help=target | grep -v "\[disabled\]"

# for clang
clang -E - -march=native -###
```

*-march=native* implies *-mtune=native*, below a high level explanation of the compiler flags *-march* and *-mtune*, view the [gcc manual](https://gcc.gnu.org/onlinedocs/gcc-5.3.0/gcc/x86-Options.html#x86-Options) for more technically sound details:

  * *-march*: determines what instruction sets are used in the binary. An instruction set is the list of commands implemented by the cpu. **The generated code may not run at all on processors other than the one indicated.**

  * *-mtune*: determines the cost model that is used when generating code. The cost model describes how long it takes the cpu to do operations. This information is used by the scheduler to decide what operations to use and in what order.
