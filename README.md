# server-challenges

My 23 entries in three server performance challenges run by [arjaythedev](https://github.com/arjaythedev): the same
small APIs written 23 times in 14 languages, from C and x86-64 assembly to COBOL, TeX, and Zsh. Each challenge asks
one question (how many users can this box hold?) and scores it the same way for everyone: a 5-minute hold under a
load generator, judged on p95, p99 and errors. Most entries are tuned C, Rust, Zig, Go and assembly. The rest answer
a different question: can COBOL, a text editor, a typesetter or a login shell serve a JSON API at all? They can.

Live ranks: [coreyjones.dev/#benchmarks](https://coreyjones.dev/#benchmarks). Every entry here is a byte-for-byte copy
of what is merged upstream, and [`entries.json`](entries.json) records where each one came from.

## The three challenges

**[The Million Users Challenge](https://github.com/arjaythedev/million-users-challenge).** A small feed API, five
endpoints (feed, read a post, create a post, like, health), backed by Postgres 18 on its own 16-core box. The app box
runs Ubuntu 24.04 with 16 dedicated vCPUs and 32 GB, and there is no Nginx: the server holds every keep-alive
connection itself, on two ports. Each entry gets three scores, the most users held for 5 minutes on 16, 8 and 4
cores, with p95 under 500 ms, p99 under 1 s and under 1% errors. 16 cores is capped at 1,000,000 users because past
that the single Postgres box is the limit; 8 and 4 cores are searched up to 3,000,000. The best stock framework in
the video held 665,000 on 16 cores.

**[The Multicore Server Challenge](https://github.com/arjaythedev/multicore-server-challenge).** The RealWorld
"Conduit" backend, a Medium clone with 19 endpoints, on an 8 vCPU / 16 GB box shared with Postgres 18
(`max_connections = 100`). Every password is bcrypt cost 10 and every token is verified on every request. A virtual
user browses like a person (about 7 s between pages, 95% reads), and the score is the most users that pass a 5-minute
hold with the same p95, p99 and error limits. The best stock framework in the video held 22,000. The challenge is now
closed to new submissions.

**[The $12 Server Challenge](https://github.com/arjaythedev/twelve-dollar-server-challenge).** The same five-endpoint
feed API, but on SQLite in-process, on 1 vCPU and 2 GB (a Synteq VPS, Xeon Platinum 8260, Ubuntu 24.04, no swap).
Nginx in front is optional; going direct saves its CPU but means holding every keep-alive connection yourself. The
search doubles the users until a 2-minute probe fails, narrows down, and the score is the most users that pass a
5-minute hold (p95 under 500 ms, p99 under 1 s, under 1% errors).

All three share the same rules in spirit: no caching across requests, every write committed before the response,
every JWT signature checked, built from source on the box with the entry's own `install.sh` and `build.sh`.

## Results

From each upstream `LEADERBOARD.md` on `main`, as of 2026-11-15. Ranks are left out on purpose, because they move every
time someone lands an entry: see [coreyjones.dev/#benchmarks](https://coreyjones.dev/#benchmarks) or the upstream
boards for those. Open and closed PRs are follow-ups that are not part of the score.

### Million Users

Most users held for 5 minutes, by cores. The board has no req/s column, and only entries near the top get a 2-core
run. [Upstream board](https://github.com/arjaythedev/million-users-challenge/blob/main/LEADERBOARD.md),
[live](https://benchmarks.arjaythedev.com/million-users).

| Entry | Language and approach | 16 cores | 8 cores | 4 cores | 2 cores | PRs |
|---|---|--:|--:|--:|--:|---|
| [c-epoll](million-users/c-epoll) | C: epoll loop per core, own Postgres wire client, group commit, TCP_DEFER_ACCEPT, ISA-L gzip | 1,000,000 (max) | 1,430,000 | 1,480,000 | 990,000 | [#10](https://github.com/arjaythedev/million-users-challenge/pull/10), [#90](https://github.com/arjaythedev/million-users-challenge/pull/90), [#96](https://github.com/arjaythedev/million-users-challenge/pull/96), [#100](https://github.com/arjaythedev/million-users-challenge/pull/100), [#104](https://github.com/arjaythedev/million-users-challenge/pull/104), [#115](https://github.com/arjaythedev/million-users-challenge/pull/115) (closed), [#129](https://github.com/arjaythedev/million-users-challenge/pull/129) (open) |
| [rust-uring](million-users/rust-uring) | Rust: raw io_uring thread per core, own Postgres wire client, reads packed under one Sync, group commit | 1,000,000 (max) | 1,360,000 | 1,340,000 | not run | [#30](https://github.com/arjaythedev/million-users-challenge/pull/30), [#73](https://github.com/arjaythedev/million-users-challenge/pull/73), [#97](https://github.com/arjaythedev/million-users-challenge/pull/97) |
| [rust-tokio](million-users/rust-tokio) | Rust: current-thread tokio per core, SO_REUSEPORT, pipelined tokio-postgres | 1,000,000 (max) | 1,260,000 | 960,000 | not run | [#11](https://github.com/arjaythedev/million-users-challenge/pull/11) |

### Multicore

[Upstream board](https://github.com/arjaythedev/multicore-server-challenge/blob/main/LEADERBOARD.md),
[live](https://benchmarks.arjaythedev.com/multicore).

| Entry | Language and approach | Users | req/s | PRs |
|---|---|--:|--:|---|
| [c-epoll](multicore/c-epoll) | C: epoll, own Postgres client, bcrypt and gzip, batched reads as index-scan pipelines, direct | 210,000 | 52,012 | [#203](https://github.com/arjaythedev/multicore-server-challenge/pull/203), [#226](https://github.com/arjaythedev/multicore-server-challenge/pull/226) (open) |
| [go-epoll](multicore/go-epoll) | Go: hand-written epoll loops, pgx pgconn, one read statement per window, group commit, own bcrypt | 120,000 | 30,100 | [#89](https://github.com/arjaythedev/multicore-server-challenge/pull/89) |
| [rust-tokio](multicore/rust-tokio) | Rust: tokio, tokio-postgres, batched unnest() reads, group commit, own bcrypt | 110,000 | 27,975 | [#90](https://github.com/arjaythedev/multicore-server-challenge/pull/90), [#119](https://github.com/arjaythedev/multicore-server-challenge/pull/119) |

### $12 Server

Users held 5 min, and the req/s of that hold.
[Upstream board](https://github.com/arjaythedev/twelve-dollar-server-challenge/blob/main/LEADERBOARD.md),
[live](https://benchmarks.arjaythedev.com/12-dollar-server).

| Entry | Language and approach | Users | req/s | PRs |
|---|---|--:|--:|---|
| [c-iouring](twelve-dollar/c-iouring-unorig-username) | C: io_uring, SQLite B-tree cursor reads, group commit, PGO | 280,000 | 26,688 | [#184](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/184), [#290](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/290), [#362](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/362) (open) |
| [asm-iouring](twelve-dollar/asm-iouring-unorig-username) | x86-64 assembly: NASM, io_uring through raw syscalls, group commit | 250,000 | 24,053 | [#182](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/182), [#206](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/206) |
| [zig-iouring](twelve-dollar/zig-iouring-unorig-username) | Zig: std.os.linux.IoUring, group commit, PGO-built SQLite | 235,000 | 22,785 | [#190](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/190) |
| [c-epoll](twelve-dollar/c-epoll-unorig-username) | C: one epoll loop, group commit, PGO | 210,000 | 20,425 | [#183](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/183) |
| [zig-epoll](twelve-dollar/zig-epoll-unorig-username) | Zig: one epoll loop, group commit, own SHA-256 | 200,000 | 19,661 | [#189](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/189) |
| [go-epoll](twelve-dollar/go-epoll-unorig-username) | Go: raw epoll syscalls, SQLite through cgo, group commit | 165,000 | 16,020 | [#186](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/186) |
| [asm-epoll](twelve-dollar/asm-epoll-unorig-username) | x86-64 assembly: NASM, one epoll loop, no libc for its own code | 155,000 | 15,256 | [#181](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/181) |
| [cobol-gnucobol](twelve-dollar/cobol-gnucobol-unorig-username) | COBOL: GnuCOBOL 3.2, epoll and SQLite through CALL STATIC | 126,000 | 12,398 | [#185](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/185) |
| [java-nio](twelve-dollar/java-nio-unorig-username) | Java: NIO selector, SQLite through FFM, no JDBC | 125,000 | 12,303 | [#187](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/187) |
| [rust-iouring](twelve-dollar/rust-iouring-unorig-username) | Rust: io-uring crate, one thread, group commit | 120,000 | 11,799 | [#188](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/188) |
| [lua-neovim](twelve-dollar/lua-neovim-unorig-username) | Lua: Neovim as the server, libuv, LuaJIT FFI to SQLite | 110,000 | 10,785 | [#443](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/443), [#463](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/463) (open) |
| [tcl-tclsh](twelve-dollar/tcl-tclsh-unorig-username) | Tcl: tclsh 8.6 event loop, SQLite's own Tcl binding, behind Nginx | 24,000 | 2,364 | [#456](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/456) |
| [prolog-swipl](twelve-dollar/prolog-swipl-unorig-username) | Prolog: SWI-Prolog, routes as clauses, JSON as a DCG, behind Nginx | 24,000 | 2,362 | [#455](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/455) |
| [tex-luatex](twelve-dollar/tex-luatex-unorig-username) | TeX: a LuaTeX job as the server, JSON bodies as macro expansions, behind Nginx | 24,000 | 2,362 | [#457](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/457), [#468](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/468) (open) |
| [elisp-emacs](twelve-dollar/elisp-emacs-unorig-username) | Emacs Lisp: Emacs in batch mode, built-in SQLite, behind Nginx | 24,000 | 2,359 | [#444](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/444), [#464](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/464) (open) |
| [octave-sockets](twelve-dollar/octave-sockets-unorig-username) | GNU Octave: server.m plus a small C++ oct-file for epoll and SQLite, direct | 18,500 | 1,806 | [#458](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/458) |
| [zsh-ztcp](twelve-dollar/zsh-ztcp-unorig-username) | Zsh: ztcp and zselect loop, HMAC-SHA256 in shell arithmetic, behind Nginx | 8,500 | 833 | [#459](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/459) |

## What mattered

Each lesson links where it was measured. Unless it says "the board", a number is from my own test rig as written up
in that PR or README, not from the benchmark box, and only compares runs on the same rig.

**1. io_uring beat epoll on one vCPU, but not because syscalls are cheaper.** In each language where I wrote both, the
io_uring entry beat its epoll twin on the $12 board: C 250,000 vs 210,000 (the C io_uring entry's first scored run,
before the B-tree reads in lesson 5), assembly 250,000 vs 155,000, Zig 235,000 vs 200,000. But the
[c-iouring README](twelve-dollar/c-iouring-unorig-username/README.md) measured the bare io_uring loop level with epoll
at 64 connections and 8% behind at 1,024, because two thirds of the CPU was the kernel's TCP work either way. The C
pair share feed range scans, group commit and PGO ([#183](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/183)). What the io_uring entry
adds is a wait for a batch of completions after a busy pass (21% less CPU per request, lesson 2), and registered file
descriptors, so one process holds more connections than `LimitNOFILE` ([#184](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/184)).
io_uring also has its own traps.
Cancelling a closed connection's operations by descriptor makes the kernel walk every pending operation on the ring;
cancelling by completion tag is a hash lookup. With 20,000 idle connections that took CPU per request from about
290 us to about 20 us ([#184](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/184),
[#190](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/190),
[#182](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/182)). And io_uring alone is not enough:
the Rust io_uring entry holds 120,000, below the Go epoll one at 165,000.

**2. Do more work per wake-up.** The cheapest request is the one that shares a syscall, a round trip and a commit
with its neighbours. In the $12 entries, after a busy pass the loop waits for up to 128 completions or a few
milliseconds: 21% less CPU per request in C, 11% in Zig and Rust
([#184](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/184),
[#190](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/190),
[#188](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/188)). For the Postgres challenges the same
idea is a 2 ms batching window per thread (43% less server CPU per request at 60k users,
[#10](https://github.com/arjaythedev/million-users-challenge/pull/10)) and packing a pass's reads under one Sync:
TCP segments per request went from 4.34 to 3.45 and Postgres CPU per request fell 24%
([#73](https://github.com/arjaythedev/million-users-challenge/pull/73)).

**3. Group commit fixes the write tail, not throughput.** The multicore Rust entry failed its 5-minute holds on p99
while passing 2-minute probes. Writes went one transaction each over 6 connections, so every checkpoint and the
autovacuum after it stalled them on WAL flushes. Sending all waiting writes as one transaction per connection took a
110k-user hold, with Postgres capped at 400 IOPS, from p99 10,027 ms and 9.21% errors to 264 ms and 0, at the same CPU
([#119](https://github.com/arjaythedev/multicore-server-challenge/pull/119)). In SQLite it also cuts disk writes: a
write costs 3.35 WAL frames committed alone, 1.95 at 22 per commit and 1.25 at 256
([#362](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/362)). Every response still waits for its
commit. It only pays when there is a group: the Emacs entry measured it and left it out, and the Tcl entry skipped it,
because at their load a turn of the event loop almost never holds two writes ([elisp-emacs](twelve-dollar/elisp-emacs-unorig-username/README.md),
[tcl-tclsh](twelve-dollar/tcl-tclsh-unorig-username/README.md)).

**4. Accepting connections is part of the hot path.** The maintainer's run of the assembly io_uring entry saw p99 jump
from 130k users at only about 50% CPU, mostly on `GET /feed`. The cause: only 16 single-shot accepts in flight,
rearmed once per pass, so during the ramp new users' first requests (usually the feed) waited in the listen queue.
Raising it to 256 is one constant ([#206](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/206));
the same fix in the C version on my x86 rig went from failing 330,000 users at about 1,700 accepts/s to holding
365,000. The entry holds 250,000 on the board. On the million-user box, `TCP_DEFER_ACCEPT` makes the kernel hand
over a connection only once its first request has arrived, so each new connection costs one wake-up instead of two
([#104](https://github.com/arjaythedev/million-users-challenge/pull/104)).

**5. SQLite's read path and checkpoints set the ceiling on $12.** In WAL mode SQLite copies the log back every 1,000
pages, inline, in whichever `COMMIT` crosses the line, and that fsync stalls every client in the batch. The C,
assembly, Zig, Go, COBOL, Java and Rust entries run `PASSIVE` checkpoints in a helper process instead
([cobol-gnucobol](twelve-dollar/cobol-gnucobol-unorig-username/README.md),
[#183](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/183)). My best $12 entry, c-iouring, then stopped asking the SQL engine
for reads at all: `/feed` and `/posts/:id` walk SQLite's B-tree cursors directly, with the reference SQL as the
fallback. That read code is adapted from another entrant's entry, rust-iouring-kensac
([#248](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/248), [#264](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/264)),
and so are the ideas of a low-priority checkpoint thread, bounded reads and answers after a burst, and SQLite's page
cache over `mmap`, as the c-iouring [credits](twelve-dollar/c-iouring-unorig-username/README.md#credits) say. The
follow-up that brought them in took the board score from 250,000 to 280,000
([#290](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/290)). On my rig the page cache beat `mmap` by 4% CPU per request.

**6. On 2 GB, memory per connection is the next wall.** Each open connection costs about 4.3 KB of kernel memory
(3.3 KB of slab, 1 KB of dentries and inodes), so every 100 MB the process keeps is about 23,000 users. A larger WAL
checkpoint threshold saved CPU but moved the out-of-memory kill from about 350,000 connections to about 330,000
([c-iouring](twelve-dollar/c-iouring-unorig-username/README.md)). The fix on the app side is to own nothing while
idle: provided buffer rings in io_uring, and no per-connection buffers in epoll. The million-user C entry keeps a 40-byte
slot per connection and held 300,000 connections at 26 MB RSS ([c-epoll](million-users/c-epoll/README.md)).

**7. The proxy in front sets its own ceiling.** Seven entries behind the board's Nginx, four of them mine, sit at
exactly 24,000 users. When the first four got there, all failed the same way: errors only on POSTs, at anywhere from
49% to 93% CPU. Nginx has 16,384 `worker_connections`; 24,000 keep-alive users do not fit, so it closes idle client connections,
and a client retries a GET that lands on one but not a POST
([#464](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/464)). The board's notes on my Emacs,
Prolog, Tcl and TeX entries show the same signature: 0.95 to 0.97% errors, all on writes, at 59 to 76% CPU. The way
out is to serve direct: the maintainer's run of the Emacs follow-up held 35,000, pending a rules question, and the TeX
follow-up held 65,000 locally ([#468](https://github.com/arjaythedev/twelve-dollar-server-challenge/pull/468)).

**8. What did not help.** Capping the million-user C entry at 4 threads, so each Sync carried a bigger batch, lost
160,000 users on 8 cores (1,420,000 to 1,260,000); it was reverted
([#90](https://github.com/arjaythedev/million-users-challenge/pull/90),
[#96](https://github.com/arjaythedev/million-users-challenge/pull/96)). Synchronous `RESTART` checkpoints in the
loop cut write throughput 40%, and 1,024 smaller receive buffers took ramp p95 from 7 to 118 ms
([c-iouring](twelve-dollar/c-iouring-unorig-username/README.md)). A 16-lane AVX-512 gather bcrypt took 18.5 ms per
hash against 12.95 for the kept version ([multicore c-epoll](multicore/c-epoll/README.md)). Emacs native
compilation measured the same as byte code, because the time is in C primitives
([elisp-emacs](twelve-dollar/elisp-emacs-unorig-username/README.md)).

## The novelty entries

The $12 rules allow any language with a SQLite binding, so eight entries use runtimes that were never meant to serve
HTTP. Every one passes the same 42-check test suite as the C entries.

**Neovim** ([lua-neovim](twelve-dollar/lua-neovim-unorig-username)). `start.sh` runs
`nvim --headless --clean -l server.lua` and nothing else. Neovim's own libuv loop serves HTTP/1.1 on port 80, and
LuaJIT's FFI calls the system SQLite and libcrypto, so no code of mine is compiled. Past 60,000 connections it starts
a fresh Neovim that inherits the listening socket. It is still an editor: buffer 1 holds a live counter you can read
from another shell with `--remote-expr`. It holds 110,000 users, 10,000 behind the Rust io_uring entry.

**Emacs** ([elisp-emacs](twelve-dollar/elisp-emacs-unorig-username)). One byte-compiled Emacs Lisp file run by
`emacs --batch`: a `make-network-process` server, a process filter that parses HTTP, Emacs 29's built-in SQLite, and
HS256 built from `secure-hash`. Letting SQLite's `json_object` render the posts, so Emacs gets one string per feed
instead of consing 20 rows, was worth about 30%. It sits behind Nginx because Emacs waits on `select`.

**COBOL** ([cobol-gnucobol](twelve-dollar/cobol-gnucobol-unorig-username)). The epoll loop, HTTP parser, strict JSON
validator, JWT checks and group commit are all COBOL, calling libc, SQLite and libcrypto's SHA-256 through
`CALL STATIC` with no C glue file. GnuCOBOL turns `COMPUTE` into GMP decimal arithmetic, so the hot path sticks to
`COMP-5` binary fields and `ADD`. At 126,000 users it edges out the Java NIO entry (125,000) and the Rust io_uring
one (120,000).

**TeX** ([tex-luatex](twelve-dollar/tex-luatex-unorig-username)). The server is an IniTeX job,
`luatex --ini server.tex`, that never reaches `\end`. TeX's main control loop is the event loop, a tail-recursive
`\serve` macro, and every JSON body is the expansion of a macro such as `\feed` or `\liked`. User text never passes
through TeX's tokenizer, so there is no TeX injection. Nothing is typeset; the DVI file stays empty forever.

**Octave** ([octave-sockets](twelve-dollar/octave-sockets-unorig-username)). The MATLAB clone answers the API from
`server.m`, with a small C++ extension for epoll and SQLite that knows nothing about HTTP. Where Octave does the work,
it does it with arrays: base64url is `[65536 256 1] * reshape(b, 3, [])`, and counting UTF-8 characters is
`sum(bitand(double(b), 192) != 128)`.

**Zsh** ([zsh-ztcp](twelve-dollar/zsh-ztcp-unorig-username)). One zsh process listens with `ztcp`, waits with
`zselect`, and computes HMAC-SHA256 in `$(( ))` shell arithmetic, about 2 ms per token on a laptop core. SQLite comes
in through a zsh module of about 140 lines of C, compiled into a zsh 5.9 built from source. In the entry's own words: "The shell that
came with your login prompt now serves a JSON API. Nobody asked for this."

**Prolog** ([prolog-swipl](twelve-dollar/prolog-swipl-unorig-username)). Every route is a clause of `route/4`,
request JSON is parsed by a strict DCG, and the main loop is `repeat, turn, fail`, so each turn's garbage is dropped
by backtracking instead of the garbage collector. The hand-written loop served 34,000 req/s against 5,100 for
SWI-Prolog's own threaded HTTP server on one CPU.

**Tcl** ([tcl-tclsh](twelve-dollar/tcl-tclsh-unorig-username)). SQLite began as a Tcl extension, so this one takes it
home: plain `tclsh8.6` and `package require sqlite3`. Channels are binary and SQLite builds every response body, so
Tcl never decodes or re-encodes a byte of UTF-8.

## Running an entry

The entries are not standalone: each expects its challenge's harness (schema, seed data, test suite, load
generator). To run one, drop it into a clone of the upstream repo's `submissions/` directory and use that repo's
scripts. For a $12 entry:

```bash
git clone https://github.com/arjaythedev/twelve-dollar-server-challenge
cd twelve-dollar-server-challenge
cp -R ../server-challenges/twelve-dollar/c-iouring-unorig-username submissions/
bash seed/make-seed.sh                                     # needs node >= 18 and sqlite3
sudo bash submissions/c-iouring-unorig-username/install.sh # once, as root, on Ubuntu 24.04
bash test/run.sh submissions/c-iouring-unorig-username     # needs curl, jq, openssl; builds, starts, runs the 42 checks
```

The other two work the same way, with Postgres:

- **Million Users:** `bash seed/make-seed.sh` needs Postgres 16 or newer, `psql` and node 18 or newer;
  `test/run.sh` needs `curl`, `jq` and `openssl`, and reads the usual `PGHOST`/`PGUSER`/`PGPASSWORD` variables.
- **Multicore:** `bash seed/make-seed.sh --dev` builds a 2% seed and needs Go 1.27 or newer, Postgres and `psql`;
  `test/run.sh` also builds the conformance suite with Go, and needs `psql` and `curl`.

`test/run.sh` takes any folder name, so the shorter names here work as they are; upstream's convention is
`<language>-<framework>-<github-username>`. To load test, the $12 repo's quick start uses k6
(`k6 run -e VUS=1000 bench/load.js`); Million Users and Multicore document their load generators in
`bench/README.md`.

## How this repo is put together

- **Provenance.** Each entry was extracted with `git archive` from upstream `main` and copied byte for byte.
  [`entries.json`](entries.json) records, per entry, the upstream commit, path and git tree hash, every PR of mine that
  touched it, and the board result with the date it was read.
- **Directory names.** The $12 entries keep their upstream names (`c-iouring-unorig-username`) because three of
  them (lua-neovim, prolog-swipl, zsh-ztcp) name their own directory in their README, and the entries are not edited.
  No Million Users or Multicore file names its own directory, so those drop the suffix; their READMEs still mention
  sibling entries by upstream name.
- **CI** ([`.github/workflows/build.yml`](.github/workflows/build.yml)). Every entry is built on `ubuntu-24.04`, the
  OS of all three benchmark boxes, the way upstream CI does it: `sudo bash <entry>/install.sh`, then
  `bash <entry>/build.sh` as the normal user. A docs job runs [`scripts/check_docs.py`](scripts/check_docs.py): every
  relative link in this README resolves, every entry directory is in `entries.json` and the other way round, and each
  directory's committed git tree hash still equals upstream's, so a stray edit to an entry fails the build.

```bash
python3 scripts/check_docs.py && python3 -m unittest discover -s scripts
```

## Credits and license

The three challenges, their specs, harnesses and leaderboards are by [arjaythedev](https://github.com/arjaythedev)
and the challenge contributors, under the MIT license:
[million-users-challenge](https://github.com/arjaythedev/million-users-challenge),
[multicore-server-challenge](https://github.com/arjaythedev/multicore-server-challenge),
[twelve-dollar-server-challenge](https://github.com/arjaythedev/twelve-dollar-server-challenge). Ideas and code
borrowed from other entrants are credited in each entry's README. See [NOTICE](NOTICE).

My entries and the rest of this repo are MIT licensed: see [LICENSE](LICENSE).
