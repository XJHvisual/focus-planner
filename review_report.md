# Review Report: test_*.py and build_exe.py

## 1. test_config_loading.py

### Verdict: Works ✅ (with issues)

**Runs?** ✅ Yes (with Python 3.12 from Microsoft Store; fails on uv-managed 3.11 due to SRE mismatch)

**Has assertions?** ⚠️ No `assert` statements, but prints [PASS]/[FAIL] tags. It's a "script-style" test, not a unittest/pytest test. Functional but not CI-friendly (no exception on failure).

**Issues:**
1. **No `unittest.TestCase` or `pytest` framework** — it's just a script that prints status. A failure doesn't raise an exception, so it would silently pass in CI.
2. **Fragile regex** — the `re.sub(r'[-_](pc|x64|x86|win64.*|win32.*)$', ...)` pattern doesn't handle `valorant-win64-shipping` correctly on its own (it relies on the mapping table, not the regex). The regex only catches suffixes at the very end, but `win64-shipping` has `-shi...` after it.
3. **`_load_mapping_config` is called at module level** (line 69), not guarded by `if __name__ == "__main__":`. Importing this file would trigger execution as a side effect.
4. **`import re` is inside the for-loop** (line 57) — inefficient, should be at the top.

### Passes: All 3 test cases pass ✅

---

## 2. test_improvement1.py

### Verdict: ⚠️ Has bugs — 2 of 8 tests FAIL

**Runs?** ✅ Yes (with Python 3.12)

**Has assertions?** ⚠️ Same as above — prints [PASS]/[FAIL] but uses `sys.exit(1)` on failure, which is slightly better.

**Issues:**
1. **FAILING TESTS (#1)** — The `test_process_mapping` method does NOT implement title-based fallback mapping. When `process_name == "unknown"`, it only checks the `process_name_mapping` dict (which has no "unknown" key), so it returns "unknown" unchanged. The real `BuiltinTracker._get_foreground()` has a title-mapping fallback (lines 2393-2406 of main.py) that the mock doesn't replicate.
2. **FAILING TESTS (#2)** — Test cases for `("unknown", "鸣潮", "鸣潮")` and `("unknown", "AppTimeTracker V2", "应用时间追踪器")` both fail because the mock's `test_process_mapping` doesn't check `_title_map` when process_name is "unknown".
3. **`import re` is inside the class method** (line 41) — inefficient, should be at the top.
4. **Mock is incomplete** — it only tests `process_name_mapping` but not the title-to-app-name fallback logic that exists in the real code.
5. **Test expectations may be wrong** (or the mock is correct and the real code's title mapping is the "improvement" being tested). Either way, the test currently fails.

### 2 of 8 tests FAIL ❌

---

## 3. build_exe.py

### Verdict: ⚠️ Issues found

**Runs?** Likely yes (pure Python, no issues spotted at parse time)

**Issues:**
1. **Hardcoded icon path** — `icon_path = os.path.join(script_dir, "focus_planner.ico")` — not hardcoded in absolute terms, but assumes the icon file always exists in the same directory. If `focus_planner.ico` is missing, it will crash PyInstaller. (Currently exists ✅)
2. **No error handling** — `subprocess.check_call` will raise `CalledProcessError` if PyInstaller fails, but there's no try/except, message, or guidance.
3. **No `--noconfirm` flag** — PyInstaller will prompt to overwrite existing build/spec files if they exist, which blocks headless/automated builds.
4. **`--add-data` uses `os.pathsep`** as separator — correct for Windows (uses `;`). ✅
5. **`--clean` flag present** — good. ✅
6. **No version/icon specification in the spec file** — acceptable for simple builds.
7. **Depends on `data/` directory existing** at build time — it's copied into the bundle. Works if data dir exists ✅.

---

## 4. Cross-Cutting Issues

| Issue | Severity | File(s) |
|-------|----------|---------|
| No unittest/pytest framework | Low | Both test files |
| `import re` inside loop/function | Low | test_config_loading.py:57, test_improvement1.py:41 |
| Module-level side effect on import | Low | test_config_loading.py:69 |
| Mock missing title-mapping fallback | Medium | test_improvement1.py (2 failing tests) |
| build_exe.py: missing `--noconfirm` | Low-Medium | build_exe.py:17 |
| build_exe.py: no try/except | Low | build_exe.py:30 |
| Broken Python environment (uv-managed 3.11 SRE mismatch) | High | Environment issue, all .py files |

---

## Summary

- **test_config_loading.py**: All 3 tests pass. No `unittest` framework, module-level side effect on import, `import re` in loop.
- **test_improvement1.py**: 2 of 8 tests FAIL — the mock is missing title-mapping fallback logic that exists in the real `BuiltinTracker._get_foreground()`. The test expectations (title-based mapping) are correct but the mock implementation doesn't support them.
- **build_exe.py**: Functional but fragile — missing `--noconfirm` for PyInstaller, no error handling, assumes icon file exists.
- **Environment**: uv-managed Python 3.11 is broken (SRE module mismatch). Python 3.12 (Microsoft Store) works.
