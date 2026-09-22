; NEMO IDE - instalador Inno Setup
; Compilar: ISCC.exe installer.iss

#define MyAppName "NEMO IDE"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "NEMO Squad"
#define MyAppURL "https://github.com/matheusenaa/Agente-NEMO"
#define MyAppExeName "start_nemo.bat"
#define BundleDir "dist\NEMO_IDE"

[Setup]
AppId={{8E4F6C2A-7B1D-4A9E-9E6F-3C2D1B0A5F4E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\NEMO_IDE.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
OutputDir=dist-installer
OutputBaseFilename=NEMO_IDE_Setup_{#MyAppVersion}
SetupIconFile=assets\NEMO.ico
; A chave fica fora do pacote — o usuário cria o .env no primeiro uso
DisableDirPage=no

[Languages]
Name: "bportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos:"; Flags: checkedonce

[Files]
Source: "{#BundleDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_data"