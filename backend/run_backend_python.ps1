param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$ScriptPath,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArgs
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $scriptDir ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    throw "未找到虚拟环境解释器：$venvPython"
}

$resolvedScriptPath = if ([System.IO.Path]::IsPathRooted($ScriptPath)) {
    $ScriptPath
} else {
    Join-Path $scriptDir $ScriptPath
}

if (-not (Test-Path $resolvedScriptPath)) {
    throw "未找到 Python 脚本：$resolvedScriptPath"
}

Write-Host "Using Python: $venvPython"
Write-Host "Running Script: $resolvedScriptPath"

& $venvPython $resolvedScriptPath @ScriptArgs
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    exit $exitCode
}
