<?php
App::uses('Controller', 'Controller');

class AppController extends Controller {

  public $uses                 = array('EmbedCode', 'CatalogConfiguration');
  public $components           = array('Session', 'Flash');
  public $helpers              = array('Session', 'Form', 'Html', 'Ezm');
  public $ext                  = '.html';
  public $viewmode             = '';
  public $sp_redirect_executed = false;
  public $sp_redirect_reserve  = false;
  public $now_url              = '';
  public $no_invoke            = false;

  /**
   * アクション実行前イベント
   */
  public function beforeFilter() {
    parent::beforeFilter();

    // -------- data_filesの漏洩防止用コード
    if ($this->Session->check('AdderKey')) {
      $this->adder_key = $this->Session->read('AdderKey');
    } else {
      $this->adder_key = sha1($this->Session->id());
      $this->Session->write('AdderKey', $this->adder_key);
    }
    // -------- data_filesの漏洩防止用コードここまで

    $maintenance           = Configure::read('maintenance');
    $is_maintenance_action = empty($this->params['plugin']) && $this->params['controller'] == 'homes' && $this->params['action'] == 'maintenance';
    if (!$maintenance) {
      if ($is_maintenance_action) {
        parent::redirect('/');
      }
    } else {
      if (!$is_maintenance_action) {
        parent::redirect(array('plugin' => null, 'controller' => 'homes', 'action' => 'maintenance'));
      }
    }

    //ログイン
    $Login = '';
    $Login = $this->Session->read('Login');
    $cnt   = 0;
    $this->Set('Login', $Login);

    //ログインしていない場合強制的にログイン画面へ
    if (empty($Login) && ($this->request->params['controller'] != 'user' && $this->request->params['action'] != 'login')) {
      //$this->redirect(array('controller'=>'user','action'=>'login'));
    }
    //カタログ注文ショップ、ポイント失効処理
    $shop_order_config = $this->_shop_order();
    if (!empty($shop_order_config['Switching']['point'])) {
      if (!empty($Login) && !empty($shop_order_config['Point']['expiry'])) {
        $this->_point_lost($Login, $shop_order_config['Point']['expiry']);
      }
    }

    // namedを正しく配列形式に直す
    $named = $this->request->params['named'];
    foreach ($named as $key => $value) {
      if (preg_match('/\[[^\]]*\]/', $key)) {
        $keys   = explode('[', $key);
        $branch = array();
        foreach ($keys as $one) {
          $branch[] = str_replace(']', '', $one);
        }
        $branch_array                   = create_nest_array($branch, $value);
        unset($this->request->params['named'][$key]);
        $this->request->params['named'] = array_merge_recursive($this->request->params['named'], $branch_array);
      }
    }

    // requestActionからの呼び出しの場合は、下記動作を無視する
    if (!$this->request->is('requested')) {
      // LPOプラグインがある時、ヘルパーにLpoを追加し、lpoのログactionを実行する
      if (CakePlugin::loaded('lpo')) {
        $this->helpers[] = 'Lpo.Lpo';
        $this->requestAction(array('plugin' => 'lpo', 'controller' => 'lpo_scans', 'action' => 'write_log'));
      }

      // SPリダイレクト設定をロード、実行する
      $this->_load_sp_redirect_settings();

      // デフォルトのキャッシュ設定をセット
      $this->response->disableCache();
      /*
        if ($this->sp_redirect_reserve === false) {
        $this->Session->read(); // 空読みして強引にセッション開始
        $this->response->cache('-1 minute', '+1 day');
        $this->response->expires('-1 minute');
        $this->response->sharable(true, 86400);
        $this->response->header(array('Pragma: '));
        }
       */
      // 認証設定をロード、実行する
      $this->_load_auth_settings();
    }
  }


  /**
   * アクション実行関数
   *
   * @param CakeRequest $request
   * @return CakeResponse
   */
  public function invokeAction(CakeRequest $request) {
    App::uses('CatalogBox', 'Model');
    if (isset($this->CatalogBox) && $this->CatalogBox instanceof CatalogBox) {
      $this->CatalogBox->unbindModel(array('belongsTo' => array('CatalogCategory')), false);
    }

    // アクションを実行しないフラグがセットされていた場合、アクションを実行せずレスポンスを返す
    if ($this->no_invoke !== false) {
      return ($this->no_invoke instanceof CakeResponse) ? $this->no_invoke : $this->response;
    }

    // アクションを実行する
    return parent::invokeAction($request);
  }


