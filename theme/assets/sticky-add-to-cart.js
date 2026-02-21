if (!customElements.get('sticky-atc-bar')) {
	function checkBarVisibility() {
	  const stickyAtcBar = document.querySelector(".sticky-atc-bar");
	  const productVisible = document.querySelector(".product .product__info-wrapper");
	  let closedBar = false;
	  const closeBtn = document.querySelector(".sticky-close-button");
  
	  document.addEventListener("scroll", (e) => {
		let productVisibleHeight = productVisible.offsetHeight / 2;
		let scrolled = document.scrollingElement.scrollTop;
	
		if (scrolled > productVisibleHeight && !closedBar) {
		  stickyAtcBar.classList.add('atc-visible');
		} else {
		  stickyAtcBar.classList.remove('atc-visible');
		}
	  });
  
	  closeBtn.addEventListener('click', () => {
		stickyAtcBar.classList.remove('atc-visible');
		closedBar = true
	  })
  
	}
  
	document.addEventListener('DOMContentLoaded', checkBarVisibility);
	document.addEventListener('shopify:section:load', checkBarVisibility);
  
	const stickyAtcSelect = document.querySelector('sticky-atc-bar .select__select');
	let atcPrice = document.querySelector('sticky-atc-bar .price-item--regular');
	let atcImage = document.querySelector('sticky-atc-bar img');
	if (stickyAtcSelect) {
	  stickyAtcSelect.onchange = function(){
		const getNewPrice = stickyAtcSelect.options[this.selectedIndex].getAttribute('data-price');
		atcPrice.innerHTML = getNewPrice;
		
		const getNewImage = stickyAtcSelect.options[this.selectedIndex].getAttribute('data-media');
		if ( getNewImage != null ) {
		  atcImage.src = getNewImage;
		}
	  };
	}

	class StickyAtcBar extends HTMLElement {
		constructor() {
			super();
		}

		connectedCallback() {
			this.select = this.querySelector('.select');
			this.formBtn = this.querySelector('.button-add-card')

			this.onVariantChange();
		}
		onVariantChange = () => {
			if (!this.select) return;
			this.select.addEventListener('change', (e) => {
				this.updateMasterId(e);
				this.renderProductInfo();
			})
		};

		updateMasterId(e) {
			this.currentVariant = e.target.value;
		}

		renderProductInfo() {
			const requestedVariantId = this.currentVariant;
			fetch(
				`${this.dataset.url}?variant=${requestedVariantId}`
			)
				.then((response) => response.text())
				.then((responseText) => {
					const html = new DOMParser().parseFromString(responseText, 'text/html');
					const addButtonUpdated = html.querySelector('.main-product .product-form__submit');
					this.toggleAddButton(
						addButtonUpdated.hasAttribute('disabled'),
						window.variantStrings.soldOut
					);

					const priceHtml = html.querySelector('.product__info-wrapper .price');
					this.updatePrice(priceHtml);
				})
				.catch((error) => {
					console.error('Error:', error);
				})
		}
		toggleAddButton(disable = true, text, modifyClass = true) {
			const addButton = this.formBtn;
			if (!addButton) return;

			const addButtonText = addButton.querySelector('span');

			if (disable) {
				addButton.setAttribute('disabled', 'disabled');
				if (text) {
					if (addButtonText) addButtonText.textContent = text;
				}
			} else {
				addButton.removeAttribute('disabled');
				if (addButtonText) addButtonText.textContent = window.variantStrings.addToCart;
			}

			if (!modifyClass) return;
		}

		updatePrice(price) {
			this.price = this.querySelector('.price');

			if (!this.price || !price) return;
			const duplicatePrice = price.cloneNode(true);
			this.price.replaceWith(duplicatePrice);
		}
	}

	customElements.define('sticky-atc-bar', StickyAtcBar);
  
}