
	
$(document).ready(function(){
  $("form input[type!=image][type!=button][type!=submit][type!=reset],form select").keypress(function(e){
    if ((e.which && e.which == 13) || (e.keyCode && e.keyCode == 13)) {
      return false;
    }else{
      return true;
    }
  });
});
