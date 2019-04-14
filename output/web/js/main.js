var svg;
var svgWidth = 1365;
var svgHeight = 1138;
var extraSpaceForWidth = 10;
var extraSpaceForHeight = 10;

function calculateRatio(width, height) {
  var widthRatio = width / svgWidth;
  var heightRatio = height / svgHeight;
  return Math.min(widthRatio, heightRatio);
}

function calculateCanvasSize() {
  var mapWidth = $("#map-container").width(),
      mapHeight = $(window).height()-70;
  var ratio = calculateRatio(mapWidth, mapHeight);
  var width = svgWidth * ratio,
      height = svgHeight * ratio;
  $("#map-container").width(width).height(height);
}

function onSvgLoaded() {
  svg = $("#map-container").svg('get');
  var s = $('svg').get(0);
  var bbox = s.getBBox();
  s.setAttribute('viewBox', '0 0 ' + (bbox.width+extraSpaceForWidth) + ' ' + bbox.height);
  s.setAttribute('width', '100%');
  s.setAttribute('height', '100%');

  $("text", svg.root()).each(function() {
    var text = $(this).text().trim();
    if (text.startsWith("http") || $(this).attr('fill') == 'gray') {
      return;
    }

    $(this).css('cursor', 'pointer')
           .on('click', function() {
             $(location).attr("href", 'stationPage/' + text.replace('/','') + '.html');
           });
  });
}

$(document).ready(function () {
  // Calculate canvas size
  calculateCanvasSize();

  $('#map-container').svg({loadURL: 'metro.svg', onLoad: onSvgLoaded});
});
