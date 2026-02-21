(function () {
  if (!customElements.get('product-slider')) {
    class ProductSlider extends HTMLElement {
      constructor() {
        super();
        this.slider = null;
        this.swiper = null;
        this.resizeTimeout = null;
        this.onResize = this.handleResize.bind(this); // Bind for event listener
      }

      connectedCallback() {
        this.init();
        window.addEventListener('resize', this.onResize);
      }

      disconnectedCallback() {
        this.cleanup();
      }
    }

    ProductSlider.prototype.setupElements = function () {
      this.slider = this.querySelector('.product-slider');
    };

    ProductSlider.prototype.initSwiper = function () {
      if (!this.slider || this.swiper) return;

      const id = this.slider.dataset.sectionId;
      if (!id) return;

      this.swiper = new Swiper(`.product-slider-${id}`, {
        direction: 'horizontal',
        loop: true,
				autoHeight: true,
        navigation: {
          nextEl: '.swiper-button-next',
          prevEl: '.swiper-button-prev',
        },
      });
    };

    ProductSlider.prototype.handleResize = function () {
      clearTimeout(this.resizeTimeout);
      this.resizeTimeout = setTimeout(() => {
        this.reinitSwiper();
      }, 200); // Debounced to prevent excessive calls
    };

    ProductSlider.prototype.reinitSwiper = function () {
      if (this.swiper) {
        this.swiper.destroy(true, true);
        this.swiper = null;
      }
      this.initSwiper();
    };

    ProductSlider.prototype.cleanup = function () {
      if (this.swiper) {
        this.swiper.destroy(true, true);
        this.swiper = null;
      }

      window.removeEventListener('resize', this.onResize);
    };

    ProductSlider.prototype.init = function () {
      this.setupElements();
      this.initSwiper();
    };

    customElements.define('product-slider', ProductSlider);
  }
})();