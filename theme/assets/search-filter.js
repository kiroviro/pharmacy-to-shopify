  if (!customElements.get('search-filter')) {
	class SearchFilter extends HTMLElement {
		constructor() {
			super();
		}

		connectedCallback() {
			this.init();
		}

		async init() {

			this.elements = {
				filterDetails: this.querySelectorAll('details'),
				filterSummary: this.querySelectorAll('summary'),
				loadingSpinner: this.querySelector('.loading__spinner'),
			};
			
			await this.initialFilterRendering();

			this.elements.filterItems = this.querySelectorAll('.filter-select__item:not(.holder)'),
			this.elements.filterSubmitButton = this.querySelector('.filter-value');		

			if (!this.elements.filterSubmitButton.hasAttribute('data-previous-href')) {
				this.elements.filterSubmitButton.setAttribute('data-previous-href', this.elements.filterSubmitButton.getAttribute('href'));
			}

			this.previousHref = this.elements.filterSubmitButton.getAttribute('data-previous-href');

			this.elements.filterDetails.forEach(item => {
				item.addEventListener('click', this.closeDetails.bind(this, item));
				const summary = item.querySelector('summary');
				if (summary) {
					summary.setAttribute('tabindex', '0');
					summary.addEventListener('keydown', this.handleKeyDown.bind(this, item));
					item.addEventListener('focusout', this.handleFocusOut.bind(this, item));
				}
			});

			document.addEventListener('click', this.closeAllDetails.bind(this));

			this.elements.filterItems.forEach(item => {
				item.addEventListener('click', this.onClick.bind(this, item));
				item.setAttribute('tabindex', '0');
				item.addEventListener('keydown', this.handleItemKeyDown.bind(this, item));
			});

		}

		handleKeyDown(details, event) {
			if (event.key === 'Enter' || event.key === ' ') {
				event.preventDefault();
				details.open = !details.open;
			}
		}

		handleItemKeyDown(item, event) {
			if (event.key === 'Enter' || event.key === ' ') {
				event.preventDefault();
				this.onClick(item);
			}
		}

		closeDetails(clickedItem) {
			this.elements.filterDetails.forEach(item => {
				if (item !== clickedItem) {
					item.removeAttribute('open');
				}
			});
		}

		closeAllDetails(event) {
			if (!Array.from(this.elements.filterDetails).some(item => item.contains(event.target))) {
				this.elements.filterDetails.forEach(item => {
					item.removeAttribute('open');
				});
			}
		}

		handleFocusOut(details, event) {
			setTimeout(() => {
				if (!details.contains(document.activeElement)) {
					details.removeAttribute('open');
				}
			}, 0);
		}

		onClick(clickedItem) {
			const parentDetails = clickedItem.closest('details');
			const summaryElement = parentDetails.querySelector('summary span');

			if (summaryElement) {
				summaryElement.textContent = clickedItem.textContent;
			}

			clickedItem.classList.toggle('active');
			const otherItems = parentDetails.querySelectorAll('.filter-select__item:not(.holder)');
			otherItems.forEach(item => {
				if (item !== clickedItem) {
					item.classList.remove('active');
				}
			});

			parentDetails.removeAttribute('open');

			this.updateFilters();
		}

		updateFilters() {
			const activeItems = this.querySelectorAll('.filter-select__item.active:not(.holder)');
			const dataFilterValues = Array.from(activeItems).map(item => item.getAttribute('data-filter')).join('&');
			const currentValue = this.previousHref || '';

			fetch(`${currentValue}?${dataFilterValues}`)
				.then(response => response.text())
				.then(responseText => {
					const html = responseText;
					const parsedHTML = new DOMParser().parseFromString(html, 'text/html');
					const disabledElements = parsedHTML.querySelectorAll('facet-filters-form .list-menu__item input[disabled]');

					this.elements.filterItems.forEach(filterItem => {
						const filterItemValue = filterItem.getAttribute('data-filter');
						filterItem.classList.remove('disabled');
						filterItem.removeAttribute('disabled');

						disabledElements.forEach(disabledElement => {
							const disabledValues = disabledElement.getAttribute('data-filter');

							if (filterItemValue === disabledValues) {
								filterItem.classList.add('disabled');
								filterItem.setAttribute('disabled', '');
								filterItem.setAttribute('tabindex', '-1');
							}
						});
					});
				});

			this.elements.filterSubmitButton.setAttribute('href', `${currentValue}?${dataFilterValues}`);
			this.elements.filterSubmitButton.removeAttribute('aria-disabled');
		}

		async initialFilterRendering() {
			this.elements.loadingSpinner.classList.remove('hidden');
			this.setAttribute('data-loading', 'true');		
			if(this.dataset.collection != 'all') {
				await	this.loadFilters(this.dataset.filterUrl);
			}
			this.removeAttribute('data-loading');
			this.elements.loadingSpinner.classList.add('hidden');
		}

		async loadFilters(url) {
			if (!this.elements.filterDetails) return;

			const res = await fetch(url);
			const html = await res.text();
			const parsedHTML = new DOMParser().parseFromString(html, 'text/html');

			const filtersForm = parsedHTML.querySelector('facet-filters-form')
			let summarySelector = '.facets__summary-label'
			if (!filtersForm) return;

			let filters = filtersForm.querySelectorAll('.facets__summary')

			if (filters.length == 0) {
				filters = filtersForm.querySelectorAll('.mobile-facets__summary')
				summarySelector = 'div > span'
			}

			if (filters.length == 0) return;

			this.elements.filterDetails.forEach( detail => {
				const summary = detail.querySelector('summary > span')
				const filterSelect = detail.querySelector('.filter-select')
				if (!summary || !filterSelect) return;
				const summaryText = summary.innerText.trim();

				filters.forEach(filter => {
					const filterLabel = filter.querySelector(`${summarySelector}`) 
					if (!filterLabel) return;

					const isEqual = filterLabel.innerText.includes(summaryText);
					if (!isEqual) return;
					
					const filterValues = filter.parentElement.querySelectorAll('[data-filter-value-name')
					if (!filterValues) return;

					const filterValuesMap = new Map();

					filterValues.forEach( value => {
						const { filterValueName } = value.dataset;
						const filterId = value.dataset.filter;
						if (!filterValuesMap.has(filterValueName)) {
							filterValuesMap.set(filterValueName, { filterValueName, filterId });
						}
					})

					filterValuesMap.forEach( ({ filterValueName, filterId }) => {
						filterSelect.append(this.createFilterHtml(filterId, filterValueName))
					})
				})
			})
		}

		createFilterHtml(filterId, label) {
			const li = document.createElement('li');
			li.className = 'filter-select__item';
			li.setAttribute('tabindex', '0');
			li.setAttribute('role', 'button');
			li.setAttribute('data-filter', filterId);
			li.innerText = label;

			return li;
		}
	}

	customElements.define('search-filter', SearchFilter);
}