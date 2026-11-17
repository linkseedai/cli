# Install the linkseed command for Windows from a GitHub release.
# publish_cli.sh replaces __VERSION__ when exporting this file.
$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Repo = "linkseedai/cli"
$Version = "0.1.0-alpha"
if ($Version -eq "__VERSION__") {
  throw "This installer has no version. Use the copy exported to GitHub."
}

switch ($env:PROCESSOR_ARCHITECTURE) {
  "AMD64" { $Cpu = "amd64" }
  default { throw "Unsupported architecture: $($env:PROCESSOR_ARCHITECTURE)" }
}

$Archive = "linkseed-$Version-windows-$Cpu.zip"
$Base = "https://github.com/$Repo/releases/download/v$Version"
$ChecksumUrl = "https://raw.githubusercontent.com/$Repo/v$Version/checksums.txt"
$TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("linkseed-cli-" + [guid]::NewGuid().ToString("n"))
New-Item -ItemType Directory -Path $TempDir | Out-Null

try {
  $ChecksumFile = Join-Path $TempDir "checksums.txt"
  $ArchiveFile = Join-Path $TempDir $Archive
  Invoke-WebRequest -Uri $ChecksumUrl -OutFile $ChecksumFile
  Invoke-WebRequest -Uri "$Base/$Archive" -OutFile $ArchiveFile

  $Expected = $null
  foreach ($Line in Get-Content -Path $ChecksumFile) {
    $Trimmed = $Line.Trim()
    if (-not $Trimmed -or $Trimmed.StartsWith("#")) { continue }
    $Parts = $Trimmed -split "\s+", 2
    if ($Parts.Length -eq 2 -and $Parts[1] -eq $Archive) {
      $Expected = $Parts[0]
      break
    }
  }
  if (-not $Expected) { throw "No checksum for $Archive." }

  $Actual = (Get-FileHash -Algorithm SHA256 -Path $ArchiveFile).Hash
  if ($Actual.ToLower() -ne $Expected.ToLower()) {
    throw "Checksum mismatch for $Archive."
  }

  Expand-Archive -LiteralPath $ArchiveFile -DestinationPath $TempDir -Force
  $Binary = Join-Path $TempDir "linkseed.exe"
  if (-not (Test-Path -LiteralPath $Binary)) {
    throw "Archive $Archive does not contain linkseed.exe."
  }

  $DestDir = Join-Path $env:LOCALAPPDATA "linkseed"
  New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
  Copy-Item -LiteralPath $Binary -Destination (Join-Path $DestDir "linkseed.exe") -Force

  $UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
  $PathParts = @()
  if ($UserPath) { $PathParts = $UserPath -split ";" }
  $AlreadyOnPath = $false
  foreach ($Part in $PathParts) {
    if ($Part.TrimEnd("\") -eq $DestDir.TrimEnd("\")) { $AlreadyOnPath = $true }
  }
  if (-not $AlreadyOnPath) {
    $Updated = if ($UserPath) { "$UserPath;$DestDir" } else { $DestDir }
    [Environment]::SetEnvironmentVariable("Path", $Updated, "User")
  }

  Write-Host "linkseed $Version installed to $DestDir\linkseed.exe"
  Write-Host "Open a new PowerShell window, then run: linkseed auth --help"
}
finally {
  Remove-Item -LiteralPath $TempDir -Recurse -Force
}
