$path = "C:\Users\Administrator\Documents\trae_projects\AI网文小说项目\认亲后，大家的画风一起跑偏了\正文\第3章 你好，顾家.md"
$content = Get-Content $path -Raw -Encoding UTF8
$chineseChars = [regex]::Matches($content, '[\u4e00-\u9fff]').Count
Write-Host "Chinese chars: $chineseChars"
