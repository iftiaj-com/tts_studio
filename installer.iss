; installer.iss
; Inno Setup script that packages the PyInstaller build (dist\TTS_Studio\)
; produced by build_exe.py into a standard Windows Setup.exe installer.
;
; Build order:
;   1. python build_exe.py          -> produces dist\TTS_Studio\TTS_Studio.exe
;   2. ISCC.exe installer.iss       -> produces installer_output\VoiceCraft-Setup-<version>.exe

#define MyAppName "VoiceCraft"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "VoiceCraft"
#define MyAppExeName "TTS_Studio.exe"
#define MyAppSourceDir "dist\TTS_Studio"

[Setup]
AppId={{B6E3F5C2-6E4B-4B7B-9C1A-2F3A6F8C5D91}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=VoiceCraft-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#MyAppExeName}
DisableWelcomePage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