  /**
   * アクション実行・レンダリング後関数
   */
  public function afterFilter() {
    parent::afterFilter();

    $response_body = $this->response->body();
    if (!$this->request->is('requested') && is_string($response_body)) {
      $rootUrl = $baseUrl = EZMANAGER_FULL_BASE_URL . APP_SITE_ROOT_URI . (APP_DIR === 'app' ? '' : (APP_DIR . '/'));
      if (empty($this->ezmBaseUrl)) {
        if (!empty($this->plugin)) {
          $baseUrl .= Inflector::underscore($this->plugin) . '/';
        }
        if ($this->request['controller'] == 'homes' && $this->request['action'] == 'webroot') {
          $pass = explode('/', $this->webroot_file);
          array_pop($pass);
          $pass = implode('/', $pass);
          if (!empty($pass)) {
            $baseUrl .= $pass . '/';
          }
        }
        if (!preg_match('/\/$/', $baseUrl)) {
          $baseUrl .= '/';
        }
      } else {
        $baseUrl = $this->ezmBaseUrl;
      }

      // 埋め込みコード
      // GA4 is owned by MUSICIAN. The legacy CMS record only selects the
      // insertion position; its stored tracking code is never rendered.
      $ga4_code = '<!-- Google tag (gtag.js) -->' . "\n"
        . '<script async src="https://www.googletagmanager.com/gtag/js?id=G-74ETNWY2T9"></script>' . "\n"
        . '<script>' . "\n"
        . '  window.dataLayer = window.dataLayer || [];' . "\n"
        . '  function gtag(){dataLayer.push(arguments);}' . "\n"
        . "  gtag('js', new Date());" . "\n\n"
        . "  gtag('config', 'G-74ETNWY2T9');" . "\n"
        . '</script>';
      $ga_exists   = false;
      $embed_codes = $this->EmbedCode->find('all', array('order' => array('id' => 'asc')));
      foreach ($embed_codes as $embed_code) {
        $code = $embed_code['EmbedCode']['code'];

        // GAコードが出現した場合、最初の1個のみ有効にする
        // The legacy helper only recognizes UA-* IDs, so detect GA4 snippets too.
        $is_ga4_code = strpos($code, 'googletagmanager.com/gtag/js?id=G-') !== false;
        if (is_ga_code($code) || $is_ga4_code) {
          if ($ga_exists) {
            continue;
          }
          $ga_exists = true;
          if ($this->request['controller'] === 'catalog_preview' || $this->request['controller'] === 'CatalogPreview') {
            continue;
          }
          $code = $ga4_code;
        }
        if (empty($embed_code['EmbedCode']['position'])) {
          $response_body = preg_replace('/\<\/head\>/i', $code . "\n" . '${0}', $response_body, 1); // 2と同じ
        } else if ($embed_code['EmbedCode']['position'] == 1) {
          $response_body = preg_replace('/\<head( [^>]+)?\>/i', '${0}' . "\n" . $code, $response_body, 1);
        } else if ($embed_code['EmbedCode']['position'] == 2) {
          $response_body = preg_replace('/\<\/head\>/i', $code . "\n" . '${0}', $response_body, 1);
        } else if ($embed_code['EmbedCode']['position'] == 3) {
          $response_body = preg_replace('/\<body( [^>]+)?\>/i', '${0}' . "\n" . $code, $response_body, 1);
        } else if ($embed_code['EmbedCode']['position'] == 4) {
          $response_body = preg_replace('/\<\/body\>/i', $code . "\n" . '${0}', $response_body, 1);
        }
      }

      // SPバナー自動挿入
      if (EZM_IS_SP_ACCESS && !preg_match('/^(.+_)?sp$/', APP_DIR)) {
        if ($this->sp_redirect_reserve !== false && strpos($response_body, '/ezm_sp_banner/') === false) {
          $banner_html   = file_get_contents(ELEMENTS . DS . 'sp_banner.html');
          $response_body = str_replace('</body>', $banner_html . "\n" . '</body>', $response_body);
        }
        $this->sp_redirect_reserve = str_replace('?viewmode=pc', '', $this->sp_redirect_reserve);
        $response_body             = str_replace('/ezm_sp_banner/', Router::url('/', true) . $this->sp_redirect_reserve . '?viewmode=reset', $response_body);
      }

      // ベースURL（ドメイン＋ディレクトリ）の変更前に入力された前ベースURLを、現行のベースURLに変換する
      if (defined('FULL_BASE_URL_HISTORY')) {
        $fullBaseUrlHistory = unserialize(FULL_BASE_URL_HISTORY);
        foreach($fullBaseUrlHistory as $beforeFullBaseUrl) {
          if ($beforeFullBaseUrl !== EZMANAGER_FULL_BASE_URL.APP_SITE_ROOT_URI) {
            $response_body = str_replace($beforeFullBaseUrl, EZMANAGER_FULL_BASE_URL.APP_SITE_ROOT_URI, $response_body);
          }
        }
      }

      // 外部JS、CSS、画像の読み込みを変換する
      if (strpos(EZMANAGER_FULL_BASE_URL, 'https://') === 0) {
        $matches = array();
        if (preg_match_all('/<(img|script|link) ([^>]+)>/i', $response_body, $matches)) {
          $searches = array();
          foreach ($matches[0] as $search) {
            if (array_key_exists($search, $searches)) {
              continue;
            }
            if (!preg_match('/http:\/\//i', $search)) {
              continue;
            }
            if (preg_match('/rel="canonical"/i', $search)) {
              continue;
            }
            $searches[$search] = preg_replace('/http:\/\//i', 'https://', $search);
          }
          foreach ($searches as $search => $replace) {
            $response_body = str_replace($search, $replace, $response_body);
          }
        }
      }

      // HTML用メディアURL整形
      $response_body = preg_replace('/(((location\.| )href| src) ?\= ?("|\'))\/?media/i', '${1}' . $rootUrl . 'media', $response_body);

      // リンク・参照URL整形
      $response_body = preg_replace('/((location\.| )href| src| action) ?\= ?("|\')(?!("|\'|(https?:\/)?\/|javascript:|mailto:|tel:|<\?|#|{{))/i', '${0}' . $baseUrl, $response_body);
      $response_body = str_replace(' href="/"', ' href="' . $rootUrl . '"', $response_body);

      $this->response->body($response_body);
    }
  }


