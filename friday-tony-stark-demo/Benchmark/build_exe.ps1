$ErrorActionPreference = "Stop"

$benchmarkDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $benchmarkDir
$entryPoint = Join-Path $benchmarkDir "main.py"
$distDir = Join-Path $benchmarkDir "dist"
$workDir = Join-Path $benchmarkDir "build"

Push-Location $projectRoot
try {
    uv run --with pyinstaller pyinstaller `
        --noconfirm `
        --clean `
        --onefile `
        --console `
        --name FRIDAYVisionBenchmark `
        --paths $projectRoot `
        --distpath $distDir `
        --workpath $workDir `
        --specpath $workDir `
        $entryPoint
}
finally {
    Pop-Location
}

Write-Host "Built: $(Join-Path $distDir 'FRIDAYVisionBenchmark.exe')"
