(function () {
	function collectionTabs() {
		const collectionsTabs = document.querySelectorAll(".collection-tabs");

		if (collectionsTabs.length) {
			collectionsTabs.forEach(tabs => {
				const id = tabs.dataset.sectionId;
        const collectionTabsElement = document.getElementById(`shopify-section-${id}`);
        const collectionTabs = collectionTabsElement.querySelector('.collection-tabs');

        if (!collectionTabs) return;

        const collectionTabsWidth = window.innerWidth;
        const collectionTabsNavigation = collectionTabs.querySelectorAll('.navigation-item');
        const collectionTabsList = collectionTabs.querySelectorAll('.collection-tabs-list');

        const activateTab = (item) => {
          collectionTabsNavigation.forEach((element) => element.classList.remove('active'));
          item.classList.add('active');
 
          collectionTabsList.forEach((element) => element.classList.remove('active'));

          const tabId = item.dataset.tab;
          collectionTabs.querySelector(`[data-tab-id="${tabId}"]`).classList.add('active');
        };

        collectionTabsNavigation.forEach((item) => {
          item.addEventListener("click", () => activateTab(item));
        });

        if (collectionTabsWidth >= 1025) {
          collectionTabsNavigation.forEach((item) => {
            item.addEventListener("keyup", (event) => (event.key === "Enter" || event.key === "Space") && activateTab(item));
          });
        }
      });
    }
  }

  document.addEventListener('DOMContentLoaded', collectionTabs);
  document.addEventListener('shopify:section:load', collectionTabs);
  window.addEventListener('resize', collectionTabs);

  collectionTabs();
})();