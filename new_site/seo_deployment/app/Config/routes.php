<?php
/**
 * ROOT
 *
 */

// webroot下にあるhtmlファイルをルーティングする
webroot_routing();
Router::redirect('/company/index/21', '/achievements.html', array('status' => 301));
Router::connect('/', array('controller' => 'homes', 'action' => 'index'));
Router::connect('/index.html', array('controller' => 'homes', 'action' => 'index'));
Router::connect('/works.html', array('controller' => 'works', 'action' => 'index'));
Router::connect('/company.html', array('controller' => 'company', 'action' => 'index'));
Router::connect('/achievements.html', array('controller' => 'company', 'action' => 'index', 21));
Router::connect('/artist.html', array('controller' => 'artist', 'action' => 'index'));

//Router::connect('/shop',   array('plugin' => 'shop','controller' => 'homes',   'action' => 'index'));      //ezshop追加時
//Router::connect('/blog',   array('plugin' => 'Blog','controller' => 'blog_diaries',   'action' => 'index'));  //ブログ追加時
//@include_once(ROOT.'/App/Config/dynamic_routes.php');


// robots.txt自動化処理用
Router::connect('/robots.txt', array('controller' => 'homes', 'action' => 'robots'));

// 既知の静的ページ以外の .html URL はホームを返さず、正しい404応答にする
Router::connect('/homes/login', array('controller' => 'homes', 'action' => 'not_found'));
Router::connect('/homes/maintenance', array('controller' => 'homes', 'action' => 'not_found'));
Router::connect('/:slug.html', array('controller' => 'homes', 'action' => 'not_found'), array('slug' => '[A-Za-z0-9_-]+'));


/*
 * SPリダイレクト
 * 
 * 定義された文字列を$this->request->urlもしくはwebroot内のHTMLファイル名と比較し、
 * 一致していたら$this->sp_redirect()を自動実行します。
 * 
 * また、
 * '/file_PC.html' => '/file_SP.html' や
 * '/file_PC.html' => '/controller/file_SP_action'
 * の形で指定することで、
 * PC側だけにあるファイル『file_PC.html』へのアクセスを、 SP側のファイル『/sp/file_SP.html』 へ転送することが出来ます
 * 
 * 例：案件URLが「http://pXXXX.eztest.jp/案件フォルダ/」の場合
 * 
 * http://pXXXX.eztest.jp/案件フォルダ『'/file_PC.html'』
 * ↓
 * http://pXXXX.eztest.jp/案件フォルダ/sp『'/file_SP.html'』
 */
$sp_redirect_settings = array(
  '/',
  '/index.html',
  '/catalog/index', // コントローラーとビューをスラッシュ区切りで指定することで、SP側へパラメータを引き継いでリダイレクトする
  '/catalog/view', // コントローラーとビューをスラッシュ区切りで指定することで、SP側へパラメータを引き継いでリダイレクトする
  '/contact.html'
//    '/file_PC.html' => '/file_SP.html',    // 'A' => 'B' という形式で記述するとPC側AファイルからSP側Bファイルへリダイレクトする
);


// SPリダイレクト設定配列を後の処理の為にセット
if (!defined("SP_REDIRECT_SETTINGS")) {
  define('SP_REDIRECT_SETTINGS', serialize($sp_redirect_settings));
}

// SPでアクセスしてるかどうかのフラグもこちらでセット
if (!defined("EZM_IS_SP_ACCESS")) {
  if (isset($_SERVER['HTTP_USER_AGENT'])) {
    $regex_ua_spn = "/(iPhone|iPod|Android.*Mobile|BlackBerry)/";
    define("EZM_IS_SP_ACCESS", (preg_match($regex_ua_spn, $_SERVER['HTTP_USER_AGENT']) != 0));
  } else {
    define("EZM_IS_SP_ACCESS", false);
  }
}

/**
 * Load all plugin routes. See the CakePlugin documentation on
 * how to customize the loading of plugin routes.
 */
CakePlugin::routes();

/**
 * Load the CakePHP default routes. Only remove this if you do not want to use
 * the built-in default routes.
 */
require CAKE . 'Config' . DS . 'routes.php';
