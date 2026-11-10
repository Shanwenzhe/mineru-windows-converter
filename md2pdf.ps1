# 用法：md2pdf "F:\某.md"；保留同目录下的 .typ、.pdf 和逐页 PNG 预览。
param([Parameter(Mandatory = $true)][string]$Md)

$ErrorActionPreference = "Stop"
$utf8 = New-Object System.Text.UTF8Encoding $false
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
$temporaryBody = $null
$locationChanged = $false

function Resolve-Tool([string]$Configured, [string]$Name) {
    $candidate = if ([string]::IsNullOrWhiteSpace($Configured)) { $Name } else { $Configured }
    $command = Get-Command -Name $candidate -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $command) { throw "找不到 $Name；请配置对应的 EXE 环境变量或将其加入 PATH。" }
    return $command.Source
}

function Invoke-Tool([string]$Executable, [string[]]$Arguments) {
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $message = & $Executable @Arguments 2>&1 | Out-String
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($code -ne 0) { throw "$Executable 失败（$code）：$message" }
    if (-not [string]::IsNullOrWhiteSpace($message)) { Write-Host $message.TrimEnd() }
}

try {
    $Md = (Resolve-Path -LiteralPath $Md).Path
    if (-not (Test-Path -LiteralPath $Md -PathType Leaf) -or [IO.Path]::GetExtension($Md) -ine ".md") {
        throw "输入必须是 Markdown (.md) 文件。"
    }
    $directory = [IO.Path]::GetDirectoryName($Md)
    $stem = [IO.Path]::GetFileNameWithoutExtension($Md)
    $pdf = Join-Path $directory ($stem + ".pdf")
    $typ = Join-Path $directory ($stem + ".typ")
    foreach ($target in @($pdf, $typ)) {
        if (Test-Path -LiteralPath $target) { throw "输出已存在，拒绝覆盖：$target" }
    }
    $pandoc = Resolve-Tool $env:PANDOC_EXE "pandoc"
    $typst = Resolve-Tool $env:TYPST_EXE "typst"
    $sourceTemplate = Join-Path $PSScriptRoot "templates\math-doc.typ"
    if (-not (Test-Path -LiteralPath $sourceTemplate -PathType Leaf)) { throw "仓库缺少 templates\math-doc.typ。" }
    $template = Join-Path $directory "math-doc.typ"
    if (Test-Path -LiteralPath $template) {
        if (-not (Test-Path -LiteralPath $template -PathType Leaf) -or
            (Get-FileHash -LiteralPath $template -Algorithm SHA256).Hash -ne
            (Get-FileHash -LiteralPath $sourceTemplate -Algorithm SHA256).Hash) {
            throw "输入目录中的 math-doc.typ 与仓库模板不同，拒绝覆盖。"
        }
    } else {
        [IO.File]::Copy($sourceTemplate, $template, $false)
    }

    Push-Location -LiteralPath $directory
    $locationChanged = $true
    $temporaryBody = Join-Path $directory (".md2pdf-" + [guid]::NewGuid().ToString("N") + ".typ")
    Invoke-Tool -Executable $pandoc -Arguments @($Md, "-f", "markdown+tex_math_dollars", "-t", "typst", "--wrap=none", "-o", $temporaryBody)
    if (-not (Test-Path -LiteralPath $temporaryBody -PathType Leaf) -or (Get-Item -LiteralPath $temporaryBody).Length -eq 0) {
        throw "Pandoc 未生成非空 Typst 源码。"
    }
    $title = ConvertTo-Json -InputObject $stem -Compress
    $header = '#import "math-doc.typ": *' + "`n" + '#show: doc.with(title: ' + $title + ', author: "")' + "`n`n"
    $body = [IO.File]::ReadAllText($temporaryBody, [Text.Encoding]::UTF8)
    # CreateNew 也防止校验后出现的新文件被覆盖。
    $stream = [IO.File]::Open($typ, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
    try {
        $bytes = $utf8.GetBytes($header + $body)
        $stream.Write($bytes, 0, $bytes.Length)
    } finally {
        $stream.Dispose()
    }
    Invoke-Tool -Executable $typst -Arguments @("compile", $typ, $pdf)
    if (-not (Test-Path -LiteralPath $pdf -PathType Leaf) -or (Get-Item -LiteralPath $pdf).Length -eq 0) {
        throw "Typst 未生成非空 PDF。"
    }
    $previewPattern = Join-Path $directory ($stem + "-preview-{p}.png")
    Invoke-Tool -Executable $typst -Arguments @("compile", "--format", "png", "--ppi", "110", $typ, $previewPattern)
    $previews = @(Get-ChildItem -LiteralPath $directory -File | Where-Object {
        $_.Name.StartsWith($stem + "-preview-") -and $_.Extension -ieq ".png" -and $_.Length -gt 0
    })
    if ($previews.Count -eq 0) { throw "Typst 未生成 PNG 页面预览。" }
    Write-Host "完成 → $pdf" -ForegroundColor Green
    Write-Host "源码：$typ；请检查保留的 PNG 页面预览。"
} catch {
    [Console]::Error.WriteLine("失败：" + $_.Exception.Message)
    exit 1
} finally {
    if ($locationChanged) { Pop-Location }
    if ($null -ne $temporaryBody -and (Test-Path -LiteralPath $temporaryBody -PathType Leaf)) {
        Remove-Item -LiteralPath $temporaryBody -Force -ErrorAction SilentlyContinue
    }
}
exit 0