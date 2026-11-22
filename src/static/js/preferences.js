// Loaded in <head> so the saved theme applies before the first paint.
(function () {
  var root = document.documentElement;
  var defaults = { theme: 'light', text: 'normal', radius: '10' };

  function read(key) {
    try {
      return window.localStorage.getItem('petfinder.' + key) || defaults[key];
    } catch (error) {
      return defaults[key];
    }
  }

  function write(key, value) {
    try {
      window.localStorage.setItem('petfinder.' + key, value);
      return true;
    } catch (error) {
      return false;
    }
  }

  function applyDisplay(key, value) {
    if (key === 'theme') root.dataset.theme = value;
    if (key === 'text') root.dataset.text = value;
  }

  applyDisplay('theme', read('theme'));
  applyDisplay('text', read('text'));

  document.addEventListener('DOMContentLoaded', function () {
    var status = document.querySelector('[data-preference-status]');

    document.querySelectorAll('[data-preference]').forEach(function (control) {
      var key = control.dataset.preference;
      if (control.type === 'checkbox') {
        control.checked = read(key) === control.dataset.on;
      } else {
        control.value = read(key);
      }
      control.addEventListener('change', function () {
        var value = control.type === 'checkbox'
          ? (control.checked ? control.dataset.on : defaults[key])
          : control.value;
        applyDisplay(key, value);
        var saved = write(key, value);
        if (status) {
          status.hidden = saved;
          status.textContent = saved ? '' : 'This browser blocked saving, so the change lasts only for this page.';
        }
      });
    });

    // A URL with search values keeps the distance the user searched with.
    var feedRadius = document.getElementById('radius');
    if (feedRadius && !window.location.search) {
      var radius = read('radius');
      if (Array.prototype.some.call(feedRadius.options, function (option) { return option.value === radius; })) {
        feedRadius.value = radius;
      }
    }
  });
})();
