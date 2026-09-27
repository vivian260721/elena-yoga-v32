(function () {
  function tryInitPoseCarousel() {
    const el = document.querySelector(".pose-carousel");

    if (!el) {
      setTimeout(tryInitPoseCarousel, 50);
      return;
    }
    if (typeof Swiper === "undefined") {
      setTimeout(tryInitPoseCarousel, 50);
      return;
    }
    if (el.swiper) {
      return;
    }

    const defaultIndex = parseInt(el.dataset.defaultIndex || "0", 10);

    const swiper = new Swiper(el, {
      effect: "coverflow",
      grabCursor: true,
      centeredSlides: true,
      slidesPerView: "auto",
      spaceBetween: 40, // 保持漂亮的間距與背景露出
      speed: 400,
      coverflowEffect: { 
        rotate: 0, 
        stretch: 0,       
        depth: 100,       
        modifier: 1.5,    
        slideShadows: false 
      },
      slideToClickedSlide: true, // 🌟 恢復官方內建的點擊切換！由 Swiper 自家演算法計算方向，絕對不會方向錯亂
      observer: true,
      observeParents: true,
      resistanceRatio: 0.85,
      on: {
        init: function (swiper) { 
          updateActiveCard(swiper); 
        },
        slideChange: function (swiper) { 
          updateActiveCard(swiper); 
        }
      },
    });

    swiper.slideTo(defaultIndex, 0);
  }

  function updateActiveCard(swiper) {
    swiper.slides.forEach((slide, index) => {
      const card = slide.querySelector(".pose-carousel-card");
      const status = slide.querySelector(".pose-carousel-status");
      const video = slide.querySelector(".pose-carousel-video");
      if (!card) return;

      const isActive = index === swiper.activeIndex;
      if (status) status.textContent = isActive ? "CURRENT" : "SELECT";

      // 嚴格控制：只有正中間的卡片影片可以點擊播放，旁邊的自動暫停並鎖定
      if (video) {
        if (isActive) {
          video.style.pointerEvents = "auto";
        } else {
          video.style.pointerEvents = "none";
          if (!video.paused) {
            video.pause();
          }
        }
      }

      if (isActive && window.emitEvent) {
        emitEvent("pose_carousel_center_change", {
          poseId: card.dataset.poseId,
          poseName: card.dataset.poseName,
        });
      }
    });
  }

  if (document.readyState === "complete") {
    tryInitPoseCarousel();
  } else {
    window.addEventListener("load", tryInitPoseCarousel);
  }
})();