  /**
   * SP版へのリダイレクトを行う関数
   * 各アクション内で$this->sp_redirect();と実行することで使う。URL指定が可能。
   * 各アクション内で使用した時、戻り値が空以外だったら、その戻り値を指定してreturnしなければならない
   *
   * @param string $url or null
   * @return CakeResponse or false
   */
  public function sp_redirect($url = null) {
    if ($this->sp_redirect_executed) {
      return $this->no_invoke;
    }
    $this->sp_redirect_executed = true;
    if (EZM_IS_SP_ACCESS) {
      // 万が一SPフォルダにあったら機能を無効にする
      if (!preg_match('/^(.+_)?sp$/', APP_DIR)) {
        $now_url = str_replace(Router::url('/', true), '', Router::url(null, true));
        $now_url = preg_replace('/^homes\/webroot\//', '', $now_url);
        if (!empty($this->request->query)) {
          $now_url = $now_url . '?' . http_build_query($this->request->query);
        }
        if ($url === null) {
          $url = $now_url;
        }

        $root_url = Router::url('/', true);

        $sp_url = '';
        if (APP_DIR == 'app') {
          $sp_dir = 'sp';
          $sp_url = $root_url . 'sp/' . $url;
        } else {
          $sp_dir = APP_DIR . '_sp';
          $sp_url = str_replace('/' . APP_DIR . '/', '/' . APP_DIR . '_sp/', $root_url) . $url;
        }

        if (!defined('SP_DIR')) {
          define('SP_DIR', $sp_dir);
        }

        if (!empty($sp_url) && is_dir(ROOT . DS . SP_DIR)) {
          if ($this->viewmode == 'sp') {
            $this->response->disableCache();
            $this->response->header('HTTP/1.1 302 Found');
            $this->response->location($sp_url);
            $this->no_invoke = $this->response;
          }
          $this->sp_redirect_reserve = $now_url;
        }
      }
    }
    return $this->no_invoke;
  }


