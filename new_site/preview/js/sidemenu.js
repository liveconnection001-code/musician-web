/*--------------------------------------------------------------------------*
 *
 * 罔��768px篁ヤ������ｃ�����≪�潟�若���ｃ���潟�������泣�ゃ���＜���ャ�� ver.2  20200605 EZgate
 *  
 *--------------------------------------------------------------------------*/

$(function () {

    const BreakPoint = 768; //�����ゃ�����ゃ�潟����紊������翫���������ゃ��紊��������������

    $(".accordion dt").on("click", function () {
      
        const windowWidth = window.innerWidth;
 
        if (windowWidth < BreakPoint) {
            $(this).next().slideToggle();
            $(this).toggleClass("active");
        }
    });


    function sideMenuControll() {

        const windowWidth = window.innerWidth;

        if (windowWidth >= BreakPoint) {
            $(".accordion dd").css('display', 'block');
            $(".accordion dt").removeClass('active');
        } else {
            $(".accordion dd").css('display', 'none');
            $(".accordion dt").removeClass('active');
        }
    }


    let timer = false;
    var currentWidth = window.innerWidth; // ���ゃ�潟������┴綛���篆���

    $(window).on("orientationchange resize", function() {
        if (timer !== false) {
            clearTimeout(timer);
        }

        timer = setTimeout(function () {

            if (currentWidth == window.innerWidth) { // ���ゃ�潟����┴綛���紊���ｃ�������������������㏍�ｃ�潟�祉����
                return;
            }
            // ���ゃ�潟����┴綛���紊���ｃ�����с���泣�ゃ�冴���������
            currentWidth = window.innerWidth; // 罔�����贋��
            sideMenuControll();


        }, 200);

    });

});
