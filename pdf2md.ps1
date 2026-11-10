# 用法：pdf2md "F:\某本书.pdf" [all|1-5,8]
# 输出：输入同级的 <书名>_mineru[_p<页码>]\<书名>.md；已有目录不会复用。
param(
    [Parameter(Mandatory = $true)][string]$Pdf,
    [string]$Pages = "all"
)

$ErrorActionPreference = "Stop"
$utf8 = New-Object System.Text.UTF8Encoding $false
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
$env:PYTHONIOENCODING = "utf-8"

function Resolve-MinerU {
    if (-not [string]::IsNullOrWhiteSpace($env:MINERU_EXE)) {
        $candidate = $env:MINERU_EXE
    } else {
        $localExe = Join-Path $PSScriptRoot "venv\Scripts\mineru.exe"
        if (Test-Path -LiteralPath $localExe -PathType Leaf) { return $localExe }
        $candidate = "mineru"
    }
    $command = Get-Command -Name $candidate -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $command) { throw "找不到 MinerU；请设置 MINERU_EXE 或将 mineru 加入 PATH。" }
    return $command.Source
}

function Invoke-MinerU([string[]]$Arguments) {
    # Windows PowerShell 5.1 将原生命令的 stderr 转成错误记录；按退出码判定成功。
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        $message = & $script:MinerU @Arguments 2>&1 | Out-String
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    return [pscustomobject]@{ Code = $code; Message = $message }
}

try {
    $Pages = $Pages.Trim()
    if ($Pages -ieq "all") {
        $Pages = "all"
    } else {
        if ($Pages -notmatch '^[1-9][0-9]*(?:-[1-9][0-9]*)?(?:,[1-9][0-9]*(?:-[1-9][0-9]*)?)*$') {
            throw "页码必须为 all、正整数或有序范围，例如 1-5,8。"
        }
        foreach ($selection in $Pages.Split(',')) {
            $ends = $selection.Split('-')
            $startPage = [long]::Parse($ends[0])
            if ($ends.Length -eq 2 -and $startPage -gt [long]::Parse($ends[1])) {
                throw "页码范围起点不能大于终点：$selection"
            }
        }
    }

    $Pdf = (Resolve-Path -LiteralPath $Pdf).Path
    if (-not (Test-Path -LiteralPath $Pdf -PathType Leaf) -or [IO.Path]::GetExtension($Pdf) -ine ".pdf") {
        throw "输入必须是 PDF 文件。"
    }
    $stem = [IO.Path]::GetFileNameWithoutExtension($Pdf)
    $suffix = if ($Pages -eq "all") { "" } else { "_p$Pages" }
    $outputDirectory = Join-Path ([IO.Path]::GetDirectoryName($Pdf)) ($stem + "_mineru" + $suffix)
    if (Test-Path -LiteralPath $outputDirectory) { throw "输出目录已存在，拒绝覆盖：$outputDirectory" }
    $script:MinerU = Resolve-MinerU
    if ([string]::IsNullOrWhiteSpace($env:MINERU_HOME)) {
        $env:MINERU_HOME = Join-Path $PSScriptRoot "home"
    }
    $tier = if ([string]::IsNullOrWhiteSpace($env:MINERU_TIER)) { "standard" } else { $env:MINERU_TIER }
    $outputFile = Join-Path $outputDirectory ($stem + ".md")
    New-Item -ItemType Directory -Path $outputDirectory -ErrorAction Stop | Out-Null

    Write-Host "启动 MinerU 本地服务（已运行则跳过）..."
    $started = Invoke-MinerU -Arguments @("server", "start")
    if ($started.Code -ne 0) { throw "MinerU 服务启动失败（$($started.Code)）：$($started.Message)" }
    Write-Host "正在转换：$Pdf  页码：$Pages"
    for ($attempt = 0; $attempt -lt 12; $attempt++) {
        $result = Invoke-MinerU -Arguments @("parse", $Pdf, "-p", $Pages, "--tier", $tier, "--wait", "86400", "-o", $outputFile)
        if ($result.Message -match "not ready" -and $attempt -lt 11) {
            Write-Host "解析引擎仍在加载，10 秒后重试..."
            Start-Sleep -Seconds 10
            continue
        }
        if ($result.Code -ne 0) { throw "MinerU 解析失败（$($result.Code)）：$($result.Message)" }
        if ($result.Message -match "not ready") { throw "MinerU 在有限重试后仍未就绪。" }
        if (-not (Test-Path -LiteralPath $outputFile -PathType Leaf) -or (Get-Item -LiteralPath $outputFile).Length -eq 0) {
            throw "MinerU 未生成非空 Markdown：$outputFile"
        }
        Write-Host "完成 → $outputFile" -ForegroundColor Green
        exit 0
    }
    throw "MinerU 解析未完成。"
} catch {
    [Console]::Error.WriteLine("失败：" + $_.Exception.Message)
    exit 1
}