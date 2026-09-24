; KyteView - Inno Setup 現代安裝程式設定檔
; 適用於 Inno Setup 6.x

#define MyAppName "KyteView"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ais7896-hue"
#define MyAppURL "https://github.com/ais7896-hue/KyteView"
#define MyAppExeName "KyteView.exe"

[Setup]
; 應用程式基本資訊
AppId={{9F7B18E3-4B82-4160-84E3-8E1E7D173981}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
; 授權檔案與圖示
LicenseFile=LICENSE
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
; 壓縮設定（最高壓縮比）
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=KyteView_Setup_{#MyAppVersion}

[Languages]
Name: "chinesetrad"; MessagesFile: "compiler:Languages\ChineseTraditional.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "開機時自動啟動 KyteView (推薦)"; GroupDescription: "啟動選項:"; Flags: checkablealone

[Files]
; 來源檔案為 PyInstaller 產生的 dist\KyteView 目錄
Source: "dist\KyteView\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\KyteView\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; 注意: 避免在發布目錄中包含本機設定檔
; Excludes: "config.json, *.log"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; 開機自動啟動
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
