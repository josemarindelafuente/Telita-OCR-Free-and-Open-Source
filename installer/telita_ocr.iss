#define MyAppName "TELITA OCR"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "TELITA OCR"
#define MyAppExeName "TelitaOCR.exe"
#define MyAppSourceDir "..\dist\TelitaOCR"
#define TesseractInstallerName "tesseract-installer.exe"
#define GhostscriptInstallerName "ghostscript-installer.exe"

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
Name: "install_tesseract"; Description: "Instalar Tesseract-OCR (requerido para OCR)"; GroupDescription: "Dependencias OCR:"; Check: NeedTesseract
Name: "install_ghostscript"; Description: "Instalar Ghostscript (requerido para OCR principal)"; GroupDescription: "Dependencias OCR:"; Check: NeedGhostscript

[Files]
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\third_party\{#TesseractInstallerName}"; DestDir: "{tmp}"; Flags: ignoreversion deleteafterinstall; Check: NeedTesseract
Source: "..\third_party\{#GhostscriptInstallerName}"; DestDir: "{tmp}"; Flags: ignoreversion deleteafterinstall; Check: NeedGhostscript

[Icons]
Name: "{group}\TELITA OCR"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\TELITA OCR"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{tmp}\{#TesseractInstallerName}"; Parameters: "/S"; Description: "Instalando Tesseract-OCR..."; Flags: waituntilterminated; Tasks: install_tesseract; Check: NeedTesseract
Filename: "{tmp}\{#GhostscriptInstallerName}"; Parameters: "/S"; Description: "Instalando Ghostscript..."; Flags: waituntilterminated; Tasks: install_ghostscript; Check: NeedGhostscript
Filename: "{app}\{#MyAppExeName}"; Description: "Ejecutar TELITA OCR"; Flags: nowait postinstall skipifsilent

[Code]
var
  NeedTesseractVar: Boolean;
  NeedGhostscriptVar: Boolean;

function FileExistsInPath(FileName: string): Boolean;
var
  Paths, CurrentPath: string;
  SeparatorPos: Integer;
begin
  Result := False;
  Paths := GetEnv('PATH');
  while Paths <> '' do
  begin
    SeparatorPos := Pos(';', Paths);
    if SeparatorPos > 0 then
    begin
      CurrentPath := Copy(Paths, 1, SeparatorPos - 1);
      Delete(Paths, 1, SeparatorPos);
    end
    else
    begin
      CurrentPath := Paths;
      Paths := '';
    end;

    CurrentPath := Trim(CurrentPath);
    if (CurrentPath <> '') and FileExists(AddBackslash(CurrentPath) + FileName) then
    begin
      Result := True;
      Exit;
    end;
  end;
end;

function DetectTesseractByRegistry(): Boolean;
var
  InstallDir: string;
begin
  Result :=
    (RegQueryStringValue(HKLM64, 'SOFTWARE\Tesseract-OCR', 'InstallDir', InstallDir) and
     FileExists(AddBackslash(InstallDir) + 'tesseract.exe'))
    or
    (RegQueryStringValue(HKLM32, 'SOFTWARE\Tesseract-OCR', 'InstallDir', InstallDir) and
     FileExists(AddBackslash(InstallDir) + 'tesseract.exe'));
end;

function DetectGhostscriptByRegistry(): Boolean;
var
  InstallPath: string;
  DllPath: string;
begin
  Result :=
    (RegQueryStringValue(HKLM64, 'SOFTWARE\GPL Ghostscript', 'GS_DLL', DllPath))
    or
    (RegQueryStringValue(HKLM32, 'SOFTWARE\GPL Ghostscript', 'GS_DLL', DllPath))
    or
    (RegQueryStringValue(HKLM64, 'SOFTWARE\GPL Ghostscript\10.0.0', 'GS_DLL', DllPath))
    or
    (RegQueryStringValue(HKLM64, 'SOFTWARE\GPL Ghostscript\10.01.0', 'GS_DLL', DllPath))
    or
    (RegQueryStringValue(HKLM64, 'SOFTWARE\GPL Ghostscript\10.02.0', 'GS_DLL', DllPath))
    or
    (RegQueryStringValue(HKLM64, 'SOFTWARE\GPL Ghostscript\10.03.0', 'GS_DLL', DllPath))
    or
    (RegQueryStringValue(HKLM64, 'SOFTWARE\GPL Ghostscript\10.04.0', 'GS_DLL', DllPath))
    or
    (RegQueryStringValue(HKLM64, 'SOFTWARE\GPL Ghostscript\10.05.0', 'GS_DLL', DllPath))
    or
    (RegQueryStringValue(HKLM64, 'SOFTWARE\GPL Ghostscript\10.06.0', 'GS_DLL', DllPath))
    or
    (RegQueryStringValue(HKLM32, 'SOFTWARE\GPL Ghostscript\10.0.0', 'GS_DLL', DllPath))
    or
    (RegQueryStringValue(HKLM32, 'SOFTWARE\GPL Ghostscript\10.01.0', 'GS_DLL', DllPath))
    or
    (RegQueryStringValue(HKLM32, 'SOFTWARE\GPL Ghostscript\10.02.0', 'GS_DLL', DllPath))
    or
    (RegQueryStringValue(HKLM32, 'SOFTWARE\GPL Ghostscript\10.03.0', 'GS_DLL', DllPath))
    or
    (RegQueryStringValue(HKLM32, 'SOFTWARE\GPL Ghostscript\10.04.0', 'GS_DLL', DllPath))
    or
    (RegQueryStringValue(HKLM32, 'SOFTWARE\GPL Ghostscript\10.05.0', 'GS_DLL', DllPath))
    or
    (RegQueryStringValue(HKLM32, 'SOFTWARE\GPL Ghostscript\10.06.0', 'GS_DLL', DllPath))
    or
    (RegQueryStringValue(HKLM64, 'SOFTWARE\GPL Ghostscript', 'InstallPath', InstallPath) and
     FileExists(AddBackslash(InstallPath) + 'bin\gswin64c.exe'))
    or
    (RegQueryStringValue(HKLM32, 'SOFTWARE\GPL Ghostscript', 'InstallPath', InstallPath) and
     FileExists(AddBackslash(InstallPath) + 'bin\gswin64c.exe'));
end;

function IsTesseractInstalled(): Boolean;
begin
  Result := DetectTesseractByRegistry() or FileExistsInPath('tesseract.exe');
end;

function IsGhostscriptInstalled(): Boolean;
begin
  Result :=
    DetectGhostscriptByRegistry()
    or FileExistsInPath('gswin64c.exe')
    or FileExistsInPath('gs.exe');
end;

function NeedTesseract(): Boolean;
begin
  Result := NeedTesseractVar;
end;

function NeedGhostscript(): Boolean;
begin
  Result := NeedGhostscriptVar;
end;

procedure InitializeWizard;
var
  MissingList: string;
begin
  NeedTesseractVar := not IsTesseractInstalled();
  NeedGhostscriptVar := not IsGhostscriptInstalled();

  MissingList := '';
  if NeedTesseractVar then
    MissingList := MissingList + '- Tesseract-OCR' + #13#10;
  if NeedGhostscriptVar then
    MissingList := MissingList + '- Ghostscript' + #13#10;

  if MissingList = '' then
  begin
    SuppressibleMsgBox(
      'Se detectaron correctamente Tesseract y Ghostscript.' + #13#10 +
      'Podras usar todos los modos OCR al finalizar la instalacion.',
      mbInformation,
      MB_OK,
      IDOK
    );
    Exit;
  end;

  SuppressibleMsgBox(
    'TELITA OCR detecto dependencias faltantes:' + #13#10#13#10 +
    MissingList + #13#10 +
    'Si dejas marcadas las tareas de dependencias, el instalador intentara instalarlas.' + #13#10 +
    'Si prefieres instalar manualmente, usa:' + #13#10 +
    '- Tesseract: https://github.com/UB-Mannheim/tesseract/wiki' + #13#10 +
    '- Ghostscript: https://ghostscript.com/releases/gsdnld.html' + #13#10#13#10 +
    'Nota: en algunos instaladores silenciosos puede ser necesario cerrar sesion o reiniciar para actualizar PATH.',
    mbInformation,
    MB_OK,
    IDOK
  );
end;
