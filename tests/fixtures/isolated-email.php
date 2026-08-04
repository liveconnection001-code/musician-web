<?php

/**
 * Replaces the copied production email configuration only inside CI's temporary
 * CakePHP root. The Log transport does not perform network delivery.
 */
class EmailConfig {
  public $default = array(
      'transport' => 'Log',
      'from' => 'noreply@example.test',
      'charset' => 'utf-8',
      'headerCharset' => 'utf-8',
  );
}
