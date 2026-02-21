class CompareDrawer extends HTMLElement {
  constructor() {
    super();

    const compareBanner = this;
    let compareCheckboxes = document.querySelectorAll('.product-compare-checkbox');

    const selectedCount = this.querySelector('.compare-banner__top-counter');
    this.compareBannerItems = this.querySelector('.compare-banner__product-items');
    let compareProductsList = JSON.parse(localStorage.getItem('compareProducts') || '[]');

    if (compareProductsList.length > 0) {
      compareBanner.classList.add('half-open');
      this.initialCheckboxState();
      this.controlCheckboxLimit();
      this.updateSelectedCount();
      this.renderCompareDrawer();
    }

    const checkRelatedproducts = document.querySelectorAll('facet-filters-form');
    if (checkRelatedproducts) {
      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
            mutation.addedNodes.forEach((addedNode) => {
              if (addedNode.nodeType === 1 && addedNode.classList.contains('collection')) {
                compareCheckboxes = document.querySelectorAll('.product-compare-checkbox');
                this.addCheckboxListeners(compareCheckboxes);
                this.initialCheckboxState();
              }
            });
          }
        });
      });

      const config = {
        childList: true,
        subtree: true,
      };
      observer.observe(document.body, config);
    }

    this.toggleOpenButton = this.querySelector('.compare-banner__top-show-btn');
    this.toggleOpenButton.addEventListener('click', function() {
      compareBanner.classList.add('half-open');
      compareBanner.classList.toggle('open');
    });

    const buttonClearCheckedItems = this.querySelector('.compare-banner__top-btn-compare-clear');
    buttonClearCheckedItems.addEventListener('click', () => {
      compareCheckboxes.forEach((checkbox) => {
        checkbox.checked = false;
        checkbox.disabled = false;
      });

      selectedCount.textContent = 0;
      localStorage.removeItem("compareProducts");
      compareProductsList = JSON.parse(localStorage.getItem('compareProducts')) || [];
      this.clearLocalStorage();
      this.controlCheckboxLimit();
      this.renderCompareDrawer();
      compareBanner.classList.remove('half-open');
      compareBanner.classList.remove('open');
    });

    compareCheckboxes.forEach((checkbox) => {
      checkbox.addEventListener('change', () => {

        const productID = checkbox.getAttribute('data-product-id');

        if (checkbox.checked) {
          this.updateLocalStorage(productID);
        } else {
          this.clearDublicates(checkbox);
          this.removeFromLocalStorage(productID);
        }

        this.updateSelectedCount();
        this.controlCheckboxLimit();
        this.renderCompareDrawer();

				if (this.compareProductCount > 0) {
					this.classList.add('open');
				}
      });
    });

    this.addEventListener('click', (event) => {
      if (event.target.classList.contains('remove-compare-product')) {

        const productId = event.target.getAttribute('data-product-id');
        const checkboxes = document.querySelectorAll(`.product-compare-checkbox[data-product-id="${productId}"]`);
        
        checkboxes.forEach((checkbox) => {
          checkbox.checked = false;
        });
    
        this.removeFromLocalStorage(productId);
        this.updateSelectedCount();
        this.controlCheckboxLimit();
        this.renderCompareDrawer();
      }
    });
  }

  addCheckboxListeners(compareCheckboxes) {
    compareCheckboxes.forEach((checkbox) => {
      checkbox.addEventListener('change', () => {
        const productID = checkbox.getAttribute('data-product-id');

        if (checkbox.checked) {
          this.updateLocalStorage(productID);
        } else {
          this.clearDublicates(checkbox);
          this.removeFromLocalStorage(productID);
        }

        this.updateSelectedCount();
        this.controlCheckboxLimit();
        this.renderCompareDrawer();
        this.classList.add('open');
      });
    });
  }

  clearDublicates(checkbox) {
    const productId = checkbox.getAttribute('data-product-id');
    const checkboxes = document.querySelectorAll(`.product-compare-checkbox[data-product-id="${productId}"]`);
    checkboxes.forEach((checkbox) => {
      checkbox.checked = false;
    });
  }

  clearLocalStorage() {
    let compareProductsList = [];
    localStorage.setItem('compareProducts', JSON.stringify(compareProductsList));
    compareProductsList = JSON.parse(localStorage.getItem('compareProducts')) || [];
  }

  removeFromLocalStorage(productID) {
    let compareProductsList = JSON.parse(localStorage.getItem('compareProducts'));
    compareProductsList = compareProductsList.filter(product => product.productId !== productID);
    localStorage.setItem('compareProducts', JSON.stringify(compareProductsList));
  }

  updateLocalStorage(productID) {

    let compareProductsList = JSON.parse(localStorage.getItem('compareProducts')) || [];
    const checkedCheckbox = document.querySelector(`.product-compare-checkbox[data-product-id="${productID}"]`);

    const productId = checkedCheckbox.getAttribute('data-product-id');
    const url = checkedCheckbox.getAttribute('data-product-url');
    const productUrl = url.split('?')[0];

    if (!compareProductsList.some(product => product.productId === productID)) {
      compareProductsList.push({ productId, productUrl });
    }

    localStorage.setItem('compareProducts', JSON.stringify(compareProductsList));
    compareProductsList = JSON.parse(localStorage.getItem('compareProducts')) || [];
  }

  updateSelectedCount() {
    const compareProductsList = JSON.parse(localStorage.getItem('compareProducts')) || [];
    const selectedCount = document.querySelector('.compare-banner__top-counter');
    const compareButton = document.querySelector('.compare-banner__top-btn-compare');
    selectedCount.textContent = compareProductsList.length;
    if (compareProductsList.length >= 2){
      compareButton.classList.remove('disabled');
    } else {
      compareButton.classList.add('disabled');
    }
  }

  controlCheckboxLimit() {
    let compareProductsList = JSON.parse(localStorage.getItem('compareProducts')) || [];
    const uniqueProductIds = new Set(compareProductsList.map(product => product.productId));
    const compareCheckboxes = document.querySelectorAll('.product-compare-checkbox');
  
    if (uniqueProductIds.size >= 4) {
      compareCheckboxes.forEach((checkbox) => {
        if (!checkbox.checked) {
          checkbox.classList.add('disabled');
          checkbox.setAttribute('disabled', '');
        }
      });
    } else {
      compareCheckboxes.forEach((checkbox) => {
        checkbox.classList.remove('disabled');
        checkbox.removeAttribute('disabled');
      });
    }
  }

  initialCheckboxState() {
    const compareProductsList = JSON.parse(localStorage.getItem('compareProducts'));
    compareProductsList.forEach(product => {
      document.querySelectorAll(`.product-compare-checkbox[data-product-id="${product.productId}"]`).forEach((checkbox) => {
        checkbox.checked = true;
      });
    });
  }

  static getSelectedProducts() {
    return JSON.parse(localStorage.getItem('compareProducts')) || [];
  }

  static async getDrawerProducts(compareProducts) {
    const tempHtml = {};
    await Promise.all(
      compareProducts.map(async (product) => {
        await fetch(`${product.productUrl}?sections=compare-drawer-product`)
          .then((response) => response.text())
          .then((html) => {
            tempHtml[product.productId] = html;
          });
      })
    );

    const returnHtml = [];
    compareProducts.forEach((product) => returnHtml.push(tempHtml[product.productId]));
    return returnHtml;
  }
  
  async renderCompareDrawer() {
    const compareProducts = CompareDrawer.getSelectedProducts();
    const compareProductCount = compareProducts.length;
    const placeholdersNeeded = Math.max(0, 4 - compareProductCount);
    this.compareBannerItems.innerHTML = '';
		this.compareProductCount = compareProductCount;
  
    if (compareProductCount > 0) {
      const compareProductHtmlArr = await CompareDrawer.getDrawerProducts(compareProducts);
  
      compareProductHtmlArr.forEach((html) => {
        const htmlObj = JSON.parse(html);
        const htmlString = htmlObj["compare-drawer-product"];
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = htmlString;
        const compareProductItem = tempDiv.querySelector('.compare-banner__product-item');
        this.compareBannerItems.appendChild(compareProductItem);
      });
    }
  
    for (let i = 0; i < placeholdersNeeded; i++) {
      const placeholder = document.createElement('div');
      placeholder.classList.add('compare-banner__product-item');
      placeholder.innerHTML = `<div class="compare-banner__product-item__empty-msg">${window.compareStrings.selectProduct}</div>`;
      this.compareBannerItems.appendChild(placeholder);
    }
		if (compareProductCount === 0) {
      const compareItems = document.querySelectorAll('compare-modal, compare-drawer');
			compareItems.forEach((item) => {
				item.classList.remove('open');
				item.classList.remove('half-open');
      });
      document.body.classList.remove('overflow-hidden');
    }		

    this.initialCheckboxState();
  }
}

