; Скрипт установщика Inno Setup для Krisha Parser Bot
; Создаёт профессиональный установщик с автоматической установкой Node.js

#define MyAppName "Krisha Parser Bot"
#define MyAppVersion "1.0"
#define MyAppPublisher "Your Company"
#define MyAppExeName "KrishaParser.exe"
#define MyAppURL "https://yourwebsite.com"

[Setup]
; Основные параметры
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE.txt
InfoBeforeFile=INSTALL_INFO.txt
OutputDir=installer_output
OutputBaseFilename=KrishaParserBot_Setup
SetupIconFile=icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

; Визуальные параметры
WizardImageFile=wizard_image.bmp
WizardSmallImageFile=wizard_small.bmp

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Основная программа
Source: "dist\KrishaParser\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; WhatsApp сервер
Source: "wa-server\*"; DestDir: "{app}\wa-server"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "node_modules,wa_auth_data,*.log"
; Документация
Source: "README.md"; DestDir: "{app}"; DestName: "README.txt"; Flags: ignoreversion
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
; Node.js установщик (если есть)
Source: "node-installer.msi"; DestDir: "{tmp}"; Flags: external deleteafterinstall; Check: NodeJSNotInstalled

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Установка Node.js если не установлен
Filename: "msiexec.exe"; Parameters: "/i ""{tmp}\node-installer.msi"" /qn /norestart"; StatusMsg: "Установка Node.js..."; Flags: waituntilterminated; Check: NodeJSNotInstalled
; Установка npm зависимостей для wa-server
Filename: "cmd.exe"; Parameters: "/c cd /d ""{app}\wa-server"" && npm install"; StatusMsg: "Установка WhatsApp сервера..."; Flags: waituntilterminated runhidden; Check: NodeJSInstalled
; Запуск программы после установки
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\wa-server\node_modules"
Type: filesandordirs; Name: "{app}\wa-server\wa_auth_data"
Type: files; Name: "{app}\phones.db"
Type: files; Name: "{app}\config.json"
Type: files; Name: "{app}\*.log"

[Code]
var
  NodeJSPage: TInputOptionWizardPage;
  DownloadPage: TDownloadWizardPage;

// Проверка установлен ли Node.js
function NodeJSInstalled: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/c node --version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

function NodeJSNotInstalled: Boolean;
begin
  Result := not NodeJSInstalled;
end;

// Инициализация мастера установки
procedure InitializeWizard;
begin
  // Страница с информацией о Node.js
  if not NodeJSInstalled then
  begin
    NodeJSPage := CreateInputOptionPage(wpLicense,
      'Установка Node.js', 'Для работы WhatsApp требуется Node.js',
      'Node.js не обнаружен в системе. Выберите действие:',
      True, False);
    NodeJSPage.Add('Установить Node.js автоматически (рекомендуется)');
    NodeJSPage.Add('Я установлю Node.js вручную позже');
    NodeJSPage.Values[0] := True;
  end;
  
  // Страница загрузки
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing), SetupMessage(msgPreparingDesc), nil);
end;

// Подготовка к установке
function NextButtonClick(CurPageID: Integer): Boolean;
var
  NodeURL: String;
begin
  Result := True;
  
  if CurPageID = wpReady then
  begin
    // Если нужно скачать Node.js
    if not NodeJSInstalled and NodeJSPage.Values[0] then
    begin
      DownloadPage.Clear;
      NodeURL := 'https://nodejs.org/dist/v20.11.0/node-v20.11.0-x64.msi';
      DownloadPage.Add(NodeURL, 'node-installer.msi', '');
      DownloadPage.Show;
      try
        try
          DownloadPage.Download;
          Result := True;
        except
          if DownloadPage.AbortedByUser then
            Log('Загрузка отменена пользователем')
          else
            SuppressibleMsgBox(AddPeriod(GetExceptionMessage), mbCriticalError, MB_OK, IDOK);
          Result := False;
        end;
      finally
        DownloadPage.Hide;
      end;
    end;
  end;
end;

// Сообщение после установки
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if not NodeJSInstalled then
    begin
      MsgBox('Node.js не установлен. Для работы WhatsApp установите Node.js вручную с https://nodejs.org/', mbInformation, MB_OK);
    end;
  end;
end;

[CustomMessages]
russian.LaunchProgram=Запустить %1 после установки
russian.CreateDesktopIcon=Создать значок на рабочем столе
russian.CreateQuickLaunchIcon=Создать значок в панели быстрого запуска
russian.AdditionalIcons=Дополнительные значки:
russian.UninstallProgram=Удалить %1

[Messages]
WelcomeLabel2=Программа установит [name/ver] на ваш компьютер.%n%nРекомендуется закрыть все другие приложения перед продолжением.
