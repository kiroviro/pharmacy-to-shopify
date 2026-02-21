// document.addEventListener('DOMContentLoaded', function () {
//   const tabs = document.querySelectorAll('.blog-tabheader__item');

//   tabs.forEach(function (tab) {
//     tab.addEventListener('click', function (event) {
//       event.preventDefault();

//       const selectedTag = this.getAttribute('data-tag');
//       filterBlogs(selectedTag);

//       tabs.forEach(function (t) {
//         t.classList.remove('blog-tabheader__item_active');
//       });

//       this.classList.add('blog-tabheader__item_active');
//     });
//   });

//   function filterBlogs(tag) {
//     var blogItems = document.querySelectorAll('.blog-articles__article');

//     blogItems.forEach(function (item) {
//       var tags = item.getAttribute('data-tags').toLowerCase().split(',');

//       if (tag.toLowerCase() === 'all' || tags.includes(tag.toLowerCase())) {
//         item.classList.remove('item-hidden');
//       } else {
//         item.classList.add('item-hidden');
//       }
//     });
//   }
// });
