<?php
$controller = dirname(__DIR__) . DIRECTORY_SEPARATOR . 'Controller' . DIRECTORY_SEPARATOR . 'AppController.php';
$expected_hash = '5c869739e93b7513cad9a0cc60c3639aa311f11b4d62578b207ce1f53ad56b06';
$provided_hash = isset($_SERVER['HTTP_X_MUSICIAN_RELEASE']) ? strtolower(trim($_SERVER['HTTP_X_MUSICIAN_RELEASE'])) : '';

if ($_SERVER['REQUEST_METHOD'] !== 'POST'
    || !hash_equals($expected_hash, $provided_hash)
    || !is_file($controller)
    || hash_file('sha256', $controller) !== $expected_hash) {
  http_response_code(404);
  exit;
}

$invalidated = true;
if (function_exists('opcache_invalidate')) {
  $invalidated = @opcache_invalidate($controller, true);
}

@unlink(__FILE__);
header('Cache-Control: no-store, no-cache, must-revalidate');
header('Content-Type: application/json; charset=UTF-8');
echo json_encode(array(
  'controller_hash' => $expected_hash,
  'opcache_invalidate' => (bool)$invalidated,
  'self_removed' => !is_file(__FILE__),
));
