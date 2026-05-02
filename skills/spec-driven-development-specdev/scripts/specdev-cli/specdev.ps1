$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Get-Command bun -ErrorAction SilentlyContinue)) {
    Write-Output '{"ok":false,"error":"Bun runtime not found","code":"PREREQ_MISSING","hint":"Install bun: https://bun.sh"}'
    exit 1
}

if (-not (Test-Path "$ScriptDir\node_modules")) {
    bun install --cwd $ScriptDir --silent
}

& bun run "$ScriptDir\src\index.ts" @args