  /**
   * SPリダイレクトの読み込み処理部
   * 読み込み後、自動実行のものは実行する
   */
  private function _load_sp_redirect_settings() {
    // SPフォルダにあったら機能を無効にする
    if (!preg_match('/^(.+_)?sp$/', APP_DIR)) {
      $viewmode = $this->request->query('viewmode');

      if (!empty($viewmode)) {
        $viewmode = ($viewmode == 'reset') ? '' : $viewmode;
        $this->Session->write('EZM_SP_REDIRECT_VIEWMODE', $viewmode);
      } else {
        $viewmode = $this->Session->read('EZM_SP_REDIRECT_VIEWMODE');
      }

      if (empty($viewmode)) {
        $viewmode = EZM_IS_SP_ACCESS ? 'sp' : 'pc';
      }

      $this->viewmode = $viewmode;

      // SPリダイレクトの自動実行
      if (EZM_IS_SP_ACCESS) {
        $now_url    = '/' . str_replace(Router::url('/', true), '', Router::url(null, true));
        $now_url    = preg_replace('/^\/homes\/webroot/', '', $now_url);
        $now_action = '/' . $this->request['controller'] . '/' . $this->request['action'];

        $sp_redirect_settings = unserialize(SP_REDIRECT_SETTINGS);

        $sp_url = null;

        if (in_array('ezm_redirect_all', $sp_redirect_settings)) {
          $sp_url = $now_url;
        } else if (strpos($now_url, $now_action) !== 0) {
          // URLとアクションが一致しない場合、Routesでルーティングされているので、URLの一致でSP側URLを判断する
          $key = array_search($now_url, $sp_redirect_settings);
          if ($key !== false && preg_match('/^[0-9]+$/', $key)) {
            $sp_url = preg_replace('/^\//', '', $now_url);
          }

          if ($sp_url === null && array_key_exists($now_url, $sp_redirect_settings)) {
            $sp_url = preg_replace('/^\//', '', $sp_redirect_settings[$now_url]);
          }
        } else {
          // アクション文字列がURLの開始部分に含まれている場合、Routesでルーティングされていないので、passとnamedを付けてSP側URLを作成する
          $key = array_search($now_action, $sp_redirect_settings);
          if ($key !== false && preg_match('/^[0-9]+$/', $key)) {
            $sp_url = preg_replace('/^\//', '', $now_action);
            foreach ($this->request['pass'] as $pass) {
              $sp_url = $sp_url . '/' . $pass;
            }
            foreach ($this->request['named'] as $named_key => $named_value) {
              $sp_url = $sp_url . '/' . $named_key . ':' . $named_value;
            }
          }

          if ($sp_url === null && array_key_exists('/' . $this->request['controller'] . '/' . $this->request['action'], $sp_redirect_settings)) {
            $sp_url = $sp_redirect_settings[$now_action];
            if (is_array($sp_url)) {
              $sp_url  = $sp_url['url'];
              $sp_type = $sp_url['type'];
            } else {
              $sp_type = 'action';
            }
            $sp_url = preg_replace('/^\//', '', $sp_url);

            if ($sp_type == 'action') {
              foreach ($this->request['pass'] as $pass) {
                $sp_url = $sp_url . '/' . $pass;
              }
              foreach ($this->request['named'] as $named_key => $named_value) {
                $sp_url = $sp_url . '/' . $named_key . ':' . $named_value;
              }
            }
          }
        }

        if ($sp_url !== null) {
          if (!empty($this->request->query)) {
            $sp_url = $sp_url . '?' . http_build_query($this->request->query);
          }
          $this->sp_redirect($sp_url);
        }
      }
    }
  }


  /**
   * 認証設定の読み込みと実行
   */
  private function _load_auth_settings() {
    if (!file_exists(ROOT . DS . APP_DIR . DS . 'Config' . DS . 'auth.php')) {
      return;
    }

    Configure::load('auth');
    $ezm_auth = Configure::read('EzmAuth');
    if (empty($ezm_auth) || !is_array($ezm_auth)) {
      return;
    }

    foreach ($ezm_auth as $ezm_auth_name => $ezm_auth_set) {
      if (isset($ezm_auth_set['loginAction'])) {
        $here_full = Router::url($this->request->here);
        $loginAction_full = Router::url($ezm_auth_set['loginAction']);
        $isLoginPage = $here_full === $loginAction_full;
      } else {
        continue;
      }

      if (empty($ezm_auth_set['authenticate']) || (empty($ezm_auth_set['pages'][$this->request['controller']]) && !$isLoginPage)) {
        continue;
      }

      $pages = empty($ezm_auth_set['pages'][$this->request['controller']]) ? array() : $ezm_auth_set['pages'][$this->request['controller']];

      if (is_string($ezm_auth_set['authenticate']) && method_exists($this, '_load_auth_setting_' . $ezm_auth_set['authenticate'])) {
        if ($this->{'_load_auth_setting_' . $ezm_auth_set['authenticate']}($ezm_auth_name, $ezm_auth_set, $pages, $isLoginPage)) {
          break;
        }
      } else if (is_array($ezm_auth_set['authenticate']) && (in_array($this->request['action'], $pages) || in_array('*', $pages) || $isLoginPage)) {
        $this->Auth = $this->Components->load('Auth');
        AuthComponent::$sessionKey = $ezm_auth_name;
        $this->Auth->initialize($this);
        $this->Auth->allow();

        foreach ($ezm_auth_set as $key => $value) {
          if ($key !== 'pages' && $key !== 'allow') {
            $this->Auth->{$key} = $value;
          }
        }
        if (in_array('*', $pages)) {
          $this->Auth->deny();
        } else {
          $this->Auth->deny($pages);
        }
        if (!empty($ezm_auth_set['allow'][$this->request['controller']])) {
          $this->Auth->allow($ezm_auth_set['allow'][$this->request['controller']]);
        }
        break;
      }
    }
  }


