; ==============================================================================
; CodeLens AI - Nullsoft Scriptable Install System (NSIS) Script
; Produces: dist\CodeLensAI-Setup.exe
; Phase H3: Zero-Friction Windows Installer with Bundled Runtime & Ollama AI
; ==============================================================================

!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "LogicLib.nsh"

; ------------------------------------------------------------------------------
; General Definitions
; ------------------------------------------------------------------------------
!define PRODUCT_NAME "CodeLens AI"
!define PRODUCT_VERSION "1.0.0"
!define PRODUCT_PUBLISHER "CodeLens AI"
!define PRODUCT_WEB_SITE "https://github.com/mrfrosty7007/CodeLens-AI"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\CodeLensAI.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKCU"

; Main Executable & Output
!define MAIN_EXECUTABLE "CodeLensAI.exe"
OutFile "dist\CodeLensAI-Setup.exe"

; Default Installation Directory ($LOCALAPPDATA\Programs\CodeLens AI for zero-UAC desktop installation)
InstallDir "$LOCALAPPDATA\Programs\CodeLens AI"
InstallDirRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_DIR_REGKEY}" ""
RequestExecutionLevel user

; Compression
SetCompressor /SOLID zlib
Unicode True

; Visual Interface Customization
!define MUI_ICON "assets\icon.ico"
!define MUI_UNICON "assets\icon.ico"
!define MUI_ABORTWARNING

; ------------------------------------------------------------------------------
; Installer Pages
; ------------------------------------------------------------------------------
!define MUI_WELCOMEPAGE_TITLE "Welcome to CodeLens AI Setup"
!define MUI_WELCOMEPAGE_TEXT "This wizard will guide you through installing CodeLens AI—the zero-friction local AI code intelligence workspace powered by Ollama and Qwen2.5-Coder.$\r$\n$\r$\nClick Next to continue."
!insertmacro MUI_PAGE_WELCOME

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

; Finish Page with Launch Option
!define MUI_FINISHPAGE_RUN "$INSTDIR\${MAIN_EXECUTABLE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch CodeLens AI now"
!define MUI_FINISHPAGE_TEXT "CodeLens AI has been successfully installed on your computer.$\r$\n$\r$\nYour offline AI intelligence workspace (Qwen2.5-Coder 3B) is configured and ready to use."
!insertmacro MUI_PAGE_FINISH

; ------------------------------------------------------------------------------
; Uninstaller Pages
; ------------------------------------------------------------------------------
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Language
!insertmacro MUI_LANGUAGE "English"

; ------------------------------------------------------------------------------
; Installer Section
; ------------------------------------------------------------------------------
Section "MainSection" SEC01
    SetOverwrite on

    ; 1. Copy Application Core Root Files
    DetailPrint "Installing CodeLens AI core files..."
    SetOutPath "$INSTDIR"
    File "build\package\CodeLensAI.exe"
    File "build\package\app.py"
    File "build\package\launcher.py"
    File "build\package\setup_manager.py"
    File "build\package\runtime_manager.py"
    File "build\package\code_runner.py"
    File "build\package\prompts.py"
    File "build\package\styles.css"
    File "build\package\requirements.txt"
    File "build\package\README.md"
    File /nonfatal "build\package\ollama_client.py"
    File /nonfatal "build\package\gemini_client.py"

    ; 2. Copy PyInstaller Dependencies (_internal)
    DetailPrint "Installing native runtime dependencies..."
    SetOutPath "$INSTDIR\_internal"
    File /r "build\package\_internal\*.*"

    ; 3. Copy Application Assets
    DetailPrint "Installing application assets..."
    SetOutPath "$INSTDIR\assets"
    File /r "build\package\assets\*.*"

    ; 4. Install Bundled Python Runtime Explicitly
    DetailPrint "Extracting isolated Python runtime environment..."
    SetOutPath "$INSTDIR"
    File "build\package\runtime.zip"
    
    nsExec::ExecToLog 'powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -Path \"$INSTDIR\runtime.zip\" -DestinationPath \"$INSTDIR\runtime\" -Force; Remove-Item \"$INSTDIR\runtime.zip\" -Force"'

    ; 5. Verify Bundled Runtime Integrity
    DetailPrint "Verifying Python runtime integrity..."
    IfFileExists "$INSTDIR\runtime\Scripts\pythonw.exe" runtime_check_ok runtime_check_missing

runtime_check_missing:
    DetailPrint "CRITICAL ERROR: Python runtime executable ($INSTDIR\runtime\Scripts\pythonw.exe) was not found!"
    MessageBox MB_ICONSTOP|MB_OK "Installation Aborted:$\r$\n$\r$\nThe bundled Python runtime ($INSTDIR\runtime\Scripts\pythonw.exe) is missing or corrupted.$\r$\nPlease ensure sufficient disk space and re-run setup."
    Abort "Missing runtime executable."

runtime_check_ok:
    DetailPrint "Python runtime verified successfully."

    ; 6. Detect and Install Ollama
    DetailPrint "Checking Ollama AI engine..."
    StrCpy $0 "0"

    ; Check standard paths
    IfFileExists "$LOCALAPPDATA\Programs\Ollama\ollama.exe" ollama_found 0
    IfFileExists "$PROGRAMFILES\Ollama\ollama.exe" ollama_found 0
    IfFileExists "$PROGRAMFILES64\Ollama\ollama.exe" ollama_found 0

    ; Check registry uninstall keys
    ReadRegStr $1 HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ollama" "UninstallString"
    StrCmp $1 "" 0 ollama_found
    ReadRegStr $1 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Ollama" "UninstallString"
    StrCmp $1 "" 0 ollama_found

    ; Check PATH
    nsExec::ExecToStack 'cmd /c where ollama'
    Pop $1
    StrCmp $1 "0" ollama_found ollama_install_step

