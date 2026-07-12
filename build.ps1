param(
    [switch]$Silent
)

$imageName = "mahsol-api"
$containerName = "mahsol-api"

Write-Output "🔨 Building image..."
docker build -t $imageName -f Dockerfile .
if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Build failed"
    exit 1
}

Write-Output "🗑️ Deleting the old container..."
docker rm -f $containerName 2>$null

Write-Output "🚀 Running the new container..."
docker run -d -p 8000:8000 --env-file .env --name $containerName $imageName

Write-Output "✅ API running at http://localhost:8000 — watch logs with: docker logs -f $containerName"

if (-not $Silent) {
    Write-Output "📜 Following logs (Ctrl+C to detach, container keeps running)..."
    docker logs -f $containerName
}
