class ImageComparison extends HTMLElement {
  constructor() {
    super();
    this.slider = null;
    this.beforeImage = null;
    this.afterImage = null;
    this.init();
  }

  init() {
    this.slider = this.querySelector(".image-comparison__range");
    this.beforeImage = this.querySelector(".image-comparison__slider-wrapper .image--before");
    this.afterImage = this.querySelector(".image-comparison__slider-wrapper .image--after");

    this.slider.addEventListener("input", () => {
      this.moveSlider();
    });

    this.moveSlider();
  }

  moveSlider() {
    const value = this.slider.value;
    this.beforeImage.style.clipPath = `inset(0 ${100 - value}% 0 0)`;
    this.afterImage.style.clipPath = `inset(0 0 0 ${value}%)`;

    const percent = (value - this.slider.min) / (this.slider.max - this.slider.min) * 100;
    const sliderElement = this.querySelector('.image-comparison__slider');
    sliderElement.style.setProperty('--percent', `${percent}%`);
  }
}

customElements.define("before-after", ImageComparison);