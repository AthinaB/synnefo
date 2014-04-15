$(document).ready(function(){ $("input").focus(); })

$(document).ready(function(){

 // table sorting

 $('.table-sorted:not(.table-users)').tablesorter({
    sortList : [[2,0]],
});



 // fix sub nav on scroll
  var $win = $(window)
    , $nav = $('.subnav:not(.nav-main)')
    , navTop = $('.subnav:not(.nav-main)').length && $('.subnav:not(.nav-main)').offset().top
    , isFixed = 0,
      navMainTop = $('.nav-main').outerHeight();

  function processScroll() {
    var i, scrollTop = $win.scrollTop();
    var navTemp = navTop - navMainTop*2;
    if (scrollTop >= (navTop - navMainTop*2) && !isFixed) {
      console.log('1 scrollTop: '+scrollTop+' navTop: '+navTemp);
      isFixed = 1;
      $nav.addClass('subnav-fixed');
    } else if (scrollTop <= (navTop -navMainTop*2) && isFixed) {
      console.log('2 scrollTop: '+scrollTop+' navTop: '+navTemp);
      isFixed = 0;
      $nav.removeClass('subnav-fixed');
    }
  }

  processScroll();

  // hack sad times - holdover until rewrite for 2.1
  $nav.on('click', function () {
    if (!isFixed) setTimeout(function () {  $win.scrollTop($win.scrollTop()) }, 10)
  })

  $win.on('scroll', processScroll)
	
	  
  
  // hide/show expand/collapse 
  
  $('.subnav .dropdown-menu a').click(function(){
  	$('.info-block-content, .show-hide-all').show();
  })
  
  	
  
  var txt_all = ['+ Expand all','- Collapse all'];
  

  $('.show-hide-all span').html(txt_all[0]); 	 
  
  
  $('.show-hide-all').click(function(){
  	var badgeAll = $(this).children('span');	
  	badgeAll.toggleClass('open');
  	var tabs = $(this).parent('.info-block').find('.object-details-content') 
  	
  	console.info(tabs);
  	if (badgeAll.hasClass('open')){
  		badgeAll.html( txt_all[1]);
  		tabs.each(function() {
	  		$(this).show();
	  		$(this).siblings('h4').addClass('expanded');
	    });
  		
  		
  	} else {
  		badgeAll.html( txt_all[0]);
  		tabs.each(function() {
	  		$(this).hide();
	  		$(this).siblings('h4').removeClass('expanded');
 
	    });
  	}
	
  	 
  });   

 
  
  $('.object-details h4').click(function(){	
  	
  	$(this).siblings('.object-details-content').toggle();
  	$(this).toggleClass('expanded');
  	 
  }); 
  
  
  $('.info-block h3').click(function(){
  	$(this).next('.info-block-content').toggle();
  	$(this).prev('.show-hide-all').toggle();
  });  
  
  $('.search-query').typeahead({
    source: function(typeahead, query) {
      if (query.indexOf("@") > -1) {
        $.ajax({
          url:'/admin/api/users/?prefix='+query, 
          dataType:'json', 
          success: function(d){
            return typeahead.process(d);
          }
      })
      } else {
      }
    }
  })
})

