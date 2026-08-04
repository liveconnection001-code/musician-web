<?php

class ContactController extends AppController {

  public $name    = 'Contact';
  public $helpers = array('Ezm');
  public $uses    = array('ContactMailSend', 'Smtp');
  public $cid     = 1;

  private $sessionKey = 'Contact.PendingForm';

  public function beforeFilter() {
    if (!$this->request->is('post')) {
      ezmError('error404');
    }

    $this->ContactMailSend->setMailConfigurationId($this->cid);
    $this->set('mail_configuration_id', $this->cid);
    parent::beforeFilter();
  }

  /**
   * 入力→確認→送信を処理する。
   * 最終送信では、確認画面のhidden値ではなくセッションの検証済み値だけを使う。
   */
  public function postmail() {
    $submitted = $this->requestData();

    if (!empty($submitted['send'])) {
      return $this->sendConfirmedForm($submitted);
    }

    $form = $this->normaliseForm($submitted);
    if ($form['website'] !== '') {
      $this->Session->delete($this->sessionKey);
      return $this->render('thanks');
    }

    $this->ContactMailSend->set(array('ContactMailSend' => $form));
    $this->ContactMailSend->validate();
    if (!empty($this->ContactMailSend->error)) {
      $this->ContactMailSend->saveMailError();
      return $this->renderContactForm($form, $this->errorsByField($this->ContactMailSend->error));
    }

    $token = sha1(uniqid(mt_rand(), true));
    $this->Session->write($this->sessionKey, array('form' => $form, 'token' => $token));
    $this->set('confirm_data', $this->ContactMailSend->getConfirmData());
    $this->set('contact_token', $token);
    return $this->render('msg');
  }

  private function sendConfirmedForm($submitted) {
    $pending = $this->Session->read($this->sessionKey);
    $token = isset($submitted['contact_token']) ? (string)$submitted['contact_token'] : '';

    if (empty($pending['form']) || empty($pending['token']) || strlen($token) !== strlen($pending['token']) || $token !== $pending['token']) {
      $this->set('confirm_error', '確認情報の有効期限が切れました。お手数ですが、もう一度入力してください。');
      return $this->render('msg');
    }

    $form = $pending['form'];
    $this->ContactMailSend->set(array('ContactMailSend' => $form));
    $this->ContactMailSend->spamCheck();
    $this->sendData($form);
    $this->Session->delete($this->sessionKey);
    return $this->render('thanks');
  }

  private function requestData() {
    $data = is_array($this->request->data) ? $this->request->data : array();
    if (!empty($data['ContactMailSend']) && is_array($data['ContactMailSend'])) {
      return $data['ContactMailSend'];
    }
    if (!empty($data['MailSend']) && is_array($data['MailSend'])) {
      return $data['MailSend'];
    }
    return $data;
  }

  private function normaliseForm($data) {
    $fields = array('inquiry_type', 'company', 'name', 'furigana', 'email', 'tel', 'event_date', 'event_pref', 'venue', 'attendee_count', 'budget', 'genre', 'photo_numbers', 'message', 'website');
    $form = array();
    foreach ($fields as $field) {
      $value = isset($data[$field]) && !is_array($data[$field]) ? (string)$data[$field] : '';
      $form[$field] = trim(str_replace("\0", '', $value));
    }
    $form['event_date_tbd'] = !empty($data['event_date_tbd']) ? '日程は未定・調整中' : '';
    if ($form['event_date_tbd'] !== '') {
      $form['event_date'] = '';
    }
    $form['agree'] = !empty($data['agree']) ? '個人情報保護方針に同意する' : '';
    return $form;
  }

  private function errorsByField($errors) {
    $result = array();
    foreach ($this->ContactMailSend->fields[$this->cid] as $field => $setting) {
      if (!empty($errors[$setting['name']])) {
        $result[$field] = $errors[$setting['name']];
      }
    }
    return $result;
  }

  private function renderContactForm($form, $errors) {
    $this->set('contact_data', $form);
    $this->set('contact_errors', $errors);
    $this->set('file', WWW_ROOT . 'contact.html');
    return $this->render('/Homes/webroot');
  }

