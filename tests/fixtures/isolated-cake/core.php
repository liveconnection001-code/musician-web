<?php

Configure::write('debug', 0);
Configure::write('App.encoding', 'UTF-8');
Configure::write('Error', array('handler' => 'ErrorHandler::handleError', 'level' => E_ALL & ~E_DEPRECATED, 'trace' => true));
Configure::write('Exception', array('handler' => 'ErrorHandler::handleException', 'renderer' => 'ExceptionRenderer', 'log' => true));
$contactTestSecuritySalt = getenv('MUSICIAN_CONTACT_TEST_SECURITY_SALT');
if ($contactTestSecuritySalt === false || $contactTestSecuritySalt === '') {
    throw new RuntimeException('MUSICIAN_CONTACT_TEST_SECURITY_SALT is required for the isolated contact test.');
}
Configure::write('Security.salt', $contactTestSecuritySalt);
Configure::write('Cache.check', false);
Configure::write('Session', array('defaults' => 'php'));
