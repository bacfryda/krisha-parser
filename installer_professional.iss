#define MyAppName "Krisha Parser Bot"
#define MyAppVersion "1.0"
#define MyAppPublisher "Krisha Parser"
#define MyAppURL "https://krisha.kz"
#define MyAppExeName "KrishaParser.exe"

[Setup]
AppId={{B8F9C3D2-1A4E-4F5B-9C8D-2E3F4A5B6C7D}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\KrishaParser
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=
OutputDir=C:\parser\krisha-bot
OutputBaseFilename=KrishaParser_Setup_Professional
SetupIconFile=C:\parser\krisha-bot\logo.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "C:\parser\krisha-bot\dist\KrishaParser\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "C:\parser\krisha-bot\wa-server\package.json"; DestDir: "{app}\wa-server"; Flags: ignoreversion
Source: "C:\parser\krisha-bot\wa-server\server.js"; DestDir: "{app}\wa-server"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "C:\parser\krisha-bot\logo.ico"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon; IconFilename: "C:\parser\krisha-bot\logo.ico"

[Run]
Filename: "{cmd}"; Parameters: "/c npm install"; WorkingDir: "{app}\wa-server"; StatusMsg: "Installing WhatsApp server..."; Flags: runhidden waituntilterminated; Check: NodeJSInstalled
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function NodeJSInstalled: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/c node --version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if not NodeJSInstalled then
    begin
      MsgBox('Node.js не установлен. Скачайте с https://nodejs.org/', mbInformation, MB_OK);
    end;
  end;
end;

[UninstallDelete]
Type: filesandordirs; Name: "{app}\wa-server\node_modules"
Type: filesandordirs; Name: "{app}\wa-server\wa_auth_data"
Type: filesandordirs; Name: "{app}\sessions"
Type: files; Name: "{app}\*.db"
Type: files; Name: "{app}\*.log"
