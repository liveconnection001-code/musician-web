

/*--------------------------------------------------------------------------*
 *
 * phone Links ver.3.1  202000721 EZgate
 *  
 *--------------------------------------------------------------------------*/



$(function () {
    if (!isPhone()) {
        return;
    }

    $('span[data-action=call]').each(function () {
        var $ele = $(this);
        var textData = $(this).html().replace(/<("[^"]*"|'[^']*'|[^'">])*>/g, ''); //spanの中身をhtmlごと抜き出し、タグのみ削除する
         //console.log("panの中身をhtmlごと抜き出し"+textData);
      
      
        if (textData == "" || textData.match(/^[^0-9\-]*$/) ) { //タグを抜き出したテキストが空、もしくは数字が全く含まれない、文字列だったら

            if ($(this).children('img').length) { //imgタグがあるなら

                var telText = $(this).children('img').attr('alt'); //imgタグのaltを拾う
                telLinkAdd($ele, telText); //リンクを生成する

            } else if ($(this).children('i').length) { //<i>タグがあるなら

                var telText = $(this).children('i').data('tel'); // <i>タグのカスタムデータを拾う
                telLinkAdd($ele, telText); //リンクを生成する
               // console.log("iタグを拾った" + telfix);

            } else {
               console.log("電話番号に無効な記述がされています")
            }

          
          
          
        } else { //テキストが存在するなら
            var telText = textData;
          
            telLinkAdd($ele, telText); //リンクを生成する

        }

    });


});

function telLinkAdd($ele, telText) {
    var telfix = telText.replace(/[^0-9+]/g, ''); //数字と＋だけを抜き出す
    $ele.wrap('<a href="tel:' + telfix + '"></a>'); //親要素にリンクを生成する
  // console.log("リンクを生成した" + telfix);

}



function isPhone() {

    // Edgeを弾く
    if (navigator.userAgent.indexOf('Edge') >= 0) {
        return false;
    }

    // Android且つMobileだった場合、電話機とみなす
    if (navigator.userAgent.indexOf('Android') >= 0 && navigator.userAgent.indexOf('Mobile') >= 0) {
        return true;
    }

    // 最後はiPhoneかどうかを判定し、結果を返す
    return (navigator.userAgent.indexOf('iPhone') >= 0);
}




// html側に書き込む要素
// <span data-action="call">TEL:012-345-6789</span>
