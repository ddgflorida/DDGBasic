@echo off
rem Build DDGBasic and upload it to PyPI.
rem Put it in the repository folder (git pull does) and run it from there.
rem Raise __version__ in src\ddgbasic.py first: PyPI refuses a version it already has.
rem twine asks for your PyPI token, unless it is in %USERPROFILE%\.pypirc.
setlocal
cd /d "%~dp0"

git pull || exit /b 1
python src\ddgbasic.py --version

rem Stop before uploading anything if a check or a test fails
python tools\check_builtin_names.py || exit /b 1
python tools\check_dependencies.py || exit /b 1
python tests\run_tests.py || (echo Tests failed: nothing was uploaded. & exit /b 1)

rem Build fresh: old files in dist would be uploaded again
if exist dist rmdir /s /q dist
python -m pip install --upgrade build twine || exit /b 1
python -m build || exit /b 1
python -m twine check dist\* || exit /b 1

python -m twine upload dist\*
