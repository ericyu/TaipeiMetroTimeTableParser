$(document).ready(function () {
  $('#timetable tr').hover(
    function() {
      var idx = $(this).index();
      $('#stations tr').eq(idx).addClass('hoverRow');
    }, function() {
      var idx = $(this).index();
      $('#stations tr').eq(idx).removeClass('hoverRow');
    }
  );

  $('#stations tr').hover(
    function() {
      var idx = $(this).index();
      $('#timetable tr').eq(idx).addClass('hoverRow');
    }, function() {
      var idx = $(this).index();
      $('#timetable tr').eq(idx).removeClass('hoverRow');
    }
  );
});
