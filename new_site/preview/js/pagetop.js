$(function(){
 
    // 「ページトップへ」の要素を隠す
    $('#pagetop').hide();
 
    // スクロールした場合
    $(window).scroll(function(){
        // スクロール位置が100を超えた場合
        if ($(this).scrollTop() > 100) {
            // 「ページトップへ」をフェードイン
            $('#pagetop').fadeIn();
        }
        // スクロール位置が100以下の場合
        else {
            // 「ページトップへ」をフェードアウト
            $('#pagetop').fadeOut();
        }
    });
 
    // 「ページトップへ」をクリックした場合
    $('#pagetop').click(function(){
        // ページトップにスクロール
        $('html,body').animate({
            scrollTop: 0
        }, 300);
        return false;
    });
		
		
 
});