customElements.define('compare-drawer', CompareDrawer);

class CompareModal extends HTMLElement {
  constructor() {
    super();
    const compareModal = this;
    const compareBanner = document.querySelector('compare-drawer.compare-banner');
    let compareProductsList = JSON.parse(localStorage.getItem('compareProducts') || '[]');

    this.compareArea = compareModal.querySelector('.compare-modal-content');
    const showModalButton = document.querySelector('.compare-banner__top-btn-compare');
    const closeModal = document.querySelector('.compare-modal-close');
    const selectedCount = document.querySelector('.compare-banner__top-counter');


    showModalButton.addEventListener('click', function() {
      compareModal.classList.add('open');
      document.body.classList.add('overflow-hidden');
      compareModal.renderCompareTable();
    });

    closeModal.addEventListener('click', function() {
      compareModal.classList.remove('open');
      document.body.classList.remove('overflow-hidden');
    });

    const clearProducts = this.querySelector('.clear-compare-modal-products');
    clearProducts.addEventListener('click', () => {

      compareModal.classList.remove('open');
      document.body.classList.remove('overflow-hidden');
      compareBanner.classList.remove('half-open');
      compareBanner.classList.remove('open');

      const compareCheckboxes = document.querySelectorAll('.product-compare-checkbox');
      compareCheckboxes.forEach((checkbox) => {
        checkbox.checked = false;
        checkbox.disabled = false;
      });

      selectedCount.textContent = 0;
      localStorage.removeItem("compareProducts");
      compareProductsList = JSON.parse(localStorage.getItem('compareProducts')) || [];

      this.clearLocalStorage();
      this.renderCompareDrawer();
      this.updateSelectedCount();
      this.controlCheckboxLimit();
    });

    this.addEventListener('click', (event) => {
      if (event.target.classList.contains('remove-compare-product')) {

        const productId = event.target.getAttribute('data-product-id');
        const checkboxes = document.querySelectorAll(`.product-compare-checkbox[data-product-id="${productId}"]`);
        
        checkboxes.forEach((checkbox) => {
          checkbox.checked = false;
        });

        const compareProducts = document.querySelectorAll('.compare-product-modal');
        compareProducts.forEach((product) => {
          if (product.getAttribute('data-product-id') == productId) {
            product.remove();
          } 
        });

        this.removeFromLocalStorage(productId);
        this.updateSelectedCount();
        this.controlCheckboxLimit();
        compareBanner.renderCompareDrawer();
      }
    })
  }

