# Test results

Written by `tests/run_tests.py --tool 1273382`. The tool was built from
commit 1273382, not from this checkout.

- Oracle: Python 3.13.17 `tarfile`, and the model of the format in `tests/run_tests.py`, which tarfile checks on every unmutated archive both read
- Lean: Lean (version 4.35.0, x86_64-unknown-linux-gnu, commit eb6cafb7290e8bd5f2937522d8d804f58f02bafc, Release)
- System tar: tar (GNU tar) 1.35
- Seed: 20261025
- Inputs: 10059
- Archives: 59 fixed, 10000 random
- Random archives: 10000, 5000 of them mutated; the model reads 4732, and tarfile agrees with it on all 3134 unmutated ones both read
- Checks run: 23269
- Archive A entries compared (list and manifest): 23
- Manifest outcome on archive A: 10 extracted, 9 rejected by the path gate, 4 skipped as non-regular
- Files written by the Lean `create` command and read back by Python: 3
- Broken inputs that must fail with exit code 1: truncated archive, random garbage, corrupted checksum
- Archives in formats the pilot does not read, which must fail with exit code 1 under `list` and `manifest`: 35
- Archives in other formats it reads, compared with tarfile under `list` and `manifest`: 19
- Failures: 10377

How the fixed archives are compared with tarfile. tarfile drops the `/` at the
end of a directory name, so directory names in `list` and names in `SKIP` lines
are compared without it. tarfile also reads an entry with typeflag NUL and a
name ending in `/` as a directory, typeflag 5, so for the readable archives the
tool's typeflag 0 on such an entry is read as 5. Every other typeflag is
compared as printed. The random archives are compared with the model, and the
model with tarfile as `tarfile_agrees` in `tests/run_tests.py` says.

## Failures by check

| Check | Run | Failed |
|-------|-----|--------|
| list-exit | 1 | 0 |
| list-match | 1 | 0 |
| manifest-exit | 1 | 0 |
| manifest-match | 1 | 0 |
| manifest-dest | 7 | 0 |
| manifest-dest-refused | 6 | 0 |
| create-exit | 1 | 0 |
| create-readback | 1 | 0 |
| create-refuses-long-name | 1 | 0 |
| truncated-fails | 1 | 0 |
| garbage-fails | 1 | 0 |
| bad-checksum-fails | 1 | 0 |
| usage | 4 | 0 |
| unsupported-fails (list) | 35 | 29 |
| unsupported-fails (manifest) | 35 | 29 |
| readable-list | 19 | 6 |
| readable-manifest | 19 | 8 |
| random list | 10000 | 5184 |
| random manifest | 10000 | 5121 |
| random model agrees with tarfile | 3134 | 0 |

## Failures

