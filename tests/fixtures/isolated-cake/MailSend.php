<?php

App::uses('AppModel', 'Model');

/**
 * Minimal, isolated parent contract used only to exercise ContactMailSend.
 * Production MailSend is not copied to CI because it and its database settings
 * are intentionally excluded from Git.
 */
class MailSend extends AppModel {
  public $useTable = false;
  public $fields = array();
  public $error = array();
  public $__cid;

  public function setMailConfigurationId($id, $lang = null) {
    $this->__cid = $id;
  }

  public function validate() {
    $data = $this->data[$this->alias];
    $this->error = array();
    foreach ($this->fields[$this->__cid] as $field => $setting) {
      if (!array_key_exists($field, $data)) {
        $this->error[$setting['name']] = $setting['name'] . 'が見つかりません。';
        continue;
      }
      if (empty($setting['validation'])) {
        continue;
      }
      foreach (explode(',', $setting['validation']) as $method) {
        if ($this->{$method}($data[$field], $setting) !== true) {
          break;
        }
      }
    }
  }

  public function required($data, $setting) {
    if ($data === '') {
      $this->error[$setting['name']] = $setting['name'] . 'が未入力です。';
      return false;
    }
    return true;
  }

  public function email($data, $setting) {
    if (filter_var($data, FILTER_VALIDATE_EMAIL) === false) {
      $this->error[$setting['name']] = $setting['name'] . 'の書式が不正です。';
      return false;
    }
    return true;
  }

  public function agree($data, $setting) {
    if ($data === '') {
      $this->error[$setting['name']] = $setting['name'] . 'についてご確認ください。';
      return false;
    }
    return true;
  }

  public function getConfirmData() {
    $result = array();
    foreach ($this->fields[$this->__cid] as $field => $setting) {
      if (empty($setting['check']) || $setting['check'] !== 'not_output') {
        $result[$setting['name']] = $this->data[$this->alias][$field];
      }
    }
    return $result;
  }

  public function spamCheck() {
  }
}
