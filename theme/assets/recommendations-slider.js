// document.addEventListener('DOMContentLoaded', function () {
//   const getSlider = document.querySelector('.recommendations-slider-container');

//   const slider = getSlider.querySelector('.recommendations-slider');
//   const prevBtn = getSlider.querySelector('.prev');
//   const nextBtn = getSlider.querySelector('.next');

//   let currentIndex = 0;
//   const slideWidth = document.querySelector('.recommendations-slide').clientWidth;

//   function updateSlider() {
//     const translateXValue = -currentIndex * slideWidth + 'px';
//     slider.style.transform = 'translateX(' + translateXValue + ')';
//   }

//   function goToPrev() {
//     currentIndex = Math.max(currentIndex - 1, 0);
//     updateSlider();
//   }

//   function goToNext() {
//     currentIndex = Math.min(currentIndex + 1, slider.children.length - 1);
//     updateSlider();
//   }

//   prevBtn.addEventListener('click', goToPrev);
//   nextBtn.addEventListener('click', goToNext);
// });
