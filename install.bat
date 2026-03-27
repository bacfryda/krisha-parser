@echo off
set "INSTALL_DIR=%ProgramFiles%\KrishaParser"
set "DESKTOP=%USERPROFILE%\Desktop"
set "TEMP_DIR=%TEMP%\krisha_temp"

mkdir "%TEMP_DIR%" 2>nul
powershell -Command "Expand-Archive -Path 'data.zip' -DestinationPath '%TEMP_DIR%' -Force"

mkdir "%INSTALL_DIR%" 2>nul
xcopy /E /I /Y /Q "%TEMP_DIR%\KrishaParser" "%INSTALL_DIR%\KrishaParser"
xcopy /E /I /Y /Q "%TEMP_DIR%\wa-server" "%INSTALL_DIR%\wa-server"

node --version >nul 2>&1
if %errorLevel% equ 0 (
    cd /d "%INSTALL_DIR%\wa-server"
    call npm install >nul 2>&1
)

powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%DESKTOP%\Krisha Parser.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\KrishaParser\KrishaParser.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%\KrishaParser'; $Shortcut.Save()"

rd /s /q "%TEMP_DIR%" 2>nul

start "" "%INSTALL_DIR%\KrishaParser\KrishaParser.exe"
