; Inno Setup Script for Sifat Voice Type
; Production-grade installer for sharing and commercial distribution

#define MyAppName "Sifat Voice Type"
#define MyAppVersion "1.1.2"
#define MyAppPublisher "Majharul Islam Sifat"
#define MyAppExeName "SifatVoiceType.exe"

[Setup]
; Basic Application Info
AppId={{E68A91F2-7A64-4F91-B71C-07851A6F8F32}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=""
AppSupportURL=""
AppUpdatesURL=""

; Installation Directories
; Defaults to user AppData Local/Programs so it NEVER requires Administrator privileges to install or run!
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Output Configuration
OutputDir=..\installer_output
OutputBaseFilename=SifatVoiceType_Setup_v1.1.2
SetupIconFile=..\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Compression
Compression=lzma2/ultra64
SolidCompression=yes

; Privileges: lowest allows regular users to install on any PC without UAC prompt or admin password!
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Detect the running app before install/uninstall so its files are not left behind.
AppMutex=Global\SifatVoiceType_SingleInstance_Mutex

; Modern UI Style
WizardStyle=modern

; Close applications using files being updated
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startupicon"; Description: "Start automatically when Windows boots (পিসি অন করলে ব্যাকগ্রাউন্ডে চালু হবে)"; GroupDescription: "Windows Integration:"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\app_icon.png"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu Shortcut
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"
; Start Menu Uninstaller
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
; Desktop Shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon
; Windows Startup Folder (if user chooses task)
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

[Registry]
; Configure auto-start via Registry HKCU (ensures seamless startup without admin rights)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "SifatVoiceType"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startupicon

[Run]
; Option to launch application immediately after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up any logs, temp files, or clipboard caches generated in app directory
Type: filesandordirs; Name: "{app}"

[Code]
// Helper function to safely terminate running application instances using Windows taskkill
procedure TerminateAppProcess();
var
  ResultCode: Integer;
begin
  Exec('taskkill.exe', '/F /IM ' + '{#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

function InitializeSetup(): Boolean;
begin
  // Terminate any running instance before running the installer
  TerminateAppProcess();
  Result := True;
end;

function InitializeUninstall(): Boolean;
begin
  // Terminate any running instance or background tray icon before uninstalling
  TerminateAppProcess();
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    // Double ensure process is completely killed
    TerminateAppProcess();
    // Clean Windows Startup registry entry
    RegDeleteValue(HKEY_CURRENT_USER, 'Software\Microsoft\Windows\CurrentVersion\Run', 'SifatVoiceType');
  end;
end;
