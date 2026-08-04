<?php

/**
 * CakePHP 2.10.18上で、MUSICIANお問い合わせフォームの送信前経路を隔離検証する。
 * このテストは専用のLogTransportだけを使い、SMTPへは接続しない。
 */

$root = getenv('MUSICIAN_CONTACT_TEST_ROOT');
$mailLog = getenv('MUSICIAN_CONTACT_TEST_LOG');
if ($root === false || $root === '' || $mailLog === false || $mailLog === '') {
  fwrite(STDERR, "MUSICIAN_CONTACT_TEST_ROOT and MUSICIAN_CONTACT_TEST_LOG are required.\n");
  exit(2);
}

if (getenv('MUSICIAN_CONTACT_TEST_SECURITY_SALT') === false || getenv('MUSICIAN_CONTACT_TEST_SECURITY_SALT') === '') {
  putenv('MUSICIAN_CONTACT_TEST_SECURITY_SALT=' . bin2hex(random_bytes(32)));
}

define('DS', DIRECTORY_SEPARATOR);
define('ROOT', rtrim($root, DS));
define('APP_DIR', 'app');
define('WEBROOT_DIR', 'webroot');
define('WWW_ROOT', ROOT . DS . APP_DIR . DS . WEBROOT_DIR . DS);
define('CAKE_CORE_INCLUDE_PATH', ROOT . DS . 'vendor' . DS . 'cakephp' . DS . 'cakephp' . DS . 'lib');

require CAKE_CORE_INCLUDE_PATH . DS . 'Cake' . DS . 'bootstrap.php';

require ROOT . DS . 'app' . DS . 'Lib' . DS . 'ContactTiming.php';
require ROOT . DS . 'app' . DS . 'Model' . DS . 'AppModel.php';
require ROOT . DS . 'app' . DS . 'Model' . DS . 'MailSend.php';
require ROOT . DS . 'app' . DS . 'Model' . DS . 'ContactMailSend.php';
require ROOT . DS . 'app' . DS . 'Controller' . DS . 'AppController.php';
require ROOT . DS . 'app' . DS . 'Controller' . DS . 'ContactController.php';
require ROOT . DS . 'app' . DS . 'Network' . DS . 'Email' . DS . 'LogTransport.php';

class ContactTestSmtp {
  public function find($type, $options = array()) {
    return array();
  }
}

class ContactTestSession {
  public $values = array();

  public function read($key) {
    return isset($this->values[$key]) ? $this->values[$key] : null;
  }

  public function write($key, $value) {
    $this->values[$key] = $value;
  }

  public function delete($key) {
    unset($this->values[$key]);
  }
}

class ContactTestMailSend {
  public $data;
  public $spamChecked = false;

  public function set($data) {
    $this->data = $data;
  }

  public function spamCheck() {
    $this->spamChecked = true;
  }
}

class ContactTestHtmlHelper {
  public function url($url) {
    return '/contact/postmail';
  }
}

class ContactConfirmationRenderer {
  public $Html;

  public function __construct() {
    $this->Html = new ContactTestHtmlHelper();
  }

  public function render($template, array $confirmData) {
    $confirm_data = $confirmData;
    $contact_token = 'contact-test-token';
    ob_start();
    include $template;
    return ob_get_clean();
  }
}

class ContactControllerTestHarness extends ContactController {
  public $sentForm;
  public $viewVars = array();

  public function sendData($form) {
    $this->sentForm = $form;
  }

  public function set($name, $value = null) {
    if (is_array($name)) {
      foreach ($name as $key => $item) {
        $this->viewVars[$key] = $item;
      }
      return;
    }
    $this->viewVars[$name] = $value;
  }

  public function render($view = null, $layout = null) {
    return $view;
  }
}

function contact_assert($condition, $message) {
  if (!$condition) {
    throw new RuntimeException($message);
  }
}

function contact_assert_same($expected, $actual, $message) {
  if ($expected !== $actual) {
    throw new RuntimeException($message . ' (expected=' . var_export($expected, true) . ', actual=' . var_export($actual, true) . ')');
  }
}

function contact_private($object, $method, array $arguments = array()) {
  $reflection = new ReflectionMethod('ContactController', $method);
  $reflection->setAccessible(true);
  return $reflection->invokeArgs($object, $arguments);
}

function contact_controller() {
  $reflection = new ReflectionClass('ContactControllerTestHarness');
  $controller = $reflection->newInstanceWithoutConstructor();
  $controller->Smtp = new ContactTestSmtp();
  return $controller;
}

function contact_raw_form() {
  return array(
      'inquiry_type' => 'イベント・式典の音楽演出/制作のご相談',
      'company' => 'テスト団体',
      'name' => 'テスト太郎',
      'furigana' => 'テストタロウ',
      'email' => 'contact-test@example.test',
      'tel' => '03-6261-4348',
      'event_date' => '2026-12-15',
      'event_date_tbd' => '',
      'event_pref' => '東京都',
      'venue' => 'テスト会場',
      'attendee_count' => '120名程度',
      'budget' => '30万〜50万円',
      'genre' => '弦楽四重奏',
      'photo_numbers' => '',
      'message' => '隔離環境で確認するお問い合わせ内容です。',
      'agree' => '1',
      'website' => '',
  );
}

