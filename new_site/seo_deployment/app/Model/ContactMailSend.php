<?php
App::uses('MailSend', 'Model');

/**
 * MUSICIANお問い合わせ専用の項目定義と入力検証です。
 *
 * 既存の汎用MailSendを変更せず、cid=1の既存メール設定・IP/拒否語対策を
 * このフォームだけで継続利用します。
 */
class ContactMailSend extends MailSend {

  public $name = 'ContactMailSend';

  public $email_field = array(
      '1' => 'email',
  );

  public $word_spam_field = array(
      '1' => array('message'),
  );

  public $fields = array(
      '1' => array(
          'inquiry_type'   => array('name' => 'お問い合わせ種別', 'validation' => 'required,inquiryType'),
          'company'        => array('name' => '貴社名・団体名', 'validation' => ''),
          'name'           => array('name' => 'お名前', 'validation' => 'required'),
          'furigana'       => array('name' => 'フリガナ', 'validation' => ''),
          'email'          => array('name' => 'メールアドレス', 'validation' => 'required,email'),
          'tel'            => array('name' => '電話番号', 'validation' => 'telephone'),
          'event_date'     => array('name' => '開催予定日', 'validation' => 'eventDate'),
          'event_date_tbd' => array('name' => '日程は未定・調整中', 'validation' => ''),
          'event_pref'     => array('name' => '開催エリア', 'validation' => 'eventPref'),
          'venue'          => array('name' => '会場名・会場の種類', 'validation' => ''),
          'attendee_count' => array('name' => '想定人数', 'validation' => ''),
          'budget'         => array('name' => 'ご予算の目安', 'validation' => 'budget'),
          'genre'          => array('name' => 'ご希望のジャンル・編成', 'validation' => ''),
          'photo_numbers'  => array('name' => 'ご覧になった写真番号', 'validation' => ''),
          'message'        => array('name' => 'お問い合わせ内容', 'validation' => 'required,messageLength'),
          'agree'          => array('name' => '個人情報保護方針への同意', 'validation' => 'agree'),
          'website'        => array('name' => 'website', 'validation' => '', 'check' => 'not_output'),
      ),
  );

  private $inquiryTypes = array(
      '出張演奏のご依頼・お見積り',
      'イベント・式典の音楽演出/制作のご相談',
      'コンサート制作のご相談',
      '編曲・楽譜制作/オリジナル楽曲のご相談',
      '音響・照明・収録・配信のご相談',
      'その他（取材・協業など）',
  );

  private $eventPrefs = array(
      '未定', '北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県',
      '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県',
      '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県', '静岡県', '愛知県',
      '三重県', '滋賀県', '京都府', '大阪府', '兵庫県', '奈良県', '和歌山県',
      '鳥取県', '島根県', '岡山県', '広島県', '山口県',
      '徳島県', '香川県', '愛媛県', '高知県',
      '福岡県', '佐賀県', '長崎県', '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県', '海外',
  );

  private $budgets = array(
      '未定・ご相談しながら決めたい', '〜30万円', '30万〜50万円', '50万〜100万円',
      '100万〜300万円', '300万円以上',
  );

  public function inquiryType($data, $value) {
    if (!in_array($data, $this->inquiryTypes, true)) {
      $this->error[$value['name']] = 'お問い合わせ種別を選択してください。';
      return false;
    }
    return true;
  }

  public function telephone($data, $value) {
    if ($data !== '' && !preg_match('/^[0-9+\-]+$/', $data)) {
      $this->error[$value['name']] = '電話番号は半角数字・ハイフン・+のみで入力してください。';
      return false;
    }
    return true;
  }

  public function eventDate($data, $value) {
    if ($data === '') {
      return true;
    }
    if (!preg_match('/^(\d{4})-(\d{2})-(\d{2})$/', $data, $matches) || !checkdate((int)$matches[2], (int)$matches[3], (int)$matches[1])) {
      $this->error[$value['name']] = '開催予定日は正しい日付で入力してください。';
      return false;
    }
    return true;
  }

  public function eventPref($data, $value) {
    if ($data !== '' && !in_array($data, $this->eventPrefs, true)) {
      $this->error[$value['name']] = '開催エリアを選択してください。';
      return false;
    }
    return true;
  }

  public function budget($data, $value) {
    if ($data !== '' && !in_array($data, $this->budgets, true)) {
      $this->error[$value['name']] = 'ご予算の目安を選択してください。';
      return false;
    }
    return true;
  }

  public function messageLength($data, $value) {
    if (mb_strlen($data, 'UTF-8') < 10) {
      $this->error[$value['name']] = 'お問い合わせ内容は10文字以上で入力してください。';
      return false;
    }
    return true;
  }

  /**
   * 親モデルのIP・拒否語・送信回数制限を維持する。
   * 親実装は表示ラベルを検索するため、拒否語検索時だけラベルキーも補う。
   */
  public function spamCheck() {
    $original = $this->data[$this->alias];
    $forSpam = $original;
    foreach ($this->word_spam_field[$this->__cid] as $field) {
      $label = $this->fields[$this->__cid][$field]['name'];
      $forSpam[$label] = isset($original[$field]) ? $original[$field] : '';
    }
    $this->data[$this->alias] = $forSpam;
    parent::spamCheck();
    $this->data[$this->alias] = $original;
  }
}
