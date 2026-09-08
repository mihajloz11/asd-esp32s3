param([string[]]$Paths)

$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    foreach ($path in $Paths) {
        $absolute = (Resolve-Path -LiteralPath $path).Path
        $document = $word.Documents.Open($absolute, $false, $false)
        try {
            $null = $document.Fields.Update()
            foreach ($toc in $document.TablesOfContents) { $toc.Update() }
            foreach ($list in $document.TablesOfFigures) { $list.Update() }
            $document.Repaginate()
            $null = $document.Fields.Update()
            $document.Save()
            $pdf = [IO.Path]::ChangeExtension($absolute, '.pdf')
            $document.ExportAsFixedFormat($pdf, 17)
            $repository = Split-Path -Parent $PSScriptRoot
            [PSCustomObject]@{
                File = [IO.Path]::GetRelativePath($repository, $absolute).Replace('\', '/')
                Pages = $document.ComputeStatistics(2)
                Pdf = [IO.Path]::GetRelativePath($repository, $pdf).Replace('\', '/')
            }
        } finally { $document.Close(0) }
    }
} finally {
    $word.Quit()
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)
}
