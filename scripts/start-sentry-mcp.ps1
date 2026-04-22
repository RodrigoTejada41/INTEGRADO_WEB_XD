Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$nodeCommand = Get-Command node -ErrorAction Stop

function Resolve-NpmCommand {
    $candidates = @()

    try {
        $candidates += (Get-Command npm.cmd -ErrorAction Stop).Source
    }
    catch {
    }

    try {
        $candidates += (Get-Command npm -ErrorAction Stop).Source
    }
    catch {
    }

    if ($env:APPDATA) {
        $candidates += (Join-Path $env:APPDATA "npm\npm.cmd")
    }

    foreach ($candidate in $candidates | Select-Object -Unique) {
        if (-not $candidate) {
            continue
        }

        try {
            if (Test-Path -LiteralPath $candidate) {
                return $candidate
            }
        }
        catch {
            # Some sandboxes deny probing user-profile paths even when the command is executable.
            return $candidate
        }
    }

    throw "Could not locate npm. Ensure Node.js/npm is installed and available for the MCP process."
}

$npmCommand = Resolve-NpmCommand

function Find-SentryCacheEntrypoint {
    $cacheRoots = @()

    if ($env:LOCALAPPDATA) {
        $cacheRoots += (Join-Path $env:LOCALAPPDATA "npm-cache\_npx")
    }

    if ($env:APPDATA) {
        $cacheRoots += (Join-Path $env:APPDATA "npm-cache\_npx")
    }

    foreach ($cacheRoot in $cacheRoots | Select-Object -Unique) {
        try {
            if (-not (Test-Path -LiteralPath $cacheRoot)) {
                continue
            }

            $entrypoint = Get-ChildItem -LiteralPath $cacheRoot -Directory -ErrorAction Stop |
                Sort-Object LastWriteTime -Descending |
                ForEach-Object {
                    $candidate = Join-Path $_.FullName "node_modules\@sentry\mcp-server\dist\index.js"
                    if (Test-Path -LiteralPath $candidate) {
                        return $candidate
                    }
                } |
                Select-Object -First 1

            if ($entrypoint) {
                return $entrypoint
            }
        }
        catch {
            Write-Verbose "Skipping inaccessible npm cache root '$cacheRoot': $($_.Exception.Message)"
        }
    }

    return $null
}

$entrypoint = Find-SentryCacheEntrypoint

if ($entrypoint) {
    & $nodeCommand.Source $entrypoint
    exit $LASTEXITCODE
}

# Fallback: let npm resolve/install the package instead of depending on a fixed cache path.
& $npmCommand exec --yes @sentry/mcp-server
