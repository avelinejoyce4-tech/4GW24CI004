param(
  [Parameter(Mandatory=$true)]
  [string]$Path,
  [string]$Culture = "en-US"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech

$engine = $null
try {
  $cultureInfo = [Globalization.CultureInfo]$Culture
  $engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine($cultureInfo)
  $resolvedPath = (Resolve-Path -LiteralPath $Path).ProviderPath
  $engine.SetInputToWaveFile($resolvedPath)
  $engine.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
  $parts = New-Object System.Collections.Generic.List[string]
  $deadline = (Get-Date).AddSeconds(120)

  while ((Get-Date) -lt $deadline) {
    try {
      $result = $engine.Recognize([TimeSpan]::FromSeconds(8))
    }
    catch [System.InvalidOperationException] {
      break
    }
    if ($null -eq $result) {
      break
    }
    if ($result.Text) {
      $parts.Add($result.Text)
    }
  }

  [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
  Write-Output ($parts -join " ")
}
finally {
  if ($engine -ne $null) {
    $engine.Dispose()
  }
}
