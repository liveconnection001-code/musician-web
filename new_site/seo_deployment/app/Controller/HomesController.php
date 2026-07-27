<?php

class HomesController extends AppController {

  public $name    = 'Homes';
  public $uses    = array('Calendar');
  public $helpers = array('Ezm', 'Jqs', 'EzCalendar');


  public function index() {
    $shop_order_config = $this->_shop_order();
    if (!empty($shop_order_config)) {
      $this->set(compact('shop_order_config'));

      if (!empty($shop_order_config['ShopOrderConfiguration']['tax']) && !empty($shop_order_config['ShopOrderConfiguration']['tax2'])) {
        $tax = array('A' => $shop_order_config['ShopOrderConfiguration']['tax'], 'B' => $shop_order_config['ShopOrderConfiguration']['tax2']);
      } elseif (!empty($shop_order_config['ShopOrderConfiguration']['tax']) && empty($shop_order_config['ShopOrderConfiguration']['tax2'])) {
        $tax = array('A' => $shop_order_config['ShopOrderConfiguration']['tax'], 'B' => '');
      } elseif (empty($shop_order_config['ShopOrderConfiguration']['tax'])) {
        $tax = array('A' => 0, 'B' => '');
      }
      $this->set(compact('tax'));
    }
  }

  public function maintenance() {
    return $this->not_found();
  }

  public function contact() {
    $id = intval($this->request->query('id'));

    if ($id > 0) {
      // モデル初期化
      $this->CatalogBox      = ClassRegistry::init('CatalogBox');
      $this->CatalogCategory = ClassRegistry::init('CatalogCategory');

      // データ取得
      $box         = $this->CatalogBox->find('first', array('conditions' => array('id' => $id)));
      $category_id = isset($box['CatalogBox']['category_id']) ? intval($box['CatalogBox']['category_id']) : 0;
      if ($category_id > 0) {
        $category = $this->CatalogCategory->find('first', array('conditions' => array('id' => $category_id)));
        $this->set('category', $category);
      }
      $this->set('category_id', $category_id);
      $this->set('box', $box);
    }

    $this->set('id', $id);
  }


  public function login() {
    return $this->not_found();
  }


  public function webroot($file) {
    $this->webroot_file = $file;
    $requested = str_replace('\\', '/', (string)$file);

    if ($requested === '' || strtolower(pathinfo($requested, PATHINFO_EXTENSION)) !== 'html' || strpos($requested, chr(0)) !== false || preg_match('#(^|/)\.\.(/|$)#', $requested)) {
      return $this->not_found();
    }

    $root = realpath(WWW_ROOT);
    $resolved = realpath(WWW_ROOT . str_replace('/', DS, ltrim($requested, '/')));
    if ($root === false || $resolved === false || !is_file($resolved) || strpos($resolved, $root . DS) !== 0) {
      return $this->not_found();
    }

    $this->set('file', $resolved);
  }


  public function not_found() {
    $this->layout = false;
    $this->response->statusCode(404);
    $this->response->type('html');
    $this->render('/Errors/error400');
  }

  public function robots() {
    $this->layout = "ajax";
    $this->response->type("text/plain");
  }
}
