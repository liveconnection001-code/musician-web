//=====================================================
// loading
//=====================================================
const loader = document.getElementById("loading");
window.addEventListener("load", () => {
  const ms = 1000; // transitionかかる時間
  loader.style.transition = "opacity " + ms + "ms";

  const loaderOpacity = function () {
    loader.style.opacity = 0;
  };
  const loaderDisplay = function () {
    loader.style.display = "none";
  };
  setTimeout(loaderOpacity, 1500); // 何秒表示させるのか
  setTimeout(loaderDisplay, 1500 + ms); // 上と同じ数字入れる
});
