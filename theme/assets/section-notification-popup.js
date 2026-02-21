document.addEventListener('DOMContentLoaded', function() {
  const popup = document.querySelector('.section-notification-popup');
  const popupWrap = popup.querySelector('.notification-block');
  const closeButton = document.querySelector('.notification-close-popup');
  const maxShowTimes = parseInt(popupWrap.getAttribute('data-show-notifications'), 10);
  let closeCount = sessionStorage.getItem('popupCloseCount') || 0;

  function showPopup() {
    popup.classList.remove('popup-hidden');
  }

  function hidePopup() {
    popup.classList.add('popup-hidden');
    closeCount++;
    sessionStorage.setItem('popupCloseCount', closeCount);
  }

  if (closeCount < maxShowTimes) {
    setTimeout(showPopup, 5000);
  }

  closeButton.addEventListener('click', hidePopup);

  document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
      hidePopup();
    }
  });
});