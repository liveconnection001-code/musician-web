<?php

Configure::write('debug', 0);
Configure::write('App.encoding', 'UTF-8');
Configure::write('Error', array('handler' => 'ErrorHandler::handleError', 'level' => E_ALL & ~E_DEPRECATED, 'trace' => true));
Configure::write('Exception', array('handler' => 'ErrorHandler::handleException', 'renderer' => 'ExceptionRenderer', 'log' => true));
Configure::write('Security.salt', 'musician-contact-isolated-test-salt-20260804');
Configure::write('Security.cipherSeed', '76859309657453542496749683645');
Configure::write('Cache.check', false);
Configure::write('Session', array('defaults' => 'php'));
