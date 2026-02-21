'use strict';

(function () {
  if (!customElements.get('slideshow-banner')) {
    const BREAKPOINTS = {
      sm: 750,
      lg: 990,
    };

    class SlideshowBanner extends HTMLElement {
      constructor() {
        super();
        this.swiper = null;
      }

      connectedCallback() {
        this.pagination = this.querySelector('.swiper-pagination');

        this.initSwiper();
      }

      initSwiper = () => {
        const slides = this.querySelectorAll('.swiper-slide');
        const slidesLength = slides.length;
        let {
          slidesPerView = 1,
          slidesPerViewSm,
          slidesPerViewLg,
          effect,
          speed,
          autoplay,
          loop = 'false',
          spaceBetween,
          spaceBetweenPc,
        } = this.dataset;
        if (!slidesPerViewSm) slidesPerViewSm = slidesPerView;
        if (!slidesPerViewLg) slidesPerViewLg = slidesPerView;

        slidesPerView = slidesLength < +slidesPerView ? slidesLength : +slidesPerView;
        slidesPerViewSm = slidesLength < +slidesPerViewSm ? slidesLength : +slidesPerViewSm;
        slidesPerViewLg = slidesLength < +slidesPerViewLg ? slidesLength : +slidesPerViewLg;

        speed = speed * 1000;

        if (autoplay == 'true') {
          autoplay = {
            delay: speed,
            disableOnInteraction: false,
          };
        } else {
          autoplay = false;
        }

        let pagination = false;

        loop = loop == 'false' ? false : true;

        if (this.pagination) {
          pagination = {
            el: '.swiper-pagination',
            clickable: true,
          };
        }

        const swiperParams = {
          autoplay,
          slidesPerView,
          pagination,
          grabCursor: true,
          effect,
          centeredSlides: true,
          loop: loop,
          spaceBetween,
          breakpoints: {
            [BREAKPOINTS.sm]: {
              slidesPerView: slidesPerViewSm,
              spaceBetween: spaceBetweenPc,
            },
            [BREAKPOINTS.lg]: {
              slidesPerView: slidesPerViewLg,
              spaceBetween: spaceBetweenPc,
            },
          },
        };

        this.swiper = new Swiper(this, swiperParams);
      };
    }

    customElements.define('slideshow-banner', SlideshowBanner);
  }
})();