  /**
   * 認証セッティング
   * カタログをユーザーモデルとして扱う認証
   */
  private function _load_auth_setting_catalog($ezm_auth_name, $ezm_auth_set, $pages, $isLoginPage) {
    if (empty($ezm_auth_set['loginRedirect'])) {
      return false;
    }

    $this->Auth = $this->Components->load('Auth');
    AuthComponent::$sessionKey = $ezm_auth_name;
    $this->Auth->initialize($this);
    $this->Auth->allow();

    $this->loadModel('CatalogBox');

    // 複数のカテゴリーにまたがる為、情報をいっぺんに取得するようmodelをbind（SQLで言うところのJOIN）する
    $assoc = array(
      'belongsTo' => array(
        'CatalogCategory' => array(
          'className'  => 'CatalogCategory',
          'foreignKey' => 'category_id',
        )
      )
    );
    $this->CatalogBox->bindModel($assoc, false);

    foreach ($ezm_auth_set as $key => $value) {
      if ($key !== 'authenticate' && $key !== 'pages' && $key !== 'allow' && $key !== 'configuration_id' && $key !== 'template') {
        $this->Auth->{$key} = $value;
      }
    }
    if (in_array('*', $pages)) {
      $this->Auth->deny();
    } else {
      $this->Auth->deny($pages);
    }
    if (!empty($ezm_auth_set['allow'][$this->request['controller']])) {
      $this->Auth->allow($ezm_auth_set['allow'][$this->request['controller']]);
    }

    $scope        = array('CatalogBox.configuration_id' => $ezm_auth_set['configuration_id']);
    if (!empty($ezm_auth_set['template'])) {
      $scope['CatalogCategory.template'] = $ezm_auth_set['template'];
    }

    $this->Auth->authenticate = array(
      'Form' => array(
        'userModel' => 'CatalogBox',
        'fields'    => array(
          'username' => 'auth_id',
          'password' => 'auth_password'
        ),
        'scope'     => $scope
      )
    );

    return true;
  }




  /**
   * 認証セッティング
   * ID・パスワードを収めた配列と比較する認証
   */
  private function _load_auth_setting_simple($ezm_auth_name, $ezm_auth_set, $pages, $isLoginPage) {
    if (empty($ezm_auth_set['users']) || empty($ezm_auth_set['loginRedirect'])) {
      return false;
    }

    $this->Auth = $this->Components->load('Auth');
    AuthComponent::$sessionKey = $ezm_auth_name;
    $this->Auth->initialize($this);
    $this->Auth->allow();

    foreach ($ezm_auth_set as $key => $value) {
      if ($key !== 'authenticate' && $key !== 'pages' && $key !== 'allow' && $key !== 'users') {
        $this->Auth->{$key} = $value;
      }
    }
    if (in_array('*', $pages)) {
      $this->Auth->deny();
    } else {
      $this->Auth->deny($pages);
    }
    if (!empty($ezm_auth_set['allow'][$this->request['controller']])) {
      $this->Auth->allow($ezm_auth_set['allow'][$this->request['controller']]);
    }

    App::uses('ArrayFormAuthenticate', 'Controller/Component/Auth');

    $this->Auth->authenticate = array(
      'ArrayForm' => array(
        'auth_name' => $ezm_auth_name,
        'users' => $ezm_auth_set['users']
      )
    );

    return true;
  }


