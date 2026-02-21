'use strict';
(function () {

	if (!customElements.get('card-slider')) {
		class CardSlider extends HTMLElement {
			constructor() {
				super();
				this.swiper = null;
				this.slider = this.querySelector('.swiper');
				let loop = this.dataset.loop === "true" ? true : false;
				let autoplay = this.dataset.autoplay === "true" ? true : false;

				this.nextBtn = this.querySelector('.swiper-button-next');
				this.prevBtn = this.querySelector('.swiper-button-prev');
				
				this.swiperParams = {
					loop,
					autoplay,
					speed: 1000,
					delay: 1000,
					slidesPerView: 1,
					grabCursor: true,
					loopFillGroupWithBlank: true,
  					loopAdditionalSlides: 1.5,
					loopPreventsSliding: true,
          on: {
            slideChange: this.updateNavigationButtons,
            init: this.updateNavigationButtons,
						autoplay: () => {
              this.updateNavigationButtons();
            }
          },
				};

				if (this.nextBtn) {
					this.nextBtn.addEventListener('click', () => {
						if (this.swiper) this.swiper.slideNext();
					});
				}
				if (this.prevBtn) {
					this.prevBtn.addEventListener('click', () => {
						if (this.swiper) this.swiper.slidePrev();
					});
				}
			}

			connectedCallback() {
				if (this.slider) {
					this.initSwiper();
				}
			}

			initSwiper() {
				this.swiper = new Swiper(this.slider, this.swiperParams);				
				this.updateNavigationButtons();
			}

      updateNavigationButtons = () => {
        if (!this.swiper) return;
				if (this.swiper.isBeginning && !this.swiper.isEnd) {
					this.nextBtn.classList.remove('disabled');
					this.prevBtn.classList.add('disabled');
				} else if (this.swiper.isEnd && !this.swiper.isBeginning) {
					this.prevBtn.classList.remove('disabled');
					this.nextBtn.classList.add('disabled');
				} else if (this.swiper.isEnd && this.swiper.isBeginning) {
					this.prevBtn.classList.add('disabled');
					this.nextBtn.classList.add('disabled');
				} else {
					this.prevBtn.classList.remove('disabled');
					this.nextBtn.classList.remove('disabled');
				}
      };
		}

		customElements.define('card-slider', CardSlider);
	}
	
})();