  /**
   * 既存のMailConfiguration・SMTP設定を使って、管理者通知と自動返信を送る。
   */
  public function sendData($form) {
    Configure::write('debug', 0);
    $MailConfiguration = ClassRegistry::init('MailConfiguration');
    $configuration = $MailConfiguration->find('first', array('conditions' => array('id' => $this->cid)));
    if (empty($configuration['MailConfiguration'])) {
      return;
    }

    $settings = $configuration['MailConfiguration'];
    $smtp = empty($settings['smtp']) ? 'default' : $settings['smtp'];
    $from = $this->parseFromAddress($settings['from_address']);
    $adminSubject = '【Webお問い合わせ】' . $form['inquiry_type'] . ' / ' . $form['name'] . '様';
    $adminText = $this->buildAdminText($form);
    $autoText = $this->buildAutoReplyText($form);
    $autoStatus = $this->sendContactEmail($smtp, $form['email'], '【MUSICIAN】お問い合わせを受け付けました', $autoText, $from);

    $adminStatuses = array();
    $recipients = preg_split('/[\r\n,]+/', $settings['to_address']);
    foreach ($recipients as $recipient) {
      $recipient = trim($recipient);
      if ($recipient !== '') {
        $adminStatuses[] = $this->sendContactEmail($smtp, $recipient, $adminSubject, $adminText, $from, $form['email']);
      }
    }

    $MailList = ClassRegistry::init('MailList');
    $MailList->create();
    $MailList->set(array(
        'mail_configuration_id' => $this->cid,
        'mailaddress' => $autoStatus,
        'from' => is_array($from) ? $from[0] . '<' . $from[1] . '>' : $from,
        'bcc' => implode(",\n", $adminStatuses),
        'ip' => getenv('REMOTE_ADDR'),
        'subject' => $adminSubject,
        'mail_contents' => $adminText,
        'word_contents' => $this->labelledFormData($form),
    ));
    $MailList->save();
  }

  private function parseFromAddress($fromAddress) {
    if (strpos($fromAddress, '<') === false) {
      return $fromAddress;
    }
    $parts = explode('<', $fromAddress, 2);
    return array(trim($parts[0]), trim(str_replace('>', '', $parts[1])));
  }

  private function labelledFormData($form) {
    $labels = array(
        'inquiry_type' => 'お問い合わせ種別', 'company' => '貴社名・団体名', 'name' => 'お名前', 'furigana' => 'フリガナ',
        'email' => 'メールアドレス', 'tel' => '電話番号', 'event_date' => '開催予定日', 'event_date_tbd' => '日程は未定・調整中',
        'event_pref' => '開催エリア', 'venue' => '会場名・会場の種類', 'attendee_count' => '想定人数', 'budget' => 'ご予算の目安',
        'genre' => 'ご希望のジャンル・編成', 'photo_numbers' => 'ご覧になった写真番号',
        'message' => 'お問い合わせ内容', 'agree' => '個人情報保護方針への同意',
    );
    $result = array();
    foreach ($labels as $field => $label) {
      $result[$label] = $form[$field] === '' ? '—' : $form[$field];
    }
    return $result;
  }

  private function buildAdminText($form) {
    $text = "MUSICIANサイトからお問い合わせがありました。\n\n";
    foreach ($this->labelledFormData($form) as $label => $value) {
      $text .= '【' . $label . "】\n" . $value . "\n\n";
    }
    return $text;
  }

  private function buildAutoReplyText($form) {
    $text = $form['name'] . " 様\n\n";
    $text .= "この度はMUSICIANへお問い合わせいただき、ありがとうございます。以下の内容で受け付けました。通常1営業日以内に、担当者よりご返信いたします。お急ぎの場合は、お電話（03-6261-4348）にてご連絡ください。\n\n";
    foreach ($this->labelledFormData($form) as $label => $value) {
      $text .= '【' . $label . "】\n" . $value . "\n\n";
    }
    return $text;
  }

  private function sendContactEmail($smtpName, $to, $subject, $text, $from, $replyTo = null) {
    try {
      $smtpConfig = $this->Smtp->find('first', array('conditions' => array('Smtp.name' => $smtpName, 'Smtp.enable' => 1)));
      if (empty($smtpConfig)) {
        $smtpConfig = $this->Smtp->find('first', array('conditions' => array('Smtp.enable' => 1)));
      }

      $transport = 'default';
      if (!empty($smtpConfig['Smtp'])) {
        $settings = $smtpConfig['Smtp'];
        $sender = empty($settings['title']) ? $settings['full_mail_address'] : array($settings['full_mail_address'] => $settings['title']);
        $transport = array(
            'transport' => 'Smtp', 'sender' => $sender, 'host' => $settings['host'], 'port' => intval($settings['port']),
            'timeout' => 30, 'username' => $settings['username'], 'password' => $settings['password'], 'client' => null,
            'log' => 'emails', 'charset' => 'utf-8', 'headerCharset' => 'utf-8',
        );
      }

      App::uses('CakeEmail', 'Network/Email');
      $Email = new CakeEmail($transport);
      if (is_array($from)) {
        $Email->sender($from[0], $from[1])->from($from[0], $from[1]);
      } else {
        $Email->sender($from)->from($from);
      }
      if (!empty($replyTo)) {
        $Email->replyTo($replyTo);
      }
      $Email->to($to)->subject($subject)->send($text);
      return '送信済み';
    } catch (Exception $exception) {
      return '送信失敗(' . $exception->getMessage() . ')';
    }
  }
}
