const scrollToTopWrp = document.querySelector('.scroll-to-top');
const scrollToTopBtn = scrollToTopWrp.querySelector('.scrollToTop');

function showScrollToTop() {
  if (document.body.scrollTop > (window.innerHeight / 2) || document.documentElement.scrollTop > (window.innerHeight / 2)) {
    scrollToTopWrp.classList.add('active');
  } else {
    scrollToTopWrp.classList.remove('active');
  }
}

window.addEventListener('scroll', () => {
  showScrollToTop();
});

function scrollToTop() {
  let position = document.body.scrollTop || document.documentElement.scrollTop;
  let scrollAnimation;

  if (position) {
    window.scrollBy(0, -Math.max(1, Math.floor(position / 10)));
    scrollAnimation = setTimeout("scrollToTop()", 30);
    window.addEventListener('wheel', () => {
      clearTimeout(scrollAnimation);
    });

  } else {
    clearTimeout(scrollAnimation);
  }
}

scrollToTopBtn.addEventListener('click', () => {
  scrollToTop();
});