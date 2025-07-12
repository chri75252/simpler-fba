# PowerShell script to identify and delete Amazon cache files with incomplete Keepa data

$files = Get-ChildItem *.json
$filesToDelete = @()
$validFiles = @()

Write-Host "Analyzing $($files.Count) Amazon cache files..."

foreach ($file in $files) {
    try {
        $content = Get-Content $file.FullName -Raw | ConvertFrom-Json
        
        # Check if Keepa data is missing or incomplete
        if ($content.keepa.status -eq "Product details tab timeout (initial)" -or 
            -not $content.keepa.product_details_tab_data -or
            $content.keepa.status -like "*timeout*") {
            $filesToDelete += $file.Name
        } else {
            $validFiles += $file.Name
        }
    } catch {
        Write-Host "Error processing $($file.Name) - will delete"
        $filesToDelete += $file.Name
    }
}

Write-Host ""
Write-Host "ANALYSIS COMPLETE:"
Write-Host "Files with missing/incomplete Keepa data: $($filesToDelete.Count)"
Write-Host "Files with valid Keepa data: $($validFiles.Count)"
Write-Host ""

if ($filesToDelete.Count -gt 0) {
    Write-Host "Files to be deleted (first 20):"
    $filesToDelete[0..19] | ForEach-Object { Write-Host "  - $_" }
    
    Write-Host ""
    $confirm = Read-Host "Do you want to delete these $($filesToDelete.Count) files? (y/N)"
    
    if ($confirm -eq "y" -or $confirm -eq "Y") {
        Write-Host "Deleting files..."
        foreach ($fileName in $filesToDelete) {
            try {
                Remove-Item $fileName -Force
                Write-Host "Deleted: $fileName"
            } catch {
                Write-Host "Error deleting $fileName : $_"
            }
        }
        Write-Host ""
        Write-Host "Cleanup complete! Deleted $($filesToDelete.Count) files with incomplete Keepa data."
    } else {
        Write-Host "Cleanup cancelled."
    }
} else {
    Write-Host "No files need to be deleted - all have valid Keepa data!"
}
