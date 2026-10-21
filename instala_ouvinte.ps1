# Cria (ou refaz) a tarefa ProspBot-iniciar: mantém o ouvinte.py (bot do Telegram da prospecção) sempre ligado.
# Mesmo jeito do Choppy (tarefa do Agendador, sem janela), mas com nome e bot próprios; nada do PCM-* é tocado.
#   - sobe no logon e a cada 5 min: se já está rodando, o Agendador ignora (IgnoreNew); se caiu, sobe de novo;
#   - sem limite de tempo de execução (o ouvinte fica em long polling para sempre);
#   - pythonw.exe: sem console nenhum (o ouvinte só escreve em ouvinte.log).
#
#   powershell -ExecutionPolicy Bypass -File instala_ouvinte.ps1            # instala e já liga
#   powershell -ExecutionPolicy Bypass -File instala_ouvinte.ps1 -Remover   # tira a tarefa e para o ouvinte
param([switch]$Remover)
$ErrorActionPreference = "Stop"
$pasta = $PSScriptRoot
$nome  = "ProspBot-iniciar"
# Python direto pelo caminho: o "python" do PATH desta máquina aponta para um venv de outra coisa
$pyw   = "$env:LOCALAPPDATA\Programs\Python\Python312\pythonw.exe"

if ($Remover) {
  Stop-ScheduledTask -TaskName $nome -ErrorAction SilentlyContinue
  Unregister-ScheduledTask -TaskName $nome -Confirm:$false -ErrorAction SilentlyContinue
  "removida"; return
}
if (-not (Test-Path $pyw)) { throw "pythonw 3.12 não encontrado em $pyw" }

$acao = New-ScheduledTaskAction -Execute $pyw -Argument "`"$pasta\ouvinte.py`"" -WorkingDirectory $pasta
$logon = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$cada5 = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
$opc  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
          -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew `
          -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$quem = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $nome -Action $acao -Trigger @($logon, $cada5) -Settings $opc -Principal $quem -Force `
  -Description "Bot do Telegram da prospecção (@ProspeccaoJoaoLeite_bot): responde ao João na hora (ouvinte.py)" | Out-Null
Start-ScheduledTask -TaskName $nome
"$nome instalada e ligada. Log: $pasta\ouvinte.log  |  Testar: mande 'status' para o bot."
