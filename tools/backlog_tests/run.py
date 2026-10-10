#!/usr/bin/env python3
"""Standard-library runner for the backlog.py tests, so they need no pytest install.

The test files are written against the pytest names they use (raises, mark.parametrize, mark.skipif, tmp_path);
this runner supplies exactly those and nothing else. Silent on pass, verbose on fail, and the verdict is the
last line. Usage: python3 tools/backlog_tests/run.py
"""
import contextlib
import importlib
import inspect
import os
import re
import shutil
import sys
import tempfile
import traceback
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
# Tests run against the shipped example settings, never a machine's own config.
os.environ["BACKLOG_CONFIG"] = str(HERE.parent.parent / "config" / "backlog.example.json")


class Skip(Exception):
    pass


@contextlib.contextmanager
def raises(exc, match=None):
    try:
        yield
    except exc as e:
        if match and not re.search(match, str(e)):
            raise AssertionError(f"{exc.__name__} message {str(e)!r} does not match {match!r}")
    else:
        raise AssertionError(f"expected {exc.__name__} was not raised")


def parametrize(names, values):
    names = [n.strip() for n in names.split(",")]

    def deco(fn):
        fn.cases = [(v if len(names) > 1 else (v,)) for v in values]
        fn.case_names = names
        return fn
    return deco


def skipif(cond, reason=""):
    def deco(fn):
        if cond:
            fn.skip_reason = reason
        return fn
    return deco


shim = types.ModuleType("pytest")
shim.raises = raises
shim.mark = types.SimpleNamespace(parametrize=parametrize, skipif=skipif)
sys.modules["pytest"] = shim


def run_case(fn, kwargs):
    tmp = None
    params = inspect.signature(fn).parameters
    if "tmp_path" in params:
        tmp = Path(tempfile.mkdtemp(prefix="backlog-test-"))
        kwargs["tmp_path"] = tmp
    try:
        fn(**kwargs)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def main():
    passed = failed = skipped = 0
    for path in sorted(HERE.glob("test_*.py")):
        mod = importlib.import_module(path.stem)
        for name, fn in inspect.getmembers(mod, inspect.isfunction):
            if not name.startswith("test_") or fn.__module__ != mod.__name__:
                continue
            if getattr(fn, "skip_reason", None) is not None:
                skipped += 1
                continue
            cases = getattr(fn, "cases", [()])
            for case in cases:
                kwargs = dict(zip(getattr(fn, "case_names", []), case))
                try:
                    run_case(fn, kwargs)
                    passed += 1
                except Exception:
                    failed += 1
                    print(f"FAIL: {path.name}::{name} {kwargs or ''}")
                    traceback.print_exc()
    print(f"backlog tests: {passed} passed, {failed} failed, {skipped} skipped")
    print("BACKLOG TESTS PASS" if not failed and passed else "BACKLOG TESTS FAIL")
    return 1 if failed or not passed else 0


if __name__ == "__main__":
    sys.exit(main())
