/* Cartola page marker — collapse/expand logic now lives in collapse-ui.js */
(function () {
  function onReady(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
      return;
    }
    fn();
  }
  onReady(function () {
    var marker = document.querySelector("#cartola-page");
    if (marker) document.body.classList.add("cartola-page");
  });
})();
