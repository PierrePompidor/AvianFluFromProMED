// Author : Pierre Pompidor / 16/06/2023
console.log("carto.js chargé");

var map;
var mapzoom;
var cible;
var markers = [];
var markerszoom = [];
var initialLoad = true;

function setMarkers(source) {
  let nbEvents = 0;
  for (let event of source) {
    if (event.places.length > 0) {
      for (let place of event.places) {
        let CM = L.circleMarker([place.lat, place.lon], {radius:1, stroke:1, color: 'red', fillColor: '#f03', fillOpacity: 0.5});
        CM.country = place.country;
        CM.place = place.name;
        for (let property in event) CM[property] = event[property];
        CM.on("mouseover", markerSelection);
        CM.addTo(map);
        markers.push(CM);
      
        CM = L.circleMarker([place.lat, place.lon], {radius:6, stroke:1, color: 'red', fillColor: '#f03', fillOpacity: 0.5});
        CM.addTo(mapzoom);
        markerszoom.push(CM);
      }
    }
    else {
      for (let country of event.countries) {
        let CM = L.circleMarker([country.lat, country.lon], {radius:1, stroke:1, color: 'red', fillColor: '#f03', fillOpacity: 0.5});
        CM.country = country.name;
        CM.place = '';
        for (let property in event) CM[property] = event[property];
        CM.on("mouseover", markerSelection);
        CM.addTo(map);
        markers.push(CM);
      
        CM = L.circleMarker([country.lat, country.lon], {radius:1, stroke:1, color: 'red', fillColor: '#f03', fillOpacity: 0.5});
        CM.addTo(mapzoom);
        markerszoom.push(CM);
      }
    }
    nbEvents++;
  }
  document.getElementById("nbFilteredEvents").innerHTML = "<h3>"+nbEvents+"</h3>";
  if (initialLoad) {
    document.getElementById("nbEvents").innerHTML = "<h3>"+nbEvents+" events</h3>";
    initialLoad = false;
  }
}

function majMarkers(npromed) {
  let nbMarkers = npromed.length;
  console.log("Nouvelle sélection :", nbMarkers);
  for (let marker of markers) map.removeLayer(marker);
  for (let marker of markerszoom) mapzoom.removeLayer(marker);
  setMarkers(npromed);
}

async function init() {
  map = L.map('mapid', {zoomControl: false, gridControl:false, maxBoundsViscosity: 1.0}).setView([48.833, 2.333], 1); 
  mapzoom = L.map('mapzoomid', {zoomControl: false, attributionControl: false, gridControl:false, maxBoundsViscosity: 1.0}).setView([48.833, 2.333], 4);
  cible = L.circleMarker([0, 0], {radius:7, stroke:1, color: 'blue', fillColor: 'blue', fillOpacity: 0.5});
  cible.addTo(mapzoom);

  map.on('mousemove', (event) => {
    let latlng = event.latlng;
    cible.setLatLng(latlng);
    mapzoom.setView(latlng);
  });

  const responseCSV = await fetch('http://localhost:5000/data/csv');
  const promedCSV = await responseCSV.text();
  //console.log(promedCSV);
  document.getElementById("updating").style.display = 'none';

  const responseJSON = await fetch('http://localhost:5000/data/json');
  const promed = await responseJSON.json();
  console.dir(promed);

  L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {
    attribution: '©OSM', noWrap: true, bounds: [[-90, -180], [90, 180]]
  }).addTo(map);

  L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {
    attribution: '©OSM', noWrap: true, bounds: [[-90, -180], [90, 180]]
  }).addTo(mapzoom);

  setMarkers(promed);
}

function markerSelection(e) {
    let event = e.target;
    let subpost = "subpost n."+event.subpost+" : "+event.subpost_header;
    if (event.subpost == '') subpost = '';
    let mortality = '';
    if (event.mortality != '') mortality = "("+event.mortality+")";
    let places = '';
    for (let place of event.places) places += place.name;
    let subject = event.subject.split(':')[1];
    let text = event.text.slice(0, 700)+"...";

    document.getElementById("infos").innerHTML = 
    `<table style="width: auto; height: auto; padding:0; soacing:0; border:1">
    <tr><td> <center>${event.archive_number}</center></td></tr>
    <tr><td> <center><a href='${event.url}' target='_blank'>${event.url}</a></center></td></tr>
    <tr><th> ${subject}</th></tr>
    <tr><td> <center> ${event.country} ${places} </center></td></tr>
    <tr><td> <center> ${event.event_date} (Publication : ${event.publication_date}) </center> </td></tr>
    <tr><td> <center> ${subpost} </center> </td></tr>
    <tr><td> <center> Serotypes : ${event.serotypes} ${mortality} </center></td></tr>
    <tr><td style='color:red'> <center> Species : ${event.species} <center></td></tr>
    <tr><td class="border">${text}</td></tr>
    </table>`;
}
