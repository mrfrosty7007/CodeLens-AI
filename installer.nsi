; ==============================================================================
; CodeLens AI - Nullsoft Scriptable Install System (NSIS) Script
; Produces: dist\CodeLensAI-Setup.exe
; Phase H3: Zero-Friction Windows Installer
; ==============================================================================

!include "MUI2.nsh"
!include "FileFunc.nsh"

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
!define MUI_WELCOMEPAGE_TEXT "This wizard will guide you through installing CodeLens AI—the offline, private AI code intelligence workspace powered by local inference.$\r$\n$\r$\nClick Next to continue."
!insertmacro MUI_PAGE_WELCOME

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

; Finish Page with Launch Option
!define MUI_FINISHPAGE_RUN "$INSTDIR\${MAIN_EXECUTABLE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch CodeLens AI now"
!define MUI_FINISHPAGE_TEXT "CodeLens AI has been successfully installed on your computer.$\r$\n$\r$\nFirst launch will verify local AI components (Ollama & Qwen 3B) for 100% offline use."
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
    SetOutPath "$INSTDIR"
    SetOverwrite on

    ; Copy all packaged distribution files
    File /r "build\package\*.*"

    ; Store installation folder
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\${MAIN_EXECUTABLE}"

    ; Create Shortcuts
    CreateDirectory "$SMPROGRAMS\CodeLens AI"
    CreateShortcut "$SMPROGRAMS\CodeLens AI\CodeLens AI.lnk" "$INSTDIR\${MAIN_EXECUTABLE}" "" "$INSTDIR\assets\icon.ico" 0
    CreateShortcut "$SMPROGRAMS\CodeLens AI\Uninstall CodeLens AI.lnk" "$INSTDIR\Uninstall.exe" "" "$INSTDIR\assets\icon.ico" 0
    CreateShortcut "$DESKTOP\CodeLens AI.lnk" "$INSTDIR\${MAIN_EXECUTABLE}" "" "$INSTDIR\assets\icon.ico" 0

    ; Write Uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Windows Add/Remove Programs Registry Entries
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
    ; Remove Shortcuts
    Delete "$DESKTOP\CodeLens AI.lnk"
    Delete "$SMPROGRAMS\CodeLens AI\CodeLens AI.lnk"
    Delete "$SMPROGRAMS\CodeLens AI\Uninstall CodeLens AI.lnk"
    RMDir "$SMPROGRAMS\CodeLens AI"

    ; Remove App Files
    Delete "$INSTDIR\${MAIN_EXECUTABLE}"
    Delete "$INSTDIR\Uninstall.exe"
    RMDir /r "$INSTDIR"

    ; Remove Registry Keys
    DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
    DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_DIR_REGKEY}"
    SetAutoClose true
SectionEnd