  clearLocalStorage() {
    let compareProductsList = [];
    localStorage.setItem('compareProducts', JSON.stringify(compareProductsList));
    compareProductsList = JSON.parse(localStorage.getItem('compareProducts')) || [];
  }

  removeFromLocalStorage(productID) {
    let compareProductsList = JSON.parse(localStorage.getItem('compareProducts'));
    compareProductsList = compareProductsList.filter(product => product.productId !== productID);
    localStorage.setItem('compareProducts', JSON.stringify(compareProductsList));
  }

  updateSelectedCount() {
    const compareProductsList = JSON.parse(localStorage.getItem('compareProducts')) || [];
    const selectedCount = document.querySelector('.compare-banner__top-counter');
    const compareButton = document.querySelector('.compare-banner__top-btn-compare');
    selectedCount.textContent = compareProductsList.length;
    if (compareProductsList.length >= 2){
      compareButton.classList.remove('disabled');
    } else {
      compareButton.classList.add('disabled');
    }
  }

  controlCheckboxLimit() {
    let compareProductsList = JSON.parse(localStorage.getItem('compareProducts')) || [];
    const uniqueProductIds = new Set(compareProductsList.map(product => product.productId));
    const compareCheckboxes = document.querySelectorAll('.product-compare-checkbox');
  
    if (uniqueProductIds.size >= 4) {
      compareCheckboxes.forEach((checkbox) => {
        if (!checkbox.checked) {
          checkbox.classList.add('disabled');
          checkbox.setAttribute('disabled', '');
        }
      });
    } else {
      compareCheckboxes.forEach((checkbox) => {
        checkbox.classList.remove('disabled');
        checkbox.removeAttribute('disabled');
      });
    }
  }
  

  static getSelectedProducts() {
    return JSON.parse(localStorage.getItem('compareProducts')) || [];
  }

