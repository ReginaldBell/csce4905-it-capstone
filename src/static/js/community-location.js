(function () {
  var picker = document.querySelector('[data-location-picker]');
  if (!picker) return;
  var latitude = picker.querySelector('[name="latitude"]');
  var longitude = picker.querySelector('[name="longitude"]');
  var status = picker.querySelector('[data-location-status]');
  var deviceButton = picker.querySelector('[data-device-location]');
  var centerButton = picker.querySelector('[data-map-center]');
  var map = null;
  var marker = null;

  function chooseLocation(lat, lng, message) {
    lng = ((lng + 180) % 360 + 360) % 360 - 180;
    latitude.value = lat.toFixed(6);
    longitude.value = lng.toFixed(6);
    status.textContent = message;
    if (map) {
      if (!marker) marker = L.marker([lat, lng]).addTo(map);
      marker.setLatLng([lat, lng]);
    }
  }

  if (window.L) {
    var hasLocation = latitude.value !== '' && longitude.value !== ''
      && Number.isFinite(Number(latitude.value)) && Number.isFinite(Number(longitude.value))
      && Math.abs(Number(latitude.value)) <= 90 && Math.abs(Number(longitude.value)) <= 180;
    var initial = hasLocation ? [Number(latitude.value), Number(longitude.value)] : [20, 0];
    map = L.map(picker.querySelector('[data-location-map]')).setView(initial, hasLocation ? 13 : 2);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    map.on('click', function (event) {
      chooseLocation(event.latlng.lat, event.latlng.lng, 'Location selected on the map.');
    });
    if (hasLocation) chooseLocation(initial[0], initial[1], 'Your selected location is marked.');
    centerButton.addEventListener('click', function () {
      var center = map.getCenter();
      chooseLocation(center.lat, center.lng, 'Map center selected.');
    });
    centerButton.disabled = false;
  } else {
    centerButton.disabled = true;
    status.textContent = 'The map could not load. Check your connection, or use your device location.';
  }

  deviceButton.addEventListener('click', function () {
    if (!window.isSecureContext || !navigator.geolocation) {
      status.textContent = 'Device location needs HTTPS or localhost. You can choose an area on the map.';
      return;
    }
    deviceButton.disabled = true;
    status.textContent = 'Waiting for your location permission...';
    navigator.geolocation.getCurrentPosition(function (position) {
      deviceButton.disabled = false;
      var lat = position.coords.latitude;
      var lng = position.coords.longitude;
      if (map) map.setView([lat, lng], 14);
      chooseLocation(lat, lng, 'Device location selected. You can adjust the spot on the map.');
    }, function (error) {
      deviceButton.disabled = false;
      status.textContent = error.code === 1
        ? 'Location permission was denied. Choose an area on the map instead.'
        : 'Your location is unavailable. Try again or choose an area on the map.';
    }, {timeout: 10000, maximumAge: 60000});
  });
  deviceButton.disabled = false;
})();
