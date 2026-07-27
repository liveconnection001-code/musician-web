//=====================================================
// 1枚目と2枚目以降の表示時間を変更するもしくは
// 1枚目のスライドが切り替わる時間を2枚目以降と合わせる
//=====================================================
const swiper = new Swiper(".swiper", {
  spaceBetween: 0,
  autoHeight: true,
  loop: true,
  loopAdditionalSlides: 1,
  speed: 1500,
  effect: "slide",

  autoplay: {
    delay: 6500,
    disableOnInteraction: false,
  },

  //メディアクエリ
  breakpoints: {
    // ウィンドウサイズが600px以下
    0: {
      slidesPerView: 1,
    },
    // ウィンドウサイズが576px以上
    576: {
      slidesPerView: 3,
    },
  },
});

swiper.on("slideChange", function () {
  // スライド切り替え時発火
  if (this.realIndex > 0) {
    // 1枚目以降の時
    this.params.autoplay.delay = 5000; // 2枚目以降の表示時間を指定
  }
});