  static async getModalProducts(compareProducts) {
    const tempHtml = [];
    await Promise.all(
      compareProducts.map(async (product) => {
        const response = await fetch(`${product.productUrl}`);
        if (response.ok) {
          const tmpl = document.createElement('template');
          tmpl.innerHTML = await response.text();
          
          const compareEl = tmpl.content.querySelector('.section-compare');
          if (compareEl) {
            tempHtml[product.productId] = compareEl.outerHTML;
          } 
        }
      })
    );

    const returnHtml = [];
    compareProducts.forEach((product) => returnHtml.push(tempHtml[product.productId]));
    return returnHtml;
  }

  async renderCompareTable() {
    const loadingSpinner = this.querySelector('.loading__spinner');
    loadingSpinner.classList.remove('hidden');
    this.compareArea.innerHTML = '';

    const compareProducts = CompareModal.getSelectedProducts();

    if (compareProducts) {

      this.compareArea.dataset.compareCount = compareProducts.length;

      const compareProductHtmlArr = await CompareModal.getModalProducts(compareProducts);
      const compareFieldsArr = [];

      if (compareProductHtmlArr.length > 0) {

        compareProductHtmlArr.forEach((compareProductHtml) => {


          const responseHTML = document.implementation.createHTMLDocument();
          responseHTML.documentElement.innerHTML = compareProductHtml;
          
          responseHTML.querySelectorAll('.shopify-section > div').forEach((compareField) => {
            
            if (!compareFieldsArr[compareField.dataset.compareKey]) {
              compareFieldsArr[compareField.dataset.compareKey] = [];
            }

            compareFieldsArr[compareField.dataset.compareKey].push(compareField);
          });
        });

        const compareElem = document.createElement('div');
        compareElem.className = 'compare-temp';

        Object.entries(compareFieldsArr).forEach(([key, value]) => {

          if (!value.every((elem) => !!elem.dataset.isEmptyMetafield)) {
            const compareRow = document.createElement('div');

            compareRow.className = `compare-row compare-row--${
              key.includes('metafield') ? 'metafield' : key.replace('compare-', '')
            }`;

            value.forEach((elem) => compareRow.appendChild(elem));
            compareElem.appendChild(compareRow);
          }
        });

        this.compareArea.innerHTML = compareElem.innerHTML;

      } else {
        this.compareArea.innerHTML = `${window.compareStrings.unableToCompare}${
          Shopify.designMode
            ? ` ${window.compareStrings.ensureEnabled}`
            : ` ${window.compareStrings.tryAgainLater}`
        }`;
      }

      setTimeout(() => {
        loadingSpinner.classList.add('hidden');
      }, 100);
    }
  }

  static async getDrawerProducts(compareProducts) {
    const tempHtml = {};
    await Promise.all(
      compareProducts.map(async (product) => {
        await fetch(`${product.productUrl}?sections=compare-drawer-product`)
          .then((response) => response.text())
          .then((html) => {
            tempHtml[product.productId] = html;
          });
      })
    );

    const returnHtml = [];
    compareProducts.forEach((product) => returnHtml.push(tempHtml[product.productId]));
    return returnHtml;
  }

  async renderCompareDrawer() {
    const compareProducts = CompareDrawer.getSelectedProducts();
    const compareProductCount = compareProducts.length;
    const placeholdersNeeded = Math.max(0, 4 - compareProductCount);
    const compareBannerItems = document.querySelector('.compare-banner__product-items');
    compareBannerItems.innerHTML = '';
		this.compareProductCount = compareProductCount;
  
    if (compareProductCount > 0) {
      const compareProductHtmlArr = await CompareDrawer.getDrawerProducts(compareProducts);
  
      compareProductHtmlArr.forEach((html) => {
        const htmlObj = JSON.parse(html);
        const htmlString = htmlObj["compare-drawer-product"];
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = htmlString;
        const compareProductItem = tempDiv.querySelector('.compare-banner__product-item');
        compareBannerItems.appendChild(compareProductItem);
      });
    }
  
    for (let i = 0; i < placeholdersNeeded; i++) {
      const placeholder = document.createElement('div');
      placeholder.classList.add('compare-banner__product-item');
      placeholder.innerHTML = `<div class="compare-banner__product-item__empty-msg">${window.compareStrings.selectProduct}</div>`;
      compareBannerItems.appendChild(placeholder);
    }

    if (compareProductCount === 0) {
			const compareItems = document.querySelectorAll('compare-modal, compare-drawer');
			compareItems.forEach((item) => {
				item.classList.remove('open');
      });
      document.body.classList.remove('overflow-hidden');
    }
  }

}

customElements.define('compare-modal', CompareModal);