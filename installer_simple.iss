#define MyAppName "Krisha Parser Bot"
#define MyAppVersion "1.0"
#define MyAppPublisher "Krisha Parser"
#define MyAppExeName "KrishaParser.exe"

[Setup]
AppId={{B8F9C3D2-1A4E-4F5B-9C8D-2E3F4A5B6C7D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\KrishaParser
DefaultGroupName={#MyAppName}
OutputDir=.
OutputBaseFilename=KrishaParser_Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Files]
Source: "dist\KrishaParser\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "wa-server\package.json"; DestDir: "{app}\wa-server"; Flags: ignoreversion
Source: "wa-server\server.js"; DestDir: "{app}\wa-server"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
