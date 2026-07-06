# Windows 작업 스케줄러에 매일 아침 뉴스 다이제스트 실행 작업을 등록합니다.
# 사용법: PowerShell에서 이 스크립트를 실행하세요. (예: .\register_task.ps1)
# 사전 준비: 실행파일\NewsDigest.exe 가 빌드되어 있어야 하고, 실행파일\config.yaml 이 채워져 있어야 합니다.

# NewsDigest.exe는 sys.executable 기준으로 자기 폴더를 찾으므로(작업 디렉터리에 의존하지 않음)
# 배치파일로 감쌀 필요 없이 exe를 직접 실행하면 된다. (.bat 경유 방식은 한글 폴더명이 배치파일의
# legacy OEM 코드페이지 파싱과 충돌해 깨지는 문제가 있어 제거함)
$exePath    = Join-Path $PSScriptRoot "..\실행파일\NewsDigest.exe"
$configPath = Join-Path $PSScriptRoot "..\실행파일\config.yaml"
$taskName   = "MorningNewsDigest"
$startTime  = "07:00"

if (-not (Test-Path $exePath)) {
    Write-Error "NewsDigest.exe를 찾을 수 없습니다: $exePath"
    exit 1
}

# config.yaml의 schedule.run_time 값을 그대로 사용한다(설정 마법사에서 고른 시간이 실제 스케줄에
# 반영되도록). 정식 YAML 파서 없이 간단한 정규식으로만 추출하며, 못 찾으면 기본값 07:00을 쓴다.
if (Test-Path $configPath) {
    $match = Select-String -Path $configPath -Pattern 'run_time:\s*"?([0-2][0-9]:[0-5][0-9])"?' | Select-Object -First 1
    if ($match) {
        $startTime = $match.Matches[0].Groups[1].Value
    }
}

# schtasks의 /TR 값에 공백이 포함된 경로를 줄 때는 이스케이프된 큰따옴표(\")로
# 감싸야 schtasks가 경로 전체를 하나의 Command로 인식한다(그렇지 않으면 첫 공백에서
# Command/Arguments가 잘못 분리된다). PowerShell의 네이티브 인자 전달 방식과 충돌하므로
# 커맨드 문자열을 직접 조립한 뒤 Invoke-Expression으로 실행한다.
$command = 'schtasks /Create /TN "' + $taskName + '" /SC DAILY /ST ' + $startTime + ' /RL LIMITED /F --% /TR "\"' + $exePath + '\""'
Invoke-Expression $command

Write-Host ""
Write-Host "등록 완료: '$taskName' 작업이 매일 $startTime 에 실행되도록 등록되었습니다."
Write-Host "지금 바로 테스트하려면: schtasks /Run /TN $taskName"
Write-Host "결과 확인:            schtasks /Query /TN $taskName /V /FO LIST"