  /**
   * 認証セッティング
   * アイテム、カテゴリ、祖先カテゴリ、アプリケーション設定のうち、より末端に近いIDとパスワードを採用する
   */
  private function _load_auth_setting_catalog_self($ezm_auth_name, $ezm_auth_set, $pages, $isLoginPage) {
    $auth_actions = empty($ezm_auth_set['pages'][$this->request['controller']]) ? array() : $ezm_auth_set['pages'][$this->request['controller']];
    if (!is_array($auth_actions)) {
      $auth_actions = array();
    }

    // 認証の対象アクションだったら処理を開始する
    if (!array_key_exists($this->request['action'], $auth_actions) && !$isLoginPage) {
      return false;
    }



    // -------------------------------------------- ID・パスワードの収集 --------------------------------------------

    $this->loadModel('CatalogBox');
    $this->loadModel('CatalogCategory');
    $this->loadModel('CatalogConfiguration');


    list($config, $setting) = $this->CatalogConfiguration->getConfigAndSetting($ezm_auth_set['configuration_id']);
    $csort = isset($setting['csort']) && strtolower($setting['csort']) === 'desc' ? 'desc' : 'asc';

    $root_category                  = array('id' => 0, 'parent_id' => 0, 'has_children' => '1', 'template' => $setting['template']);
    $root_category['auth_file']     = empty($setting['auth_file']) ? '' : $setting['auth_file'];
    $root_category['auth_id']       = empty($setting['auth_id']) ? '' : $setting['auth_id'];
    $root_category['auth_password'] = empty($setting['auth_password']) ? '' : $setting['auth_password'];

    $categories = array(array('CatalogCategory' => $root_category));

    $category_id = 0;

    $query = $this->request->query;

    if ($isLoginPage) {
      if (!isset($query['type']) || !isset($query['controller']) || !isset($query['action']) || !isset($query['pass_id'])) {
        $this->redirect('/');
      }

      $type = $query['type'];
      $target_controller = $query['controller'];
      $target_action = $query['action'];
      $pass_id = $query['pass_id'];
    } else {
      $type = $auth_actions[$this->request['action']];
      $target_controller = $this->request['controller'];
      $target_action = $this->request['action'];
      $pass_id = empty($this->request['pass'][0]) ? 0 : $this->request['pass'][0];
    }

    $query['type'] = $type;
    $query['controller'] = $target_controller;
    $query['action'] = $target_action;
    $query['pass_id'] = $pass_id;


    if ($type === 'detail' && !empty($pass_id)) {
      $box_id = $pass_id;
      $box    = $this->CatalogBox->find('first', array('conditions' => array('CatalogBox.configuration_id' => $ezm_auth_set['configuration_id'], 'CatalogBox.id' => $box_id)));
      if (!empty($box['CatalogBox']['category_id'])) {
        $category_id            = $box['CatalogBox']['category_id'];
        $box['CatalogCategory'] = $box['CatalogBox'];
        unset($box['CatalogBox']);
      }
    } else if ($type === 'index') {
      $category_id = empty($pass_id) ? 0 : $pass_id;
      if (empty($category_id) && $this->skip_root_index) {
        $first = $this->CatalogCategory->find('first', array('conditions' => array('configuration_id' => $ezm_auth_set['configuration_id'], 'parent_id' => 0), 'order' => 'lft ' . $csort));
        if (!empty($first)) {
          $category_id = $first['CatalogCategory']['id'];
        }
      }
    }

    if ($category_id != 0) {
      $this->CatalogCategory->attachTreeBehavior($ezm_auth_set['configuration_id']);
      $categories = am($categories, $this->CatalogCategory->getPath($category_id));
      if (!empty($box['CatalogCategory'])) {
        $categories[] = $box;
      }
    }
    krsort($categories);

    $auth_users      = array();
    $auth_categories = array();
    $auth_files      = array();

    foreach ($categories as $category) {
      $category = $category['CatalogCategory'];
      if (!empty($category['auth_id']) && !empty($category['auth_password'])) {
        $auth_users[]      = array('username' => $category['auth_id'], 'pass' => $category['auth_password']);
        $auth_categories[] = (isset($category['category_id']) ? 'box' : 'category') . $category['id'];
      }

      $auth_file = empty($category['auth_file']) ? '' : $category['auth_file'];

      if (!empty($auth_file) && file_exists(ROOT . DS . 'app' . DS . 'Config' . DS . $auth_file) && !in_array($auth_file, $auth_files)) {
        $file_contents = file_get_contents(ROOT . DS . 'app' . DS . 'Config' . DS . $auth_file);
        if (!empty($file_contents)) {
          $file_user_info_array = explode("\n", $file_contents);
          foreach ($file_user_info_array as $file_user_info) {
            $user_info = explode(' ', $file_user_info);
            if (!empty($user_info[0]) && !empty($user_info[1])) {
              $auth_users[] = array('username' => $user_info[0], 'pass' => $user_info[1]);
            }
          }
        }
        $auth_files[] = $auth_file;
      }
    }

    krsort($auth_categories);

    // ---------------------------------------- ID・パスワードの収集ここまで ----------------------------------------


    if (empty($auth_users)) {
      return false;
    }

    // ID・パスワードが見つかった場合、対象ページである。Authコンポーネントのセットアップ開始
    // Authコンポーネントの初期化
    $this->Auth = $this->Components->load('Auth');
    AuthComponent::$sessionKey = $ezm_auth_name;
    $this->Auth->initialize($this);

    // ログインアクションの決定
    $this->Auth->loginAction = $ezm_auth_set['loginAction'] . '?' . http_build_query($query);

    // オプション項目のセット
    foreach ($ezm_auth_set as $key => $value) {
      if ($key !== 'authenticate' && $key !== 'pages' && $key !== 'allow' && $key !== 'configuration_id' && $key !== 'loginAction') {
        $this->Auth->{$key} = $value;
      }
    }

    // 許可・不許可の決定
    $this->Auth->allow();
    $this->Auth->deny(array_keys($auth_actions));
    if (!empty($ezm_auth_set['allow'][$this->request['controller']])) {
      $this->Auth->allow($ezm_auth_set['allow'][$this->request['controller']]);
    }

    // 認証オブジェクトのセット
    App::uses('CatalogFormAuthenticate', 'Controller/Component/Auth');

    $this->Auth->authenticate = array(
      'CatalogForm' => array(
        'configuration_id' => $ezm_auth_set['configuration_id'],
        'catalog_users' => $auth_users
      )
    );

    // 対象ページで未ログインだった場合、強制ログアウト
    if (!$isLoginPage) {
      $username = $this->Session->read($ezm_auth_name . '.0.username');
      $password = $this->Session->read($ezm_auth_name . '.0.pass');

      $return = false;
      if (!is_string($username) || $username === '' || !is_string($password) || $password === '') {
      } else {
        $return = Hash::extract($auth_users, '{n}[username=' . $username . '][pass=' . $password . ']');
      }

      if (empty($return)) {
        $this->Session->delete($ezm_auth_name);
      }
    }

    return true;
  }


