#define MyAppName "TELITA OCR"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "TELITA OCR"
#define MyAppExeName "TelitaOCR.exe"
#define MyAppSourceDir "..\dist\TelitaOCR"

[Setup]
AppId={{A84A0B14-4A6A-4F35-B6E5-203869D95D22}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\TELITA OCR
DefaultGroupName=TELITA OCR
AllowNoIcons=yes
OutputDir=..\installer_output
OutputBaseFilename=TELITA_OCR_Installer
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\TELITA OCR"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\TELITA OCR"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Ejecutar TELITA OCR"; Flags: nowait postinstall skipifsilent

[Code]
procedure InitializeWizard;
begin
  SuppressibleMsgBox(
    'IMPORTANTE: TELITA OCR requiere instalar tambien:' + #13#10#13#10 +
    '- Tesseract-OCR (https://github.com/UB-Mannheim/tesseract/wiki)' + #13#10 +
    '- Ghostscript (https://ghostscript.com/releases/gsdnld.html)' + #13#10#13#10 +
    'Despues de instalarlos, asegurese de agregar sus rutas al PATH de Windows.',
    mbInformation,
    MB_OK,
    IDOK
  );
end;
