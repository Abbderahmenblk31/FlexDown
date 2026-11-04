# Full Evaluation Report

## Pytest: PASS
```
...........                                                              [100%]
11 passed in 107.27s (0:01:47)

```

## Flake8: PASS
```

```

## Mypy: PASS
```
flexdown\core\bridge_server.py:100: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
flexdown\core\bridge_server.py:125: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
flexdown\ui\widgets\progress_widget.py:34: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
flexdown\ui\widgets\progress_widget.py:35: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
flexdown\ui\widgets\progress_widget.py:36: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
flexdown\core\scheduler.py:26: note: By default the bodies of untyped functions are not checked, consider using --check-untyped-defs  [annotation-unchecked]
Success: no issues found in 31 source files

```

## Bandit: PASS
```
Run started:2026-10-18 19:21:50.087511+00:00

Test results:
	No issues identified.

Code scanned:
	Total lines of code: 6251
	Total lines skipped (#nosec): 0
	Total potential issues skipped due to specifically being disabled (e.g., #nosec BXXX): 3

Run metrics:
	Total issues (by severity):
		Undefined: 0
		Low: 35
		Medium: 0
		High: 0
	Total issues (by confidence):
		Undefined: 0
		Low: 0
		Medium: 2
		High: 33
Files skipped (0):
[main]	INFO	profile include tests: None
[main]	INFO	profile exclude tests: None
[main]	INFO	cli include tests: None
[main]	INFO	cli exclude tests: None
[main]	INFO	running on Python 3.13.6

```

## Pip-audit: PASS
```
No known vulnerabilities found

```

## Download-Performance: PASS
```
Downloaded 10.00 MiB in 21.40s -> 0.47 MiB/s
```

**Overall grade:** A (6/6 passed)