  public function _setFlash($message, $type = NULL) {
    $default = array('element' => 'normal');
    if (!empty($type) && is_array($type)) {
      $this->Flash->set($message, am($default, $type));
    } elseif (!empty($type) && is_string($type)) {
      $this->Flash->set($message, array('element' => $type));
    } else {
      $this->Flash->set($message, $default);
    }
  }


  public function _shop_order() {
    App::uses('CatalogConfiguration', 'Model');
    $CatalogConfiguration = $this->CatalogConfiguration->find('first', array('conditions' => array('OR' => array('0' => array('application like' => '%so0%'), '1' => array('application like' => '%co0%')))));
    $shop_order_config    = array();
    if (!empty($CatalogConfiguration)) {
      $File              = new File(APP_FILES_PATH . DS . $CatalogConfiguration['CatalogConfiguration']['application'] . '_' . $CatalogConfiguration['CatalogConfiguration']['id'] . DS . 'configure.dat');
      $shop_order_config = unserialize($File->read());
      $File->close();
    }
    return $shop_order_config;
  }


  public function _point_lost($Login, $expiry) {
    $Point = ClassRegistry::init('Point');
    $Point->create();
    $point = $Point->find('first', array('conditions' => array('user_id' => $Login['id']), 'order' => array('id' => 'desc')));
    if (!empty($expiry)) {
      $now_date = date('Y-m-d');
      if (!empty($point['Point']['expiry_date'])) {
        //失効日が設定されている場合は現在の日付と比べて失効処理を行う。
        $expiry_date = date('Y-m-d', strtotime($point['Point']['expiry_date']));
        if ($point['Point']['expiry_date'] < $now_date) {
          $save                            = array();
          $save['Point']['user_id']        = $point['Point']['user_id'];
          $save['Point']['deleted']        = 0;
          $save['Point']['point_title']    = 'ポイント失効';
          $save['Point']['point_before']   = $point['Point']['point_after'];
          $save['Point']['point_gain']     = $point['Point']['point_after'];
          $save['Point']['point_after']    = 0;
          $save['Point']['system_message'] = '失効';
          $save['Point']['created']        = $save['Point']['modified']       = $now_date;
          $save['Point']['comment']        = 'ポイント失効日' . date('Y年m月d日', strtotime($expiry_date)) . 'を経過したためポイントが失効しました。';
          $save['Point']['expiry_date']    = null;
          $Point->save($save);
        }
      }
    }
    return;
  }


  /**
   * CakeEmailのインスタンスを作成
   *
   * @param string $smtp_name 設定名
   * @return object CakeEmailインスタンス
   * @access private
   */
  private function __getCakeEmail($smtp_name) {
    static $email = array();

    if (empty($email[$smtp_name])) {
      $smtp_config = $this->Smtp->find('first', array('conditions' => array('Smtp.name' => $smtp_name, 'Smtp.enable' => 1)));
      if (empty($smtp_config)) {
        $smtp_config = $this->Smtp->find('first', array('conditions' => array('Smtp.enable' => 1)));
      }

      if (empty($smtp_config)) {
        $smtp = 'default';
      } else {
        if (empty($smtp_config['Smtp']['title'])) {
          $sender = $smtp_config['Smtp']['full_mail_address'];
        } else {
          $sender = array($smtp_config['Smtp']['full_mail_address'] => $smtp_config['Smtp']['title']);
        }
        $smtp = array(
          'transport'     => 'Smtp',
          'sender'        => $sender,
          'host'          => $smtp_config['Smtp']['host'],
          'port'          => intval($smtp_config['Smtp']['port']),
          'timeout'       => 30,
          'username'      => $smtp_config['Smtp']['username'],
          'password'      => $smtp_config['Smtp']['password'],
          'client'        => null,
          'log'           => 'emails',
          'charset'       => 'utf-8',
          'headerCharset' => 'utf-8',
        );
      }
      App::uses('CakeEmail', 'Network/Email');
      $email[$smtp_name] = new CakeEmail($smtp);
    }
    return $email[$smtp_name];
  }


