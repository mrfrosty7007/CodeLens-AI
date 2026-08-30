OutFile "dist\test-package.exe"
Section "Main"
    SetOutPath "$INSTDIR"
    File "build\package\app.py"
    File "build\package\CodeLensAI.exe"
    File /r "build\package\_internal\*.*"
    File /r "build\package\runtime\*.*"
SectionEnd
