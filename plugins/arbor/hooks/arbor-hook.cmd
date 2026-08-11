: << 'CMDBLOCK'
@echo off
rem Cross-platform launcher for Arbor hooks.
rem
rem cmd.exe runs the batch block above CMDBLOCK; POSIX shells skip that block
rem because `:` swallows it as a here-document and run the shell section below.
rem The file is pinned to LF by .gitattributes so both readers see one form.
rem
rem Interpreters are selected by running them, not by looking them up on PATH:
rem on Windows without Python installed, `python3` resolves to a Microsoft Store
rem stub that exists on PATH and fails on execution.
rem
rem With no working interpreter this exits 0 and prints nothing. A missing
rem interpreter must degrade to "no context injected", never to a hook failure.
rem
rem Usage: arbor-hook.cmd <hook-event>

setlocal
set "ARBOR_SCRIPT=%~dp0..\skills\arbor\scripts\arbor.py"

if not "%ARBOR_PYTHON%"=="" (
    "%ARBOR_PYTHON%" -c "" >nul 2>nul
    if not errorlevel 1 (
        "%ARBOR_PYTHON%" "%ARBOR_SCRIPT%" hook %1
        exit /b %ERRORLEVEL%
    )
)

python -c "" >nul 2>nul
if not errorlevel 1 (
    python "%ARBOR_SCRIPT%" hook %1
    exit /b %ERRORLEVEL%
)

py -3 -c "" >nul 2>nul
if not errorlevel 1 (
    py -3 "%ARBOR_SCRIPT%" hook %1
    exit /b %ERRORLEVEL%
)

exit /b 0
CMDBLOCK

ARBOR_DIR="$(cd "$(dirname "$0")" && pwd)"
ARBOR_SCRIPT="$ARBOR_DIR/../skills/arbor/scripts/arbor.py"

for arbor_candidate in "$ARBOR_PYTHON" python3 python; do
    [ -n "$arbor_candidate" ] || continue
    "$arbor_candidate" -c "" >/dev/null 2>&1 || continue
    exec "$arbor_candidate" "$ARBOR_SCRIPT" hook "$1"
done

exit 0