  /**
   * CakePHPのmail機能を利用してメールを送信します。
   *
   * @param bool $to_system システム宛ならtrue
   * @param mixed $smtp_name 転送先設定識別名
   * @param mixed $to 宛先
   * @param string $subject 件名
   * @param string $text 内容
   * @param mixed $from Fromヘッダー
   * @param array $attachment 添付ファイル
   * @access private
   */
  protected function __sendCakeEmail($to_system, $smtp_name, $to, $subject, $text, $from, $attachment = null, $sender = null) {
    static $mxr = array();
    $result = '送信済み';

    set_error_handler(function ($errno, $errstr, $errfile, $errline) {
      if (strpos($errno . $errstr . $errfile . $errline, 'chmod') === false) {
        // エラーが発生した場合、ErrorExceptionを発生させる
        throw new ErrorException(
          $errstr,
          0,
          $errno,
          $errfile,
          $errline
        );
      }
    });

    try {
      $Email = $this->__getCakeEmail($smtp_name);
      $mxr_diff = false;

      if (is_array($from)) {
        if ($sender) {
          $Email->sender($sender)->from($from[0], $from[1]);
        } else {
          $Email->sender($from[0], $from[1])->from($from[0], $from[1]);
        }
      } else {
        if ($sender) {
          $Email->sender($sender)->from($from);
        } else {
          $Email->sender($from)->from($from);
        }
      }

      if (!defined('EZMANAGER_CHECK_MAILTO_HOST') || EZMANAGER_CHECK_MAILTO_HOST == true) {
        $to_divide = explode('@', $to);
        if (count($to_divide) !== 2) {
          throw new Exception('Invalid email set for "_to". You passed "' . $to . '".');
        }

        if (!array_key_exists($to_divide[1], $mxr)) {
          $mxr[$to_divide[1]] = dns_get_record($to_divide[1], DNS_MX);
          if (empty($mxr[$to_divide[1]])) {
            throw new Exception('getmxrr failed: "' . $to . '" not known');
          }

          $dns = array();
          foreach ($mxr[$to_divide[1]] as $dnsr) {
            $dns[] = $dnsr['pri'] . ' ' . $dnsr['target'];
          }
          sort($dns);
          $mxr[$to_divide[1]] = $dns;
        }

        if (empty($mxr[$to_divide[1]])) {
          throw new Exception('getmxrr failed: "' . $to . '" not known');
        }

        if ($to_system) {
          $mxr_file = array();
          if (file_exists(ROOT . DS . 'app' . DS . 'tmp' . DS . 'mxr.txt')) {
            $mxr_file = @file_get_contents(ROOT . DS . 'app' . DS . 'tmp' . DS . 'mxr.txt');
            $mxr_file = @unserialize($mxr_file);
          }
          if (empty($mxr_file)) {
            $mxr_file = array();
          }
          if (!empty($mxr_file[$to_divide[1]])) {
            $mxr_diff = ($mxr_file[$to_divide[1]] != $mxr[$to_divide[1]]);
          }
          $mxr_file[$to_divide[1]] = $mxr[$to_divide[1]];
          @file_put_contents(ROOT . DS . 'app' . DS . 'tmp' . DS . 'mxr.txt', serialize($mxr_file));
          @chmod(ROOT . DS . 'app' . DS . 'tmp' . DS . 'mxr.txt', 0777);
        }
      }

      $Email->to($to);
      $Email->subject($subject);

      if ($attachment) {                //$attachment
        $Email->attachments($attachment);
      }

      $Email->send($text);

      if ($mxr_diff) {
        throw new Exception('getmxrr alert');
      }

      // throw new Exception('メールフォームにてエラーが発生しました。');
    } catch (Exception $e) {
      $param = array();
      $result = $param['error']  = $e->getMessage();
      if ($result == 'getmxrr alert') {
        $result = '送信施行(' . $result . ')';
      } else {
        $result = '送信失敗(' . $result . ')';
      }

      if (preg_match('/getmxrr failed/', $param['error'], $matches) && !$to_system) { // メアドのホストが見つからず、エンドユーザー宛ての場合、APIへ送らない
        $result = '送信失敗(メール送信先のサーバーが見つかりませんでした)';
      } elseif (Configure::read('debug') == 0) {
        $param['domain'] = FULL_BASE_URL;
        $param['mailaddress'] = $to;

        //リクエスト時のオプション指定
        $options = array(
          'http' => array(
            'method'           => 'POST',
            'header'           => array(
              'Content-type: application/x-www-form-urlencoded',
              'User-Agent: Mozilla/5.0 (Windows NT 5.1; rv:13.0) Gecko/20100101 Firefox/13.0.1'
            ),
            'content'          => http_build_query($param),
            'ignore_errors'    => true,
            'protocol_version' => '1.1',
            'timeout'          => 1
          ),
          'ssl'  => array(
            'verify_peer'      => false,
            'verify_peer_name' => false
          )
        );

        //リクエスト実行
        $contents = file_get_contents("http://api.ezm2.com/contact/recieve_error", false, stream_context_create($options));

        //      //ステータスコード
        //      preg_match('/HTTP\/1\.[0|1|x] ([0-9]{3})/', $http_response_header[0], $matches);
        //      $statusCode = (int) $matches[1];
        //
        //      //配列で返すためにjsonのエンコード
        //      $contents_array = array();
        //      if ($statusCode === 200) {
        //        $contents_array = json_decode($contents);
        //      }
      }
    }

    set_error_handler(function ($errno, $errstr, $errfile, $errline) {
      return;
    });

    if (is_array($to)) {
      $to = implode(',', $to);
    }

    return $to . ' ' . $result;
  }
}
