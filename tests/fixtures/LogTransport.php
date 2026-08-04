<?php

App::uses('AbstractTransport', 'Network/Email');

/**
 * Isolated-test transport. It records mail bodies locally and never opens SMTP.
 */
class LogTransport extends AbstractTransport {
  public function send(CakeEmail $email) {
    $path = getenv('MUSICIAN_CONTACT_TEST_LOG');
    if ($path === false || $path === '') {
      throw new RuntimeException('MUSICIAN_CONTACT_TEST_LOG is required for LogTransport.');
    }

    $entry = array(
        'headers' => $email->getHeaders(array('from', 'sender', 'replyTo', 'to', 'subject')),
        'message' => implode("\r\n", (array)$email->message()),
    );
    $encoded = json_encode($entry, JSON_UNESCAPED_UNICODE);
    if ($encoded === false || file_put_contents($path, $encoded . "\n", FILE_APPEND | LOCK_EX) === false) {
      throw new RuntimeException('Unable to write isolated contact mail log.');
    }
    return array('headers' => $entry['headers'], 'message' => $entry['message']);
  }
}
