Set-StrictMode -Version 2
$ErrorActionPreference = 'Stop'

function Get-KpHash([string]$Path) {
    if (-not [IO.File]::Exists($Path)) { return $null }
    $stream=[IO.File]::OpenRead($Path)
    $algorithm=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($algorithm.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
    finally { $algorithm.Dispose(); $stream.Dispose() }
}
function Read-KpJson([string]$Path) {
    return [IO.File]::ReadAllText($Path, [Text.Encoding]::UTF8) | ConvertFrom-Json
}
function Write-KpJson([string]$Path, $Value) {
    $temp = $Path + '.writing'
    [IO.File]::WriteAllText($temp, ($Value | ConvertTo-Json -Depth 30), [Text.UTF8Encoding]::new($false))
    if ([IO.File]::Exists($Path)) { [IO.File]::Replace($temp, $Path, [NullString]::Value) }
    else { [IO.File]::Move($temp, $Path) }
}
function Assert-KpStopped {
    $processes=[Diagnostics.Process]::GetProcessesByName('VernalEdge')
    $running=$processes.Length -gt 0
    foreach ($process in $processes) { $process.Dispose() }
    if ($running) {
        throw 'Close Vernal Edge before installing or removing the patch.'
    }
}
function Assert-KpPath([string]$Name) {
    if ($Name -cnotmatch '^(data\.win|loc/(available|ko-KR|ja-JP)\.json)$') {
        throw "Invalid patch target: $Name"
    }
}
function Assert-KpDigest($Hash) {
    if ($null -ne $Hash -and $Hash -cnotmatch '^[a-f0-9]{64}$') { throw 'Invalid SHA256 digest.' }
}
function Move-KpFile([string]$Source, [string]$Target) {
    if ([IO.File]::Exists($Target)) { [IO.File]::Replace($Source, $Target, [NullString]::Value) }
    else { [IO.File]::Move($Source, $Target) }
}
function Copy-KpCount($InputStream, $OutputStream, [long]$Count) {
    $buffer = New-Object byte[] 1048576
    while ($Count -gt 0) {
        $read = $InputStream.Read($buffer, 0, [int][Math]::Min($buffer.Length, $Count))
        if ($read -le 0) { throw 'Unexpected end of patch/source data.' }
        $OutputStream.Write($buffer, 0, $read)
        $Count -= $read
    }
}
function Write-KpPatchedFile([string]$GameDirectory, [string]$PackageDirectory, $Entry, [string]$Output) {
    Assert-KpPath $Entry.path
    $base = $null
    $outStream = $null
    try {
        if ($null -ne $Entry.original) {
            $base = [IO.File]::OpenRead((Join-Path $GameDirectory $Entry.path))
        }
        $outStream = [IO.File]::Open($Output, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
        [long]$written = 0
        foreach ($op in $Entry.operations) {
            [long]$length = $op.length
            if ($length -le 0 -or $written + $length -gt [long]$Entry.size) { throw 'Invalid patch segment length.' }
            if ($op.type -eq 'copy') {
                if ($null -eq $base -or [long]$op.offset -lt 0 -or [long]$op.offset + $length -gt $base.Length) {
                    throw 'Patch source range is invalid.'
                }
                [void]$base.Seek([long]$op.offset, [IO.SeekOrigin]::Begin)
                Copy-KpCount $base $outStream $length
            } elseif ($op.type -eq 'add') {
                Assert-KpDigest $op.blob
                $blobPath = Join-Path $PackageDirectory ('payload/' + $op.blob + '.gz')
                if ((Get-KpHash $blobPath) -cne $op.blob) { throw 'Patch payload checksum mismatch.' }
                $inputStream = [IO.File]::OpenRead($blobPath)
                $gzip = $null
                try {
                    $gzip = [IO.Compression.GZipStream]::new($inputStream, [IO.Compression.CompressionMode]::Decompress)
                    Copy-KpCount $gzip $outStream $length
                    if ($gzip.ReadByte() -ne -1) { throw 'Patch segment has extra data.' }
                } finally {
                    if ($null -ne $gzip) { $gzip.Dispose() }
                    $inputStream.Dispose()
                }
            } else { throw 'Unknown patch operation.' }
            $written += $length
        }
        if ($written -ne [long]$Entry.size) { throw 'Patched size does not match manifest.' }
    } finally {
        if ($null -ne $outStream) { $outStream.Dispose() }
        if ($null -ne $base) { $base.Dispose() }
    }
    if ((Get-KpHash $Output) -cne $Entry.patched) { throw ('Patched checksum mismatch: ' + $Entry.path) }
}
function Clear-KpStage([string]$Stage, [string]$BackupDirectory) {
    # Never recursively delete a computed directory. Only remove our staged files.
    $resolved = [IO.Path]::GetFullPath($Stage)
    $parent = [IO.Path]::GetFullPath($BackupDirectory).TrimEnd('\') + '\'
    if (-not $resolved.StartsWith($parent, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe stage cleanup.' }
    if ([IO.Directory]::Exists($Stage)) {
        foreach ($file in [IO.Directory]::GetFiles($Stage)) { [IO.File]::Delete($file) }
        [IO.Directory]::Delete($Stage, $false)
    }
}
function Assert-KpState($State) {
    if ($State.format -ne 1 -or @($State.files).Count -ne 3) { throw 'Invalid backup state.' }
    $seen = @{}
    foreach ($entry in $State.files) {
        Assert-KpPath $entry.path
        Assert-KpDigest $entry.original
        Assert-KpDigest $entry.patched
        if ($null -eq $entry.patched -or $seen.ContainsKey($entry.path)) { throw 'Invalid backup file entries.' }
        $seen[$entry.path] = $true
    }
    if (-not $seen.ContainsKey('data.win') -or -not $seen.ContainsKey('loc/available.json')) { throw 'Missing required patch target.' }
    Assert-KpDigest $State.exe
    if ($null -eq $State.exe) { throw 'Missing executable guard.' }
}
function Restore-KpState([string]$GameDirectory, [string]$BackupDirectory, $State) {
    Assert-KpState $State
    if ((Get-KpHash (Join-Path $GameDirectory 'VernalEdge.exe')) -cne $State.exe) {
        throw 'Executable changed since installation. Recovery is blocked to protect an updated game.'
    }
    # Preflight ALL files, so a user edit prevents any restoration writes.
    foreach ($entry in $State.files) {
        $current = Get-KpHash (Join-Path $GameDirectory $entry.path)
        if ($current -cne $entry.original -and $current -cne $entry.patched) {
            throw ('Conflict; refusing to overwrite: ' + $entry.path)
        }
        if ($null -ne $entry.original -and (Get-KpHash (Join-Path $BackupDirectory $entry.path)) -cne $entry.original) {
            throw ('Original backup is missing or corrupt: ' + $entry.path)
        }
    }
    $stage = Join-Path $BackupDirectory ('.restore-' + [Guid]::NewGuid().ToString('N'))
    [void][IO.Directory]::CreateDirectory($stage)
    try {
        for ($i = 0; $i -lt @($State.files).Count; $i++) {
            $entry = $State.files[$i]
            if ($null -ne $entry.original) {
                [IO.File]::Copy((Join-Path $BackupDirectory $entry.path), (Join-Path $stage "$i.bin"), $false)
                if ((Get-KpHash (Join-Path $stage "$i.bin")) -cne $entry.original) { throw 'Restore stage checksum mismatch.' }
            }
        }
        $State.phase = 'restoring'
        Write-KpJson (Join-Path $BackupDirectory 'state.json') $State
        for ($i = @($State.files).Count - 1; $i -ge 0; $i--) {
            $entry = $State.files[$i]
            $target = Join-Path $GameDirectory $entry.path
            $current = Get-KpHash $target
            if ($current -cne $entry.original -and $current -cne $entry.patched) { throw ('File changed during restore: ' + $entry.path) }
            if ($null -ne $entry.original) { Move-KpFile (Join-Path $stage "$i.bin") $target }
            elseif ($null -ne $current) { [IO.File]::Delete($target) }
        }
        foreach ($entry in $State.files) {
            if ((Get-KpHash (Join-Path $GameDirectory $entry.path)) -cne $entry.original) { throw 'Restore verification failed.' }
        }
        $State.phase = 'removed'
        Write-KpJson (Join-Path $BackupDirectory 'state.json') $State
    } finally { Clear-KpStage $stage $BackupDirectory }
}
function Invoke-KoreanPatch {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true)][string]$GameDirectory,
        [Parameter(Mandatory=$true)][string]$PackageDirectory,
        [ValidateSet('Install','Uninstall','Verify')][string]$Mode = 'Install',
        [switch]$AllowBeta
    )
    $GameDirectory = [IO.Path]::GetFullPath($GameDirectory)
    $PackageDirectory = [IO.Path]::GetFullPath($PackageDirectory)
    if (-not [IO.Directory]::Exists($GameDirectory)) { throw 'Game directory does not exist.' }
    Assert-KpStopped
    $backup = Join-Path $GameDirectory '.vernal-edge-ko-backup'
    $statePath = Join-Path $backup 'state.json'
    if ($Mode -eq 'Uninstall') {
        if (-not [IO.File]::Exists($statePath)) { throw 'No installation state found.' }
        Restore-KpState $GameDirectory $backup (Read-KpJson $statePath)
        Write-Output 'Original files restored. Backup retained. Save files were not accessed.'
        return
    }
    $manifest = Read-KpJson (Join-Path $PackageDirectory 'manifest.json')
    if ($manifest.format -ne 1 -or $manifest.appid -ne 1546710) { throw 'Unsupported patch manifest.' }
    $candidateState = [pscustomobject]@{format=1; package=$manifest.package; exe=$manifest.exe; phase='preparing'; files=@($manifest.files)}
    Assert-KpState $candidateState
    if ((Get-KpHash (Join-Path $GameDirectory 'VernalEdge.exe')) -cne $manifest.exe) { throw 'Unsupported executable/version.' }
    if ($Mode -eq 'Verify') {
        foreach ($entry in $manifest.files) {
            if ((Get-KpHash (Join-Path $GameDirectory $entry.path)) -cne $entry.patched) { throw ('Installed checksum differs: ' + $entry.path) }
        }
        Write-Output 'All installed patch checksums match.'
        return
    }
    if (-not $manifest.releaseReady -and -not $AllowBeta) { throw 'This is an unreviewed beta. Add -AllowBeta only if you intend to test it.' }
    if ([IO.File]::Exists($statePath)) {
        $existing = Read-KpJson $statePath
        Assert-KpState $existing
        if ($existing.phase -eq 'installed' -and $existing.package -ceq $manifest.package) {
            foreach ($entry in $manifest.files) {
                if ((Get-KpHash (Join-Path $GameDirectory $entry.path)) -cne $entry.patched) { throw ('Installed file modified: ' + $entry.path) }
            }
            Write-Output 'This patch is already installed; nothing changed.'
            return
        }
        if ($existing.phase -ne 'removed') { throw 'Another/incomplete patch installation exists. Run -Mode Uninstall first.' }
    }
    foreach ($entry in $manifest.files) {
        if ((Get-KpHash (Join-Path $GameDirectory $entry.path)) -cne $entry.original) {
            throw ('Unsupported original or existing file; no files changed: ' + $entry.path)
        }
    }
    [void][IO.Directory]::CreateDirectory($backup)
    $stage = Join-Path $backup ('.install-' + [Guid]::NewGuid().ToString('N'))
    [void][IO.Directory]::CreateDirectory($stage)
    try {
        for ($i=0; $i -lt @($manifest.files).Count; $i++) {
            $entry=$manifest.files[$i]
            if ($null -ne $entry.original) {
                $saved=Join-Path $backup $entry.path
                [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($saved))
                if (-not [IO.File]::Exists($saved)) { [IO.File]::Copy((Join-Path $GameDirectory $entry.path), $saved, $false) }
                if ((Get-KpHash $saved) -cne $entry.original) { throw ('Existing backup differs; never overwrite it: ' + $entry.path) }
            }
            Write-KpPatchedFile $GameDirectory $PackageDirectory $entry (Join-Path $stage "$i.bin")
        }
        Assert-KpStopped
        # Recheck originals after potentially lengthy patch reconstruction.
        foreach ($entry in $manifest.files) {
            if ((Get-KpHash (Join-Path $GameDirectory $entry.path)) -cne $entry.original) { throw 'Game changed while staging; no patch committed.' }
        }
        $candidateState.phase='installing'
        Write-KpJson $statePath $candidateState
        try {
            for ($i=0; $i -lt @($manifest.files).Count; $i++) {
                $entry=$manifest.files[$i]
                Move-KpFile (Join-Path $stage "$i.bin") (Join-Path $GameDirectory $entry.path)
            }
            foreach ($entry in $manifest.files) {
                if ((Get-KpHash (Join-Path $GameDirectory $entry.path)) -cne $entry.patched) { throw 'Commit verification failed.' }
            }
            $candidateState.phase='installed'
            Write-KpJson $statePath $candidateState
        } catch {
            $installError=$_
            try { Restore-KpState $GameDirectory $backup $candidateState }
            catch { throw ('Install failed and recovery needs attention. Keep the backup and run -Mode Uninstall. Details: ' + $_.Exception.Message) }
            throw ('Install failed; original files restored. Details: ' + $installError.Exception.Message)
        }
        Write-Output 'Korean patch installed. Select Korean in the game language menu.'
    } finally { Clear-KpStage $stage $backup }
}
Export-ModuleMember -Function Invoke-KoreanPatch
