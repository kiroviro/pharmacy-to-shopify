window.addEventListener('DOMContentLoaded', () => {
  const box = document.getElementById('box');
  const indicator = document.getElementById('indicator');
  const indicatorWrapper = document.querySelector('.indicator__wrapper');

  function updateIndicator() {
    const maxScroll = box.scrollWidth - box.clientWidth;
    const scrollFraction = box.scrollLeft / maxScroll;
    const indicatorMaxScroll = indicatorWrapper.clientWidth - indicator.clientWidth;
    indicator.style.transform = `translateX(${scrollFraction * indicatorMaxScroll}px)`;
  }

  function setupScroll() {
    box.addEventListener('scroll', updateIndicator);
    indicator.style.width = `${indicatorWrapper.clientWidth / 2}px`;
    updateIndicator();
  }

  if (window.innerWidth < 767) {
    setupScroll();
  }

  window.addEventListener('resize', () => {
    if (window.innerWidth < 767) {
      setupScroll();
    } else {
      box.removeEventListener('scroll', updateIndicator);
    }
  });
});
