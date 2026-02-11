# SOC Copilot API 端点测试脚本
$baseUrl = 'http://localhost:3000'
$token = $null

Write-Host "=== SOC Copilot API 端点测试 ===" -ForegroundColor Cyan
Write-Host ""

# 1. 健康检查端点
Write-Host "1. 测试健康检查端点 (GET /api/health)" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/health" -Method GET -TimeoutSec 15 -UseBasicParsing
    Write-Host "   状态码: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "   响应内容: $($response.Content)" -ForegroundColor Gray
} catch {
    Write-Host "   错误: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        Write-Host "   状态码: $([int]$_.Exception.Response.StatusCode)" -ForegroundColor Red
    }
}
Write-Host ""

# 2. 登录端点
Write-Host "2. 测试登录端点 (POST /api/auth/login)" -ForegroundColor Yellow
$loginBody = @{ username = "admin"; password = "admin123!" } | ConvertTo-Json
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/api/auth/login" -Method POST -Body $loginBody -ContentType "application/json" -TimeoutSec 15 -UseBasicParsing -SessionVariable session
    Write-Host "   状态码: $($response.StatusCode)" -ForegroundColor Green
    $loginResponse = $response.Content | ConvertFrom-Json
    Write-Host "   响应内容: $($response.Content)" -ForegroundColor Gray
    if ($loginResponse.access_token) {
        $token = $loginResponse.access_token
        Write-Host "   Token获取成功!" -ForegroundColor Green
    }
} catch {
    Write-Host "   错误: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        Write-Host "   状态码: $([int]$_.Exception.Response.StatusCode)" -ForegroundColor Red
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $reader.BaseStream.Position = 0
        $reader.DiscardBufferedData()
        $errorBody = $reader.ReadToEnd()
        Write-Host "   响应内容: $errorBody" -ForegroundColor Red
    }
}
Write-Host ""

# 3. 获取 Playbook 列表
Write-Host "3. 测试获取 Playbook 列表 (GET /api/playbook/playbooks)" -ForegroundColor Yellow
if ($token) {
    $headers = @{ "Authorization" = "Bearer $token" }
    try {
        $response = Invoke-WebRequest -Uri "$baseUrl/api/playbook/playbooks" -Method GET -Headers $headers -TimeoutSec 15 -UseBasicParsing
        Write-Host "   状态码: $($response.StatusCode)" -ForegroundColor Green
        $content = $response.Content
        if ($content.Length -gt 200) { $content = $content.Substring(0, 200) + "..." }
        Write-Host "   响应内容: $content" -ForegroundColor Gray
    } catch {
        Write-Host "   错误: $($_.Exception.Message)" -ForegroundColor Red
        if ($_.Exception.Response) {
            Write-Host "   状态码: $([int]$_.Exception.Response.StatusCode)" -ForegroundColor Red
        }
    }
} else {
    Write-Host "   跳过: 未获取到 Token" -ForegroundColor Gray
}
Write-Host ""

# 4. 获取资产列表
Write-Host "4. 测试获取资产列表 (GET /api/assets)" -ForegroundColor Yellow
if ($token) {
    $headers = @{ "Authorization" = "Bearer $token" }
    try {
        $response = Invoke-WebRequest -Uri "$baseUrl/api/assets" -Method GET -Headers $headers -TimeoutSec 15 -UseBasicParsing
        Write-Host "   状态码: $($response.StatusCode)" -ForegroundColor Green
        $content = $response.Content
        if ($content.Length -gt 200) { $content = $content.Substring(0, 200) + "..." }
        Write-Host "   响应内容: $content" -ForegroundColor Gray
    } catch {
        Write-Host "   错误: $($_.Exception.Message)" -ForegroundColor Red
        if ($_.Exception.Response) {
            Write-Host "   状态码: $([int]$_.Exception.Response.StatusCode)" -ForegroundColor Red
        }
    }
} else {
    Write-Host "   跳过: 未获取到 Token" -ForegroundColor Gray
}
Write-Host ""

# 5. 获取历史记录
Write-Host "5. 测试获取历史记录 (GET /api/history)" -ForegroundColor Yellow
if ($token) {
    $headers = @{ "Authorization" = "Bearer $token" }
    try {
        $response = Invoke-WebRequest -Uri "$baseUrl/api/history" -Method GET -Headers $headers -TimeoutSec 15 -UseBasicParsing
        Write-Host "   状态码: $($response.StatusCode)" -ForegroundColor Green
        $content = $response.Content
        if ($content.Length -gt 200) { $content = $content.Substring(0, 200) + "..." }
        Write-Host "   响应内容: $content" -ForegroundColor Gray
    } catch {
        Write-Host "   错误: $($_.Exception.Message)" -ForegroundColor Red
        if ($_.Exception.Response) {
            Write-Host "   状态码: $([int]$_.Exception.Response.StatusCode)" -ForegroundColor Red
        }
    }
} else {
    Write-Host "   跳过: 未获取到 Token" -ForegroundColor Gray
}
Write-Host ""

Write-Host "=== 测试完成 ===" -ForegroundColor Cyan
