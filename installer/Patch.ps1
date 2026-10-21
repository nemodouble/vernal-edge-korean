[CmdletBinding()]
param(
    [string]$GameDirectory,
    [ValidateSet('Install','Uninstall','Verify')][string]$Mode='Install',
    [switch]$AllowBeta
)
$ErrorActionPreference='Stop'
try {
    if (-not $GameDirectory) {
        $candidate=$PSScriptRoot
        for ($i=0; $i -lt 5; $i++) {
            if (Test-Path -LiteralPath (Join-Path $candidate 'VernalEdge.exe')) { $GameDirectory=$candidate; break }
            $parent=Split-Path -Parent $candidate
            if (-not $parent -or $parent -eq $candidate) { break }
            $candidate=$parent
        }
        if (-not $GameDirectory) { $GameDirectory=Read-Host 'Vernal Edge game folder (contains VernalEdge.exe)' }
    }
    Import-Module (Join-Path $PSScriptRoot 'Patch.Core.psm1') -Force
    Invoke-KoreanPatch -GameDirectory $GameDirectory -PackageDirectory $PSScriptRoot -Mode $Mode -AllowBeta:$AllowBeta
} catch { Write-Error $_; exit 1 }
