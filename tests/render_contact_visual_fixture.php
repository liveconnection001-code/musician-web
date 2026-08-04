<?php

$template = getenv('MUSICIAN_CONTACT_TEMPLATE');
if ($template === false || $template === '') {
  fwrite(STDERR, "MUSICIAN_CONTACT_TEMPLATE is required.\n");
  exit(2);
}

function h($value) {
  return htmlspecialchars($value, ENT_QUOTES, 'UTF-8');
}

class ContactVisualHtmlHelper {
  public function url($url) {
    return '/contact/postmail';
  }
}

class ContactVisualRenderer {
  public $Html;

  public function __construct() {
    $this->Html = new ContactVisualHtmlHelper();
  }

  public function element($name, $data = array()) {
    return '';
  }

  public function render($template) {
    $contact_timing = 'visual-fixture-token';
    include $template;
  }
}

$renderer = new ContactVisualRenderer();
$renderer->render($template);
