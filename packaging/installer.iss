; Installationsprogramm für das Finance-Tool (Inno Setup 6).
;
; * Installiert pro Benutzer nach %LOCALAPPDATA%\Programs\Finance-Tool –
;   dafür sind KEINE Administratorrechte nötig.
; * Legt Startmenü-Eintrag und (optional) Desktop-Verknüpfung an.
; * Die Daten (Umsätze, gelernte Regeln) liegen getrennt in
;   %APPDATA%\Finance-Tool und bleiben bei Updates und Deinstallation erhalten.
;
; Aufruf:  ISCC.exe /DAppVersion=2.0.0 /DQuelle=<Pfad zu dist\Finance-Tool> installer.iss

#define AppName "Finance-Tool"
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef Quelle
  #define Quelle "..\dist\Finance-Tool"
#endif
#ifndef Ausgabe
  #define Ausgabe "..\dist"
#endif

[Setup]
; Feste ID – daran erkennt Windows ein Update derselben Anwendung.
AppId={{6F2C7B1E-4D3A-4B8E-9C5F-2A1E0D9B7C34}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Finance-Tool
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
OutputDir={#Ausgabe}
OutputBaseFilename=Finance-Tool-Setup-{#AppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\Finance-Tool.exe
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0
; Läuft das Programm noch, wird es für das Update geschlossen.
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; Beim Update alte Programmdateien entfernen, damit keine veralteten
; Bibliotheken liegen bleiben (Benutzerdaten liegen woanders).
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#Quelle}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\Finance-Tool.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Finance-Tool.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Finance-Tool.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
