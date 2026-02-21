document.addEventListener('DOMContentLoaded', () => {
  const progress = document.querySelector('.article-template__top-progress');
  const progressLine = document.querySelector('.article-template__top-progress span');
  const progressWrapper = document.querySelector('.article-template__top-wrapper.sticky-post');
  const sectionHeader = document.querySelector('.section-header');
  let totalHeight = sectionHeader.getBoundingClientRect().bottom;
  let scrollColor = progressWrapper ? progressWrapper.dataset.colorSheme : null;

  let windowHeight = document.documentElement.clientHeight;

  function progressScroll() {
    let windowScroll = window.scrollY;
    let progressLineWidth = (windowScroll / (document.documentElement.scrollHeight - windowHeight)) * 100;
    totalHeight = sectionHeader.getBoundingClientRect().bottom;

    if (progress) {
      progressLine.style.width = `${progressLineWidth}%`;
      progress.style.top = `${totalHeight}px`;
    }

    if (progressWrapper && progressLineWidth > 5) {
      progressWrapper.classList.add('on-scroll');
      if (scrollColor) {
        progressWrapper.classList.add(scrollColor);
      }

			if (progress) {
				progressWrapper.style.top = `${totalHeight + 3}px`;
			} else {
				progressWrapper.style.top = `${totalHeight}px`;
			}
    } else if (progressWrapper) {
      progressWrapper.classList.remove('on-scroll');
      if (scrollColor) {
        progressWrapper.classList.remove(scrollColor);
      }
      progressWrapper.style.top = `-3rem`;
    }
  }

  let animationId;

  function animateProgress() {
    cancelAnimationFrame(animationId);
    animationId = requestAnimationFrame(progressScroll);
  }

  if (progress || progressWrapper) {
    window.addEventListener('scroll', animateProgress);
    window.addEventListener('resize', () => {
      windowHeight = document.documentElement.clientHeight;
      animateProgress();
    });
  }
});
