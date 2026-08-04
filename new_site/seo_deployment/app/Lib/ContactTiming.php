<?php

/**
 * Contactフォームの表示時刻トークンを発行・検証する。
 * 署名鍵は既存のCakePHP設定からだけ取得し、コードや出力へ含めない。
 */
class ContactTiming {

  const PURPOSE = 'musician-contact-timing-v1';
  const MIN_SECONDS = 5;
  const MAX_SECONDS = 86400;

  public static function issue($issuedAt = null) {
    $issuedAt = $issuedAt === null ? time() : (int)$issuedAt;
    $signature = self::signature($issuedAt);
    return $signature === null ? '' : $issuedAt . '.' . $signature;
  }

  public static function isValid($token) {
    if (!is_string($token) || !preg_match('/^([0-9]{1,11})\.([a-f0-9]{64})$/', $token, $matches)) {
      return false;
    }

    $issuedAt = (int)$matches[1];
    $expected = self::signature($issuedAt);
    if ($expected === null || !self::secureEquals($expected, $matches[2])) {
      return false;
    }

    $elapsed = time() - $issuedAt;
    return $elapsed >= self::MIN_SECONDS && $elapsed <= self::MAX_SECONDS;
  }

  private static function signature($issuedAt) {
    $secret = Configure::read('Security.salt');
    if (!is_string($secret) || $secret === '') {
      return null;
    }
    return hash_hmac('sha256', self::PURPOSE . '|' . (int)$issuedAt, $secret);
  }

  private static function secureEquals($expected, $actual) {
    if (function_exists('hash_equals')) {
      return hash_equals($expected, $actual);
    }
    if (strlen($expected) !== strlen($actual)) {
      return false;
    }
    $difference = 0;
    for ($index = 0; $index < strlen($expected); $index++) {
      $difference |= ord($expected[$index]) ^ ord($actual[$index]);
    }
    return $difference === 0;
  }
}