function contact_normalised_form($controller, array $raw) {
  return contact_private($controller, 'normaliseForm', array($raw));
}

function contact_model_for(array $form) {
  $model = new ContactMailSend();
  $model->setMailConfigurationId(1);
  $model->set(array('ContactMailSend' => $form));
  $model->validate();
  return $model;
}

function contact_post_controller(array $submitted) {
  $controller = contact_controller();
  $controller->Session = new ContactTestSession();
  $controller->ContactMailSend = new ContactMailSend();
  $controller->ContactMailSend->setMailConfigurationId(1);
  $controller->request = (object)array('data' => array('ContactMailSend' => $submitted));
  return $controller;
}

try {
  $versionContents = file_get_contents(CAKE_CORE_INCLUDE_PATH . DS . 'Cake' . DS . 'VERSION.txt');
  preg_match('/^([0-9]+\.[0-9]+\.[0-9]+)$/m', $versionContents, $versionMatch);
  $version = isset($versionMatch[1]) ? $versionMatch[1] : '';
  contact_assert_same('2.10.18', $version, 'CakePHP core version must be 2.10.18');

  $controller = contact_controller();
  $form = contact_normalised_form($controller, contact_raw_form());
  $model = contact_model_for($form);

  // K-T1: normal input reaches confirmation and both isolated mail bodies.
  $normalSubmission = contact_raw_form();
  $normalSubmission['contact_timing'] = ContactTiming::issue(time() - 5);
  $normalController = contact_post_controller($normalSubmission);
  contact_assert_same('msg', $normalController->postmail(), 'K-T1: normal input must render the confirmation screen');
  $confirmation = $normalController->viewVars['confirm_data'];
  contact_assert(empty($model->error), 'K-T1: fully populated form must validate');
  contact_assert_same('120名程度', $confirmation['想定人数'], 'K-T1: attendee count is missing from confirmation');
  contact_assert(!isset($confirmation['ご覧になった写真番号']), 'K-T1: photo-number label must not appear in confirmation data');
  $confirmationMarkup = (new ContactConfirmationRenderer())->render(ROOT . DS . 'app' . DS . 'View' . DS . 'Contact' . DS . 'msg.html', $confirmation);
  contact_assert(strpos($confirmationMarkup, '<th>想定人数</th>') !== false && strpos($confirmationMarkup, '120名程度') !== false, 'K-T1: attendee count is not rendered by msg.html');
  file_put_contents($mailLog, '');
  $adminText = contact_private($controller, 'buildAdminText', array($form));
  $autoText = contact_private($controller, 'buildAutoReplyText', array($form));
  $autoStatus = contact_private($controller, 'sendContactEmail', array('default', 'customer@example.test', '自動返信テスト', $autoText, 'noreply@example.test'));
  $adminStatus = contact_private($controller, 'sendContactEmail', array('default', 'admin@example.test', '管理者通知テスト', $adminText, 'noreply@example.test', 'customer@example.test'));
  contact_assert_same('送信済み', $autoStatus, 'K-T1: automatic reply was not accepted by LogTransport');
  contact_assert_same('送信済み', $adminStatus, 'K-T1: administrator notification was not accepted by LogTransport');
  $mailEntries = array_values(array_filter(explode("\n", trim(file_get_contents($mailLog)))));
  contact_assert_same(2, count($mailEntries), 'K-T1: LogTransport must receive both emails');
  $mailText = '';
  foreach ($mailEntries as $entry) {
    $decoded = json_decode($entry, true);
    contact_assert(is_array($decoded) && isset($decoded['message']), 'K-T1: mail log entry is invalid');
    $mailText .= $decoded['message'] . "\n";
  }
  $mailText = str_replace("\r\n", "\n", $mailText);
  $expectedAttendee = '【想定人数】' . "\n" . '120名程度';
  contact_assert(substr_count($mailText, $expectedAttendee) === 2, 'K-T1: both mail bodies must include attendee count');
  echo "[PASS] K-T1 normal input reaches confirmation and both isolated mail bodies.\n";

  // K-T2: a filled photo-number honeypot must return thanks without any send path.
  $honeypotSubmission = contact_raw_form();
  $honeypotSubmission['photo_numbers'] = '150';
  $honeypotController = contact_post_controller($honeypotSubmission);
  contact_assert_same('thanks', $honeypotController->postmail(), 'K-T2: filled photo-number honeypot must render thanks');
  contact_assert($honeypotController->sentForm === null, 'K-T2: filled honeypot must not invoke mail sending');
  contact_assert($honeypotController->Session->read('Contact.PendingForm') === null, 'K-T2: filled honeypot must not save pending form data');
  echo "[PASS] K-T2 filled photo_numbers returns thanks without mail.\n";

  // K-T3: a submission under five seconds must preserve user data and show a normal error.
  $fastSubmission = contact_raw_form();
  $fastSubmission['contact_timing'] = ContactTiming::issue();
  $fastController = contact_post_controller($fastSubmission);
  contact_assert_same('/Homes/webroot', $fastController->postmail(), 'K-T3: too-fast input must return to the form');
  contact_assert(isset($fastController->viewVars['contact_errors']['_form']), 'K-T3: too-fast input must have a form error');
  contact_assert_same($fastSubmission['message'], $fastController->viewVars['contact_data']['message'], 'K-T3: too-fast input must preserve message');
  contact_assert($fastController->sentForm === null, 'K-T3: too-fast input must not invoke mail sending');
  echo "[PASS] K-T3 under-five-second input is rejected with preserved data.\n";

  // K-T4: a correctly signed token older than 24 hours must also be rejected.
  $expiredSubmission = contact_raw_form();
  $expiredSubmission['contact_timing'] = ContactTiming::issue(time() - (25 * 60 * 60));
  $expiredController = contact_post_controller($expiredSubmission);
  contact_assert_same('/Homes/webroot', $expiredController->postmail(), 'K-T4: expired input must return to the form');
  contact_assert(isset($expiredController->viewVars['contact_errors']['_form']), 'K-T4: expired input must have a form error');
  contact_assert_same($expiredSubmission['name'], $expiredController->viewVars['contact_data']['name'], 'K-T4: expired input must preserve name');
  echo "[PASS] K-T4 25-hour token is rejected with preserved data.\n";

  // K-T5: photo numbers must not reach confirmation or either email body.
  contact_assert(strpos($confirmationMarkup, 'ご覧になった写真番号') === false, 'K-T5: confirmation must not show photo-number label');
  contact_assert(strpos($mailText, 'ご覧になった写真番号') === false && strpos($mailText, '写真番号：') === false, 'K-T5: mail bodies must not show photo numbers');
  contact_assert(!isset($model->fields[1]['photo_numbers']), 'K-T5: photo numbers must not remain in the mail field definition');
  echo "[PASS] K-T5 confirmation and both mail bodies exclude photo numbers.\n";

  // K-T8 regression: the existing optional and required-field rules and final server-held send remain intact.
  $optionalBlank = $form;
  $optionalBlank['attendee_count'] = '';
  $optionalBlankModel = contact_model_for($optionalBlank);
  contact_assert(empty($optionalBlankModel->error), 'K-T8: blank attendee count must remain valid');
  $requiredLabels = array(
      'inquiry_type' => 'お問い合わせ種別',
      'name' => 'お名前',
      'email' => 'メールアドレス',
      'message' => 'お問い合わせ内容',
      'agree' => '個人情報保護方針への同意',
  );
  foreach ($requiredLabels as $field => $label) {
    $missing = $form;
    $missing[$field] = '';
    $missingModel = contact_model_for($missing);
    contact_assert(isset($missingModel->error[$label]), 'K-T8: required field must fail: ' . $field);
  }
  $telephoneBlank = $form;
  $telephoneBlank['tel'] = '';
  $telephoneBlankModel = contact_model_for($telephoneBlank);
  contact_assert(empty($telephoneBlankModel->error), 'K-T8: blank telephone must remain valid');
  $sendController = contact_controller();
  $sendController->Session = new ContactTestSession();
  $sendController->ContactMailSend = new ContactTestMailSend();
  $pending = $form;
  $pending['attendee_count'] = 'セッション側の想定人数';
  $sendController->Session->values['Contact.PendingForm'] = array('form' => $pending, 'token' => 'contact-test-token');
  $result = contact_private($sendController, 'sendConfirmedForm', array(array(
      'send' => '1',
      'contact_token' => 'contact-test-token',
      'attendee_count' => '改ざん値',
      'photo_numbers' => '改ざん値',
  )));
  contact_assert_same('thanks', $result, 'K-T8: successful confirmation must render thanks');
  contact_assert_same('セッション側の想定人数', $sendController->sentForm['attendee_count'], 'K-T8: final send used client-controlled attendee count');
  contact_assert($sendController->ContactMailSend->spamChecked, 'K-T8: spam check must run before final send');
  contact_assert($sendController->Session->read('Contact.PendingForm') === null, 'K-T8: pending form must be cleared after final send');
  echo "[PASS] K-T8 required fields, optional telephone, server-held confirmation, and thanks transition remain valid.\n";

  echo "[PASS] Isolated CakePHP 2.10.18 contact test completed.\n";
} catch (Exception $exception) {
  fwrite(STDERR, '[FAIL] ' . $exception->getMessage() . "\n");
  exit(1);
}
