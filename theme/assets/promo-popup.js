// document.addEventListener('DOMContentLoaded', function() {
//   const popupWrap = document.querySelector('.promo-popup-wrap');
//   const popupTimeout = parseInt(popupWrap.getAttribute('data-popup-timeout'), 10) * 1000;
//   const popupTimes = parseInt(popupWrap.getAttribute('data-popup-times'), 10);
// 	const successMessage = popupWrap.querySelector('.promo-popup-success');
//   const closeButtons = popupWrap.querySelectorAll('.promo-popup-close');
//   const overlay = popupWrap.querySelector('.overlay');
//   const form = popupWrap.querySelector('form');

//   let popupCounter = sessionStorage.getItem('popupCounter') || 0;
//   let formSubmitted = localStorage.getItem('formSubmitted') === 'true';
//   const successMessageIsShown = localStorage.getItem('successMessageIsShown') === 'true';

// 	if (formSubmitted && successMessage && !successMessageIsShown) {
//     openPopup();
//     localStorage.setItem('successMessageIsShown', 'true');
// 	}

//   function openPopup() {
//     popupWrap.style.visibility = 'visible';
//     popupWrap.style.opacity = '1';
//     popupCounter++;
//     sessionStorage.setItem('popupCounter', popupCounter);
//   }

//   function closePopup() {
//     popupWrap.style.visibility = 'hidden';
//     popupWrap.style.opacity = '0';
//   }

//   if (!formSubmitted && popupCounter < popupTimes) {
//     setTimeout(openPopup, popupTimeout);
//   }

// 	if (closeButtons.length) {
// 		closeButtons.forEach( btn => {
// 			btn.addEventListener('click', function() {
//         closePopup();
//       });

// 			btn.addEventListener('keydown', function(event) {
// 				if (event.key === 'Enter' || event.key === ' ') {
// 					closePopup();
// 				}
// 			});
// 		})
// 	}

//   overlay.addEventListener('click', function() {
//     closePopup();
//   });

//   form.addEventListener('submit', function() {
//     localStorage.setItem('formSubmitted', 'true');
//     localStorage.setItem('successMessageIsShown', 'false');
//   });

// 	const addCopyBtn = () => {
// 		const copyBtn = document.querySelector('.promo-popup-discount__copy-btn');
// 		if (!copyBtn) {
// 			return;		
// 		}

// 		const { id } = copyBtn.dataset;
// 		if (!id) {
// 			return;
// 		}

// 		const textElement = document.getElementById(`${id}`);
// 		if (!textElement) {
// 			return;	
// 		}
		
// 		const textToCopy = textElement.innerText;
// 		let timeoutId;
		
// 		copyBtn.addEventListener('click', () => {
// 			if (navigator.clipboard && navigator.clipboard.writeText) {
// 				navigator.clipboard.writeText(textToCopy).then(function () {
// 					copyBtn.classList.add('js-copied');

// 					if (timeoutId) {
// 						clearTimeout(timeoutId);
// 					}

// 					timeoutId = setTimeout(() => {
// 						copyBtn.classList.remove('js-copied');
// 						timeoutId = null; 
// 					}, 3000);
// 				})
// 			}
// 		});
// 	}

// 	addCopyBtn();
// });

document.addEventListener('DOMContentLoaded', function() {
	const popupWrap = document.querySelector('.promo-popup-wrap');
	if (!popupWrap) return;
	
	const popupTimeout = parseInt(popupWrap.getAttribute('data-popup-timeout'), 10) * 1000;
	const popupTimes = parseInt(popupWrap.getAttribute('data-popup-times'), 10);
	const successMessage = popupWrap.querySelector('.promo-popup-success');
	const closeButtons = popupWrap.querySelectorAll('.promo-popup-close');
	const overlay = popupWrap.querySelector('.overlay');
	const form = popupWrap.querySelector('form');
	
	let popupCounter = parseInt(sessionStorage.getItem('popupCounter') || 0, 10);
	let formSubmitted = localStorage.getItem('formSubmitted') === 'true';
	const successMessageIsShown = localStorage.getItem('successMessageIsShown') === 'true';
	
	if (formSubmitted && successMessage && !successMessageIsShown) {
	  openPopup();
	  localStorage.setItem('successMessageIsShown', 'true');
	}
	
	function openPopup() {
	  popupWrap.style.visibility = 'visible';
	  popupWrap.style.opacity = '1';
	  sessionStorage.setItem('popupCounter', ++popupCounter);
	}
	
	function closePopup() {
	  popupWrap.style.visibility = 'hidden';
	  popupWrap.style.opacity = '0';
	  overlay.classList.add('hidden');
	}
	
	if (!formSubmitted && popupCounter < popupTimes) {
	  setTimeout(openPopup, popupTimeout);
	}
	
	if (closeButtons.length) {
	  closeButtons.forEach(btn => {
		btn.addEventListener('click', closePopup);
		
		btn.addEventListener('keydown', function(event) {
		  if (event.key === 'Enter' || event.key === ' ') {
			closePopup();
		  }
		});
	  });
	}
	
	if (overlay) {
	  overlay.addEventListener('click', closePopup);
	}
	
	if (form) {
	  form.addEventListener('submit', function() {
		localStorage.setItem('formSubmitted', 'true');
		localStorage.setItem('successMessageIsShown', 'false');
	  });
	}
	
	function addCopyBtn() {
	  const copyBtn = document.querySelector('.promo-popup-discount__copy-btn');
	  if (!copyBtn) return;
	  
	  const { id } = copyBtn.dataset;
	  if (!id) return;
	  
	  const textElement = document.getElementById(`${id}`);
	  if (!textElement) return;
	  
	  const textToCopy = textElement.innerText;
	  let timeoutId;
	  
	  copyBtn.addEventListener('click', () => {
		if (navigator.clipboard && navigator.clipboard.writeText) {
		  navigator.clipboard.writeText(textToCopy).then(function () {
			copyBtn.classList.add('js-copied');
			
			if (timeoutId) clearTimeout(timeoutId);
			
			timeoutId = setTimeout(() => {
			  copyBtn.classList.remove('js-copied');
			  timeoutId = null;
			}, 3000);
		  });
		}
	  });
	}
	
	addCopyBtn();
  });
  