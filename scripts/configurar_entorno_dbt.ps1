$envPath = Join-Path $PSScriptRoot "..\.env"

if (-not (Test-Path $envPath)) {
    throw "No se encontro el archivo .env en la raiz del proyecto."
}

$keyLine = Get-Content $envPath |
    Where-Object { $_ -match '^PSEUDONYMIZATION_KEY=' } |
    Select-Object -First 1

if (-not $keyLine) {
    throw "No se encontro PSEUDONYMIZATION_KEY en .env."
}

$key = $keyLine.Substring("PSEUDONYMIZATION_KEY=".Length).Trim()

if ([string]::IsNullOrWhiteSpace($key)) {
    throw "PSEUDONYMIZATION_KEY esta vacia."
}

# PostgreSQL recibira la clave como una configuracion de sesion.
# De esta forma no se escribe el secreto dentro del SQL compilado por dbt.
$env:PGOPTIONS = "-c app.pseudonymization_key=$key"

Remove-Variable key
Remove-Variable keyLine

Write-Host "Entorno dbt configurado para seudonimizacion."