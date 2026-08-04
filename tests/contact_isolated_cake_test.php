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

define('DS', DIRECTORY_SEPARATOR);
define('ROOT', rtrim($root, DS));
define('APP_DIR', 'app');
define('WEBROOT_DIR', 'webroot');
define('WWW_ROOT', ROOT . DS . APP_DIR . DS . WEBROOT_DIR . DS);
define('CAKE_CORE_INCLUDE_PATH', ROOT . DS . 'vendor' . DS . 'cakephp' . DS . 'cakephp');

require CAKE_CORE_INCLUDE_PATH . DS . 'lib' . DS . 'Cake' . DS . 'bootstrap.php';

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

  public function sendData($form) {
    $this->sentForm = $form;
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
      'photo_numbers' => '写真番号：１２、No.34、56',
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

try {
  $versionContents = file_get_contents(CAKE_CORE_INCLUDE_PATH . DS . 'lib' . DS . 'Cake' . DS . 'VERSION.txt');
  preg_match('/^([0-9]+\.[0-9]+\.[0-9]+)$/m', $versionContents, $versionMatch);
  $version = isset($versionMatch[1]) ? $versionMatch[1] : '';
  contact_assert_same('2.10.18', $version, 'CakePHP core version must be 2.10.18');

  $controller = contact_controller();
  $form = contact_normalised_form($controller, contact_raw_form());
  $model = contact_model_for($form);

  // T1: all fields must appear in the automatically enumerated confirmation data.
  contact_assert(empty($model->error), 'T1: fully populated form must validate');
  $confirmation = $model->getConfirmData();
  contact_assert_same('120名程度', $confirmation['想定人数'], 'T1: attendee count is missing from confirmation');
  contact_assert_same('写真番号：１２、No.34、56', $confirmation['ご覧になった写真番号'], 'T1: photo numbers are missing from confirmation');
  $confirmationMarkup = (new ContactConfirmationRenderer())->render(ROOT . DS . 'app' . DS . 'View' . DS . 'Contact' . DS . 'msg.html', $confirmation);
  contact_assert(strpos($confirmationMarkup, '<th>想定人数</th>') !== false && strpos($confirmationMarkup, '120名程度') !== false, 'T1: attendee count is not rendered by msg.html');
  contact_assert(strpos($confirmationMarkup, '<th>ご覧になった写真番号</th>') !== false && strpos($confirmationMarkup, '写真番号：１２、No.34、56') !== false, 'T1: photo numbers are not rendered by msg.html');
  echo "[PASS] T1 confirmation lists both new optional fields.\n";

  // T2: send both text bodies through the isolated LogTransport and inspect them.
  file_put_contents($mailLog, '');
  $adminText = contact_private($controller, 'buildAdminText', array($form));
  $autoText = contact_private($controller, 'buildAutoReplyText', array($form));
  $autoStatus = contact_private($controller, 'sendContactEmail', array('default', 'customer@example.test', '自動返信テスト', $autoText, 'noreply@example.test'));
  $adminStatus = contact_private($controller, 'sendContactEmail', array('default', 'admin@example.test', '管理者通知テスト', $adminText, 'noreply@example.test', 'customer@example.test'));
  contact_assert_same('送信済み', $autoStatus, 'T2: automatic reply was not accepted by LogTransport');
  contact_assert_same('送信済み', $adminStatus, 'T2: administrator notification was not accepted by LogTransport');
  $mailEntries = array_values(array_filter(explode("\n", trim(file_get_contents($mailLog)))));
  contact_assert_same(2, count($mailEntries), 'T2: LogTransport must receive both emails');
  $mailText = '';
  foreach ($mailEntries as $entry) {
    $decoded = json_decode($entry, true);
    contact_assert(is_array($decoded) && isset($decoded['message']), 'T2: mail log entry is invalid');
    $mailText .= $decoded['message'] . "\n";
  }
  foreach (array('【想定人数】' . "\n" . '120名程度', '【ご覧になった写真番号】' . "\n" . '写真番号：１２、No.34、56') as $expected) {
    contact_assert(substr_count($mailText, $expected) === 2, 'T2: both mail bodies must include ' . $expected);
  }
  echo "[PASS] T2 LogTransport captured both mail bodies with both new fields.\n";

  // T3: both additions remain optional.
  $optionalBlank = $form;
  $optionalBlank['attendee_count'] = '';
  $optionalBlank['photo_numbers'] = '';
  $optionalBlankModel = contact_model_for($optionalBlank);
  contact_assert(empty($optionalBlankModel->error), 'T3: blank optional fields must not produce validation errors');
  echo "[PASS] T3 both new fields may be blank.\n";

  // T4: each current required field must still reject an empty value.
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
    contact_assert(isset($missingModel->error[$label]), 'T4: required field must fail: ' . $field);
  }
  echo "[PASS] T4 all five required fields reject empty values.\n";

  // T5: telephone remains optional.
  $telephoneBlank = $form;
  $telephoneBlank['tel'] = '';
  $telephoneBlankModel = contact_model_for($telephoneBlank);
  contact_assert(empty($telephoneBlankModel->error), 'T5: blank telephone must remain valid');
  echo "[PASS] T5 telephone may be blank.\n";

  // T6: preserve full-width, half-width and multiple photo numbers in confirmation and both mail bodies.
  $photoValue = '作品１２、No.34、56';
  $photoForm = $form;
  $photoForm['photo_numbers'] = $photoValue;
  $photoModel = contact_model_for($photoForm);
  contact_assert(empty($photoModel->error), 'T6: mixed-width photo numbers must validate');
  contact_assert_same($photoValue, $photoModel->getConfirmData()['ご覧になった写真番号'], 'T6: confirmation changed photo numbers');
  $photoAdmin = contact_private($controller, 'buildAdminText', array($photoForm));
  $photoAuto = contact_private($controller, 'buildAutoReplyText', array($photoForm));
  contact_assert(strpos($photoAdmin, $photoValue) !== false && strpos($photoAuto, $photoValue) !== false, 'T6: mail text changed photo numbers');
  echo "[PASS] T6 mixed-width and multiple photo numbers remain UTF-8 intact.\n";

  // T7: final send must use the server-side pending form and render thanks.
  $sendController = contact_controller();
  $sendController->Session = new ContactTestSession();
  $sendController->ContactMailSend = new ContactTestMailSend();
  $pending = $form;
  $pending['attendee_count'] = 'セッション側の想定人数';
  $pending['photo_numbers'] = 'セッション側の写真番号';
  $sendController->Session->values['Contact.PendingForm'] = array('form' => $pending, 'token' => 'contact-test-token');
  $result = contact_private($sendController, 'sendConfirmedForm', array(array(
      'send' => '1',
      'contact_token' => 'contact-test-token',
      'attendee_count' => '改ざん値',
      'photo_numbers' => '改ざん値',
  )));
  contact_assert_same('thanks', $result, 'T7: successful confirmation must render thanks');
  contact_assert_same('セッション側の想定人数', $sendController->sentForm['attendee_count'], 'T7: final send used a client-controlled attendee count');
  contact_assert_same('セッション側の写真番号', $sendController->sentForm['photo_numbers'], 'T7: final send used client-controlled photo numbers');
  contact_assert($sendController->ContactMailSend->spamChecked, 'T7: spam check must run before final send');
  contact_assert($sendController->Session->read('Contact.PendingForm') === null, 'T7: pending form must be cleared after final send');
  echo "[PASS] T7 confirmation sends server-held data and renders thanks.\n";

  echo "[PASS] Isolated CakePHP 2.10.18 contact test completed.\n";
} catch (Exception $exception) {
  fwrite(STDERR, '[FAIL] ' . $exception->getMessage() . "\n");
  exit(1);
}