ollama_install_step:
    DetailPrint "Ollama not found on system. Extracting bundled Ollama installer..."
    InitPluginsDir
    SetOutPath "$PLUGINSDIR"
    File "tools\OllamaSetup.exe"

    DetailPrint "Installing Ollama silently..."
    nsExec::ExecToLog '"$PLUGINSDIR\OllamaSetup.exe" /silent'
    Pop $1
    DetailPrint "Ollama installation completed (exit code: $1)."
    Delete "$PLUGINSDIR\OllamaSetup.exe"
    Goto ollama_service_step

ollama_found:
    DetailPrint "Ollama AI engine is already installed."
    Goto ollama_service_step

ollama_service_step:
    ; 7. Start and Wait for Ollama Service
    DetailPrint "Verifying Ollama background service..."
    nsExec::ExecToStack 'powershell -NoProfile -ExecutionPolicy Bypass -Command "if (-not (Get-Process ollama -ErrorAction SilentlyContinue)) { if (Test-Path \"$$env:LOCALAPPDATA\Programs\Ollama\ollama.exe\") { Start-Process \"$$env:LOCALAPPDATA\Programs\Ollama\ollama.exe\" -ArgumentList \"serve\" -WindowStyle Hidden } else { Start-Process \"ollama\" -ArgumentList \"serve\" -WindowStyle Hidden } }"'

    DetailPrint "Waiting for Ollama service to be ready on port 11434..."
    nsExec::ExecToLog 'powershell -NoProfile -ExecutionPolicy Bypass -Command "$$ready = $$false; for ($$i = 0; $$i -lt 30; $$i++) { try { $$r = Invoke-WebRequest -Uri \"http://127.0.0.1:11434/api/tags\" -UseBasicParsing -TimeoutSec 2; if ($$r.StatusCode -eq 200) { $$ready = $$true; break } } catch {}; Start-Sleep -Seconds 1 }; if ($$ready) { Write-Host \"Ollama service is active and responsive.\" } else { Write-Warning \"Ollama service did not respond within 30s. Setup will continue.\" }"'

    ; 8. Download Default Model (qwen2.5-coder:3b)
    DetailPrint "Checking default local AI model (qwen2.5-coder:3b)..."
    nsExec::ExecToLog 'powershell -NoProfile -ExecutionPolicy Bypass -Command "$$env:PATH = \"$$env:LOCALAPPDATA\Programs\Ollama;\" + $$env:PATH; Write-Host \"Checking installed models in Ollama...\"; try { $$tags = Invoke-RestMethod -Uri \"http://127.0.0.1:11434/api/tags\" -TimeoutSec 5; $$m = $$tags.models | Where-Object { $$_.name -like \"*qwen2.5-coder:3b*\" }; if ($$m) { Write-Host \"Model qwen2.5-coder:3b is already installed.\"; exit 0 } } catch {}; Write-Host \"Downloading qwen2.5-coder:3b model (~1.9 GB)... Progress will be shown below:\"; if (Get-Command ollama -ErrorAction SilentlyContinue) { ollama pull qwen2.5-coder:3b } else { try { $$body = @{ name = \"qwen2.5-coder:3b\"; stream = $$false } | ConvertTo-Json; Invoke-RestMethod -Uri \"http://127.0.0.1:11434/api/pull\" -Method Post -Body $$body -ContentType \"application/json\" -TimeoutSec 600; Write-Host \"Model downloaded successfully.\" } catch { Write-Warning \"Model download deferred to launcher: $$_\" } }"'

    ; 9. Shortcuts & Registry
    SetOutPath "$INSTDIR"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\${MAIN_EXECUTABLE}"

    CreateDirectory "$SMPROGRAMS\CodeLens AI"
    CreateShortcut "$SMPROGRAMS\CodeLens AI\CodeLens AI.lnk" "$INSTDIR\${MAIN_EXECUTABLE}" "" "$INSTDIR\assets\icon.ico" 0
    CreateShortcut "$SMPROGRAMS\CodeLens AI\Uninstall CodeLens AI.lnk" "$INSTDIR\Uninstall.exe" "" "$INSTDIR\assets\icon.ico" 0
    CreateShortcut "$DESKTOP\CodeLens AI.lnk" "$INSTDIR\${MAIN_EXECUTABLE}" "" "$INSTDIR\assets\icon.ico" 0

    WriteUninstaller "$INSTDIR\Uninstall.exe"

    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\assets\icon.ico"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegDWORD ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "NoModify" 1
    WriteRegDWORD ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "NoRepair" 1

    ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
    IntFmt $0 "0x%08X" $0
    WriteRegDWORD ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "EstimatedSize" "$0"
SectionEnd

; ------------------------------------------------------------------------------
; Uninstaller Section
; ------------------------------------------------------------------------------
Section Uninstall
    Delete "$DESKTOP\CodeLens AI.lnk"
    Delete "$SMPROGRAMS\CodeLens AI\CodeLens AI.lnk"
    Delete "$SMPROGRAMS\CodeLens AI\Uninstall CodeLens AI.lnk"
    RMDir "$SMPROGRAMS\CodeLens AI"

    Delete "$INSTDIR\${MAIN_EXECUTABLE}"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir /r "$INSTDIR"

    DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
    DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_DIR_REGKEY}"
    SetAutoClose true
SectionEnd
