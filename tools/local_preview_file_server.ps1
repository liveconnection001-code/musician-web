param(
    [Parameter(Mandatory = $true)]
    [string]$ServeRoot,
    [int]$Port = 3110
)

$resolvedServeRoot = [System.IO.Path]::GetFullPath($ServeRoot)
$listener = [System.Net.HttpListener]::new()
$listener.Prefixes.Add("http://127.0.0.1:$Port/")
$listener.Start()

try {
    while ($listener.IsListening) {
        $context = $listener.GetContext()
        $response = $context.Response
        $response.Headers['Access-Control-Allow-Origin'] = '*'
        $response.Headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        $response.Headers['Access-Control-Allow-Headers'] = '*'

        if ($context.Request.HttpMethod -eq 'OPTIONS') {
            $response.StatusCode = 204
            $response.Close()
            continue
        }

        $relativePath = [System.Uri]::UnescapeDataString($context.Request.Url.AbsolutePath.TrimStart('/'))
        $candidatePath = [System.IO.Path]::GetFullPath((Join-Path $resolvedServeRoot $relativePath))

        if (-not $candidatePath.StartsWith($resolvedServeRoot, [System.StringComparison]::OrdinalIgnoreCase) -or -not [System.IO.File]::Exists($candidatePath)) {
            $response.StatusCode = 404
            $response.Close()
            continue
        }

        $extension = [System.IO.Path]::GetExtension($candidatePath).ToLowerInvariant()
        $response.ContentType = switch ($extension) {
            '.jpg' { 'image/jpeg' }
            '.jpeg' { 'image/jpeg' }
            '.png' { 'image/png' }
            '.css' { 'text/css; charset=utf-8' }
            '.html' { 'text/html; charset=utf-8' }
            default { 'application/octet-stream' }
        }

        $bytes = [System.IO.File]::ReadAllBytes($candidatePath)
        $response.ContentLength64 = $bytes.Length
        $response.OutputStream.Write($bytes, 0, $bytes.Length)
        $response.OutputStream.Close()
    }
}
finally {
    $listener.Stop()
    $listener.Close()
}
