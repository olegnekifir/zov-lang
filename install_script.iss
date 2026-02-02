[Setup]
AppName=ZOV Language
AppVersion=1.0
DefaultDirName={autopf}\ZOV_Lang
DefaultGroupName=Olezha
UninstallDisplayIcon={app}\zov.exe
Compression=lzma
SolidCompression=yes
OutputDir=userdocs:Inno Setup Outputs
PrivilegesRequired=admin
ChangesEnvironment=yes

[Files]
Source: "Ваш путь к файлу zov.exe. Пример: D:/zov-lang/zov.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ZOV Tools"; Filename: "{app}\zov.exe"

[Registry]
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; \
    ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; \
    Check: NeedsAddPath('{app}')

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE,
    'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
    'Path', OrigPath) then begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + UpperCase(Param) + ';', ';' + UpperCase(OrigPath) + ';') = 0;
end;