- unsupported-fails: GNU long name entry (typeflag L) (list): rc=0 out='././@LongLink\t127\t76\nd/nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn\t1\t48\n'
- unsupported-fails: GNU long name entry (typeflag L) (manifest): rc=0 out='SKIP\t././@LongLink\t76\nOK\tout/d/nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn\t1\t120\n'
- unsupported-fails: GNU long link entry (typeflag K) (list): rc=0 out='l.txt\t1\t75\n'
- unsupported-fails: GNU long link entry (typeflag K) (manifest): rc=0 out='SKIP\tl.txt\t75\n'
- unsupported-fails: pax long path (typeflag x) (list): rc=0 out='././@PaxHeader\t136\t120\nd/nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn\t1\t48\n'
- unsupported-fails: pax long path (typeflag x) (manifest): rc=0 out='SKIP\t././@PaxHeader\t120\nOK\tout/d/nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn\t1\t120\n'
- unsupported-fails: pax path override (list): rc=0 out='././@PaxHeader\t27\t120\nsafe.txt\t1\t48\n'
- unsupported-fails: pax path override (manifest): rc=0 out='SKIP\t././@PaxHeader\t120\nOK\tout/safe.txt\t1\t120\n'
- unsupported-fails: pax path override that climbs out (list): rc=0 out='././@PaxHeader\t27\t120\nsafe.txt\t1\t48\n'
- unsupported-fails: pax path override that climbs out (manifest): rc=0 out='SKIP\t././@PaxHeader\t120\nOK\tout/safe.txt\t1\t120\n'
- unsupported-fails: pax non-ASCII name (list): rc=0 out='././@PaxHeader\t24\t120\ncaf?/notes.txt\t1\t48\n'
- unsupported-fails: pax non-ASCII name (manifest): rc=0 out='SKIP\t././@PaxHeader\t120\nOK\tout/caf?/notes.txt\t1\t120\n'
- unsupported-fails: pax global header (typeflag g) (list): rc=0 out='././@PaxHeader\t18\t103\ng.txt\t1\t48\n'
- unsupported-fails: pax global header (typeflag g) (manifest): rc=0 out='SKIP\t././@PaxHeader\t103\nOK\tout/g.txt\t1\t103\n'
- unsupported-fails: split name, invalid UTF-8 in the prefix field only (list): rc=0 out='qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq/file.txt\t1\t48\n'
- unsupported-fails: split name, invalid UTF-8 in the prefix field only (manifest): rc=0 out='OK\tout/qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq/file.txt\t1\t120\n'
- unsupported-fails: split name, invalid UTF-8 in the name field only (list): rc=0 out='pppppppppppppppppppppppppppppp/\t1\t48\n'
- unsupported-fails: split name, invalid UTF-8 in the name field only (manifest): rc=0 out='OK\tout/pppppppppppppppppppppppppppppp\t1\t120\n'
- unsupported-fails: split name, invalid UTF-8 in both fields (list): rc=0 out='\t1\t48\n'
- unsupported-fails: split name, invalid UTF-8 in both fields (manifest): rc=0 out='REJECT\t\n'
- unsupported-fails: short name, invalid UTF-8 (list): rc=0 out='\t1\t48\n'
- unsupported-fails: short name, invalid UTF-8 (manifest): rc=0 out='REJECT\t\n'
- unsupported-fails: GNU header with access and change times (incremental dump) (list): rc=0 out='15267276047/a.txt\t1\t48\n'
- unsupported-fails: GNU header with access and change times (incremental dump) (manifest): rc=0 out='OK\tout/15267276047/a.txt\t1\t120\n'
- unsupported-fails: GNU header with a sparse map (list): rc=0 out='a.txt\t1\t48\n'
- unsupported-fails: GNU header with a sparse map (manifest): rc=0 out='OK\tout/a.txt\t1\t120\n'
- unsupported-fails: unknown typeflag D (list): rc=0 out='u.txt\t1\t68\n'
- unsupported-fails: unknown typeflag D (manifest): rc=0 out='SKIP\tu.txt\t68\n'
- unsupported-fails: unknown typeflag M (list): rc=0 out='u.txt\t1\t77\n'
- unsupported-fails: unknown typeflag M (manifest): rc=0 out='SKIP\tu.txt\t77\n'
- unsupported-fails: unknown typeflag N (list): rc=0 out='u.txt\t1\t78\n'
- unsupported-fails: unknown typeflag N (manifest): rc=0 out='SKIP\tu.txt\t78\n'
- unsupported-fails: unknown typeflag S (list): rc=0 out='u.txt\t1\t83\n'
- unsupported-fails: unknown typeflag S (manifest): rc=0 out='SKIP\tu.txt\t83\n'
- unsupported-fails: unknown typeflag V (list): rc=0 out='u.txt\t1\t86\n'
- unsupported-fails: unknown typeflag V (manifest): rc=0 out='SKIP\tu.txt\t86\n'
- unsupported-fails: unknown typeflag A (list): rc=0 out='u.txt\t1\t65\n'
- unsupported-fails: unknown typeflag A (manifest): rc=0 out='SKIP\tu.txt\t65\n'
- unsupported-fails: unknown typeflag Z (list): rc=0 out='u.txt\t1\t90\n'
- unsupported-fails: unknown typeflag Z (manifest): rc=0 out='SKIP\tu.txt\t90\n'
- unsupported-fails: ustar magic with a GNU version (list): rc=0 out='m.txt\t1\t48\n'
- unsupported-fails: ustar magic with a GNU version (manifest): rc=0 out='OK\tout/m.txt\t1\t120\n'
- unsupported-fails: name ending in / with typeflag b'\x00' and data (list): rc=0 out='d/\t1\t0\n'
- unsupported-fails: name ending in / with typeflag b'\x00' and data (manifest): rc=0 out='OK\tout/d\t1\t120\n'
- unsupported-fails: name ending in / with typeflag b'0' and data (list): rc=0 out='e/\t1\t48\n'
- unsupported-fails: name ending in / with typeflag b'0' and data (manifest): rc=0 out='OK\tout/e\t1\t120\n'
- unsupported-fails: size field of spaces (list): rc=0 out='f\t0\t48\n'
- unsupported-fails: size field of spaces (manifest): rc=0 out='OK\tout/f\t0\t0\n'
- unsupported-fails: GNU magic with version 00 (list): rc=0 out='a.txt\t1\t48\n'
- unsupported-fails: GNU magic with version 00 (manifest): rc=0 out='OK\tout/a.txt\t1\t120\n'
- unsupported-fails: GNU header with the last byte of the prefix area set (list): rc=0 out='a.txt\t1\t48\n'
- unsupported-fails: GNU header with the last byte of the prefix area set (manifest): rc=0 out='OK\tout/a.txt\t1\t120\n'
- unsupported-fails: system tar, default format, long name (list): rc=0 out='d/\t0\t53\n././@LongLink\t127\t76\nd/nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn\t1\t48\n'
- unsupported-fails: system tar, default format, long name (manifest): rc=0 out='SKIP\td/\t53\nSKIP\t././@LongLink\t76\nOK\tout/d/nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn\t1\t120\n'
- unsupported-fails: system tar, incremental dump (times in bytes 345 to 368) (list): rc=0 out='15267733331/a.txt\t3\t48\n'
- unsupported-fails: system tar, incremental dump (times in bytes 345 to 368) (manifest): rc=0 out='OK\tout/15267733331/a.txt\t3\t219\n'
- unsupported-fails: system tar, sparse file (typeflag S, map in bytes 386 to 494) (list): rc=0 out='sparse\t3\t83\n'
- unsupported-fails: system tar, sparse file (typeflag S, map in bytes 386 to 494) (manifest): rc=0 out='SKIP\tsparse\t83\n'
- readable-manifest: contiguous file (typeflag 7): rc=0 lean=['SKIP\tcontig.bin\t55'] expected=['OK\tout/contig.bin\t10\t1104']
- readable-manifest: names ending in / with typeflags NUL and 0, read as directories: rc=0 lean=['OK\tout/olddir\t0\t0', 'OK\tout/olddir/f.txt\t3\t319', 'OK\tout/slashdir\t0\t0'] expected=['SKIP\tolddir\t53', 'OK\tout/olddir/f.txt\t3\t319', 'SKIP\tslashdir\t48']
- readable-list: typeflag 1 with a size field, then two files: rc=0 lean=[('node', 1024, 49), ('b.txt', 1, 48)] expected=[('node', 0, 49), ('hidden.txt', 6, 48), ('b.txt', 1, 48)]
- readable-manifest: typeflag 1 with a size field, then two files: rc=0 lean=['SKIP\tnode\t49', 'OK\tout/b.txt\t1\t98'] expected=['SKIP\tnode\t49', 'OK\tout/hidden.txt\t6\t620', 'OK\tout/b.txt\t1\t98']
- readable-list: typeflag 2 with a size field, then two files: rc=0 lean=[('node', 1024, 50), ('b.txt', 1, 48)] expected=[('node', 0, 50), ('hidden.txt', 6, 48), ('b.txt', 1, 48)]
- readable-manifest: typeflag 2 with a size field, then two files: rc=0 lean=['SKIP\tnode\t50', 'OK\tout/b.txt\t1\t98'] expected=['SKIP\tnode\t50', 'OK\tout/hidden.txt\t6\t620', 'OK\tout/b.txt\t1\t98']
- readable-list: typeflag 3 with a size field, then two files: rc=0 lean=[('node', 1024, 51), ('b.txt', 1, 48)] expected=[('node', 0, 51), ('hidden.txt', 6, 48), ('b.txt', 1, 48)]
- readable-manifest: typeflag 3 with a size field, then two files: rc=0 lean=['SKIP\tnode\t51', 'OK\tout/b.txt\t1\t98'] expected=['SKIP\tnode\t51', 'OK\tout/hidden.txt\t6\t620', 'OK\tout/b.txt\t1\t98']
- readable-list: typeflag 4 with a size field, then two files: rc=0 lean=[('node', 1024, 52), ('b.txt', 1, 48)] expected=[('node', 0, 52), ('hidden.txt', 6, 48), ('b.txt', 1, 48)]
- readable-manifest: typeflag 4 with a size field, then two files: rc=0 lean=['SKIP\tnode\t52', 'OK\tout/b.txt\t1\t98'] expected=['SKIP\tnode\t52', 'OK\tout/hidden.txt\t6\t620', 'OK\tout/b.txt\t1\t98']
- readable-list: typeflag 5 with a size field, then two files: rc=0 lean=[('node', 1024, 53), ('b.txt', 1, 48)] expected=[('node', 0, 53), ('hidden.txt', 6, 48), ('b.txt', 1, 48)]
- readable-manifest: typeflag 5 with a size field, then two files: rc=0 lean=['SKIP\tnode\t53', 'OK\tout/b.txt\t1\t98'] expected=['SKIP\tnode\t53', 'OK\tout/hidden.txt\t6\t620', 'OK\tout/b.txt\t1\t98']
- readable-list: typeflag 6 with a size field, then two files: rc=0 lean=[('node', 1024, 54), ('b.txt', 1, 48)] expected=[('node', 0, 54), ('hidden.txt', 6, 48), ('b.txt', 1, 48)]
- readable-manifest: typeflag 6 with a size field, then two files: rc=0 lean=['SKIP\tnode\t54', 'OK\tout/b.txt\t1\t98'] expected=['SKIP\tnode\t54', 'OK\tout/hidden.txt\t6\t620', 'OK\tout/b.txt\t1\t98']
- random 0 list: seed=20261025 rc=0 want_rc=1 got=['/nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn/\\x09\t0\t50', '\\x7f\t2436\t48', './x.txt\t1024\t54'] want=[]
- random 0 manifest: seed=20261025 rc=0 want_rc=1 got=['SKIP\t/nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn/\\x09\t50', 'REJECT\t\\x7f', 'SKIP\t./x.txt\t54'] want=[]
- random 2 list: seed=20261025 rc=1 want_rc=0 got=[] want=['/é/..a/..a/../\t0\t53', '日本/日本\t2431\t0', '//a b/\t0\t53']
- random 2 manifest: seed=20261025 rc=1 want_rc=0 got=[] want=['SKIP\t/é/..a/..a/../\t53', 'OK\tout/日本/日本\t2431\t315641', 'SKIP\t//a b/\t53']
- random 3 list: seed=20261025 rc=0 want_rc=1 got=['././@PaxHeader\t135\t120', 'pppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppp\t0\t52', '././@PaxHeader\t19\t120'] want=[]
- random 3 manifest: seed=20261025 rc=0 want_rc=1 got=['SKIP\t././@PaxHeader\t120', 'SKIP\tpppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppp\t52', 'SKIP\t././@PaxHeader\t120'] want=[]
- random 4 list: seed=20261025 rc=0 want_rc=0 got=['\\x85\t0\t50', '/a b/a/-\t513\t0', '/\\x85/é\t1\t52'] want=['\\x85\t0\t50', '/a b/a/-\t513\t0', '/\\x85/é\t0\t52']
- random 9 list: seed=20261025 rc=0 want_rc=1 got=['..a\t1496\t48', '././@LongLink\t127\t76', 'pppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppp\t2709\t55'] want=[]
- random 9 manifest: seed=20261025 rc=0 want_rc=1 got=['OK\tout/..a\t1496\t193800', 'SKIP\t././@LongLink\t76', 'SKIP\tpppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppppp\t55'] want=[]
- random 10 list: seed=20261025 rc=0 want_rc=0 got=['a/\\\\/x.txt\t0\t0', 'a b/\\\\/a\t1024\t51'] want=['a/\\\\/x.txt\t0\t0', 'a b/\\\\/a\t0\t51', '../\\u2028\t0\t49']
- random 10 manifest: seed=20261025 rc=0 want_rc=0 got=['OK\ta/\\/x.txt\t0\t0', 'SKIP\ta b/\\\\/a\t51'] want=['OK\ta/\\/x.txt\t0\t0', 'SKIP\ta b/\\\\/a\t51', 'SKIP\t../\\u2028\t49']
- random 12 list: seed=20261025 rc=0 want_rc=1 got=['././@PaxHeader\t80\t120', 'a b/nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn/:/?/\t0\t53', 'ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff.txt\t513\t48'] want=[]
- random 12 manifest: seed=20261025 rc=0 want_rc=1 got=['SKIP\t././@PaxHeader\t120', 'SKIP\ta b/nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn/:/?/\t53', 'OK\t/ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff.txt\t513\t63981'] want=[]
- random 15 list: seed=20261025 rc=0 want_rc=1 got=['/..a/x.txt\t513\t48', '日本/\\u2028/\\\\\t0\t55', '\\x09/x.txt/-/\\x09\t0\t49'] want=[]
- random 15 manifest: seed=20261025 rc=0 want_rc=1 got=['REJECT\t/..a/x.txt', 'SKIP\t日本/\\u2028/\\\\\t55', 'SKIP\t\\x09/x.txt/-/\\x09\t49'] want=[]
- random 16 list: seed=20261025 rc=0 want_rc=1 got=['\\x0a\t0\t52', '/\\\\/\\\\\t0\t54', 'a b/..a/../.\t0\t55'] want=[]
- random 16 manifest: seed=20261025 rc=0 want_rc=1 got=['SKIP\t\\x0a\t52', 'SKIP\t/\\\\/\\\\\t54', 'SKIP\ta b/..a/../.\t55'] want=[]
- random 20 list: seed=20261025 rc=0 want_rc=1 got=['b/nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn/:/\t0\t53', '..\t0\t54', '././@PaxHeader\t198\t120'] want=[]
- random 20 manifest: seed=20261025 rc=0 want_rc=1 got=['SKIP\tb/nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn/:/\t53', 'SKIP\t..\t54', 'SKIP\t././@PaxHeader\t120'] want=[]
- random 23 manifest: seed=20261025 rc=0 want_rc=0 got=['SKIP\t\\x85\t54', 'SKIP\ta\t52', 'REJECT\t\\x7f/'] want=['SKIP\t\\x85\t54', 'SKIP\ta\t52', 'SKIP\t\\x7f/\t48']

This lists every failure of a fixed case, and the first 20 of the
10305 failures of random cases. The script prints them all as it runs.
