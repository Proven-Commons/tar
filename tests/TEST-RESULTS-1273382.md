# Test results

Run by `tests/run_tests.py --tool 1273382` against Python's `tarfile` module.
The tool was built from commit 1273382, not from this checkout. The axiom
check reads this checkout's proofs, not the tool, so it is left out.
Lean: Lean (version 4.35.0, x86_64-unknown-linux-gnu, commit eb6cafb7290e8bd5f2937522d8d804f58f02bafc, Release). Python: 3.13.17. System tar: tar (GNU tar) 1.35.

- Checks run: 107, all on the tool
- Failures: 68
- Archive A entries compared (list and manifest): 23
- Manifest outcome on archive A: 10 extracted, 9 rejected by the path gate, 4 skipped as non-regular
- Files written by the Lean `create` command and read back by Python: 3
- Broken inputs that must fail with exit code 1: truncated archive, random garbage, corrupted checksum
- Archives in formats the pilot does not read, which must fail with exit code 1 under `list` and `manifest`: 29
- Archives in other formats it reads, compared with tarfile under `list` and `manifest`: 13

How the output is compared with tarfile. tarfile drops the `/` at the end of a
directory name, so directory names in `list` and names in `SKIP` lines are
compared without it. tarfile also reads an entry with typeflag NUL and a name
ending in `/` as a directory, typeflag 5, so for the readable archives the
tool's typeflag 0 on such an entry is read as 5. Every other typeflag is
compared as printed.

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
- unsupported-fails: system tar, default format, long name (list): rc=0 out='d/\t0\t53\n././@LongLink\t127\t76\nd/nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn\t1\t48\n'
- unsupported-fails: system tar, default format, long name (manifest): rc=0 out='SKIP\td/\t53\nSKIP\t././@LongLink\t76\nOK\tout/d/nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn\t1\t120\n'
- unsupported-fails: system tar, incremental dump (times in bytes 345 to 368) (list): rc=0 out='15267725440/a.txt\t3\t48\n'
- unsupported-fails: system tar, incremental dump (times in bytes 345 to 368) (manifest): rc=0 out='OK\tout/15267725440/a.txt\t3\t219\n'
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
