param([string]$Game, [string]$Package, [string]$Mode, [string]$Scenario='normal', [string]$ModulePath)
$ErrorActionPreference='Stop'
try {
    if (-not $ModulePath) { $ModulePath=Join-Path $PSScriptRoot '../installer/Patch.Core.psm1' }
    $module=Import-Module $ModulePath -Force -PassThru
    # Fixture tests must not depend on whether the user is playing the real game.
    & $module { function script:Assert-KpStopped {} }
    if ($Scenario -eq 'running') {
        & $module { function script:Assert-KpStopped { throw 'Close Vernal Edge before installing or removing the patch.' } }
    }
    if ($Scenario -eq 'fail-second-commit') {
        & $module {
            $script:realMove=${function:Move-KpFile}
            $script:moveCount=0
            function script:Move-KpFile([string]$Source,[string]$Target) {
                $script:moveCount++
                if ($script:moveCount -eq 2) { throw 'Injected test-only commit failure' }
                & $script:realMove $Source $Target
            }
        }
    }
    Invoke-KoreanPatch -GameDirectory $Game -PackageDirectory $Package -Mode $Mode -AllowBeta
} catch { Write-Output ('FAIL: '+$_.Exception.Message); exit 1 }
