/*
* Various functions that will be used throughout all templates
* are inside ui Object
*/

ui = {};

/* when closeEl el is clicked, its parent with class divToCloseClass slidesUp */
ui.closeDiv = function(closeEl, divToCloseClass) {
    closeEl.click(function(e){
        e.preventDefault();
        $(this).parents(divToCloseClass).slideUp('slow');
    });
}


ui.trimChars = function( str, chars) {
    if ( str.length>chars){
        return $.trim(str).substring(0, chars)+ "...";
    } else {
        return str;
    }
}

/* sets lt-sidebar height. Useful for jscrollpane scrollbar */
ui.setSidebarHeight = function(){
    var WindowHeight = $(window).height();
    var h1= WindowHeight - $('.header').outerHeight();
    var h2= $('.main').outerHeight();
    $('.lt-sidebar').height((h2>h1) ? h2 : h1);
}


/* 
* Logic for Entities actions. Present in items_list pages
* Available categories are :
*  - both/single ( for multiple entities/single entities)
*  - running/stopped ( for running/stopped entities)
*  - permanent ( for entities always active )
*/
ui.entitiesActionsEnabled = function(){
    var all = $('.snf-checkbox-checked').length;
    var running = $('.snf-checkbox-checked').parents('.container').find('.running').length;
    var stopped = $('.snf-checkbox-checked').parents('.container').find('.stopped').length;
    $('.header .main-actions li:not(.permanent) a').removeClass('active');  
    if ( (running*stopped) > 0 ){          
         $('.main-actions li.both a').addClass('active');
         $('.main-actions li.single a').removeClass('active');
    } else {
        if (running > 0) {
            $('.main-actions li.both a').addClass('active');
            $('.main-actions li.running a').addClass('active');
        } else if (stopped>0) {
            $('.main-actions li.both a').addClass('active');
            $('.main-actions li.stopped a').addClass('active');
        }
        if ( all > 1 ) {
            $('.main-actions li.single a').removeClass('active');
        }
    }
}

ui.entitiesActionsInit = function(){

    $('.entities li .container').mouseleave(
        function(e){
            $(this).find('.snf-checkbox-unchecked').parents('.check').removeClass('active');
         }
    );

    $('.entities .container .check').click(function(e){
        e.preventDefault();
        var checkbox = $(this).find('.snf-checkbox-unchecked, .snf-checkbox-checked');
        checkbox.toggleClass('snf-checkbox-unchecked');
        checkbox.toggleClass('snf-checkbox-checked');
        
        if(checkbox.hasClass('snf-checkbox-checked')){
            $(this).parents('.container').addClass('set-bg');
            $(this).addClass('active');
        }
        else{
            $(this).parents('.container').removeClass('set-bg');
        }
        ui.entitiesActionsEnabled();
    })
   
}

/*
* In order for the editable value functionality to work, the html markup
* should be:
    <div class="editable">
        <span class="input-txt">editable value</span>
        <input type="text">
        <a href="#" class="edit">edit</a>
        <a href="#" class="save">save</a>
        <a href="#" class="cancel">cancel</a>
    </div>
*/
ui.editable = function(){

/*
* resetForm hides save and cancel buttons,
* text input and shows input-txt. resetForm does not alter
* input-txt content.
*/

    function resetForm(e, elem) {
        var el = elem.parents('.editable');
        el.find('input[type="text"]').hide();
        el.find('a.cancel, a.save').hide();
        el.find('a.edit, .input-txt').show();
    }

/* 
* showForm hides input-txt, shows save and cancel buttons and
* sets input value to input-txt content.
*/
    function showForm(e,elem) {
        e.stopPropagation(); 
        e.preventDefault();
        var el = elem.parents('.editable'); 
        el.find('input[type="text"]').val(el.find('.input-txt').html());
        el.find('input[type="text"]').show();
        el.find('a.cancel, a.save').show();
        elem.hide();
        el.find('.input-txt').hide();

    }

/*
setValue sets input-txt value to the input value.
Makes sure that the input value is not empty.
TODO:
Ajax request to submit form
*/

    function setValue(elem) {
        var el = elem.parents('.editable');
        if( el.find('input[type="text"]').val() ) {
            el.find('.input-txt').html(el.find('input[type="text"]').val());
        }
    }


    $('.editable .edit').click(function(e){
        showForm(e, $(this));
    })

    $('.editable .cancel').click(function(e){
        e.stopPropagation();
        e.preventDefault();
        resetForm(e, $(this));
    })

    $('.editable .save').click(function(e){
        e.stopPropagation();
        e.preventDefault();
        setValue($(this));
        resetForm(e, $(this));

    })


    $('.editable input[type="text"]').click(function(e){
        e.stopPropagation();
    })

    $('.editable input[type="text"]').keyup(function(e){
        if(e.keyCode == 13) { 
            setValue($(this));
            resetForm(e, $(this));
            
        }
    
    })

    $('html').click(function(e) {
        resetForm(e, $('.editable a.cancel'));
    });

}

/* TODO: better overlay functionality */
ui.overlay = function() {
    $('[data-overlay-id]').click(function(e){
        e.preventDefault();
        var el = $(this);
        // main-actions a need to be active to trigger overlay
        if ( (el.parents('.main-actions').find('li a.active').length == 0) && (el.parents('.main-actions').length > 0) ) {
            return false;
        }
        var id = el.data('overlay-id');
        $('.overlay-area').show();
        $(id).slideDown('slow');
    });


}

//permits only one checkbox to be checked in a ul
ui.checkAction = function(checkbox) {
        var otherChecked = checkbox.closest('li').siblings('li').find('span.snf-checkbox-checked').length;
        if(otherChecked!=0){
            checkbox.toggleClass('snf-checkbox-checked');
            checkbox.toggleClass('snf-checkbox-unchecked');
        }
        
}


// when user moves a vm or network icon (list view)
ui.placementByUser = function() {
    if($('.sortable').length != 0) {
        $( ".sortable" ).sortable({
            items: "> li:not(:last)",
            stop: function(event, ui) {
                $.map($(this).find('li'), function(el) {
                            return $(el).attr('data-order', $(el).index());
                        });
            }
        });

        $( ".sortable" ).disableSelection(); //i think unnecessary
    }
}

//create vm
ui.pickFlavor = function(flavorSelection) {
        ui.select_flavor = 1;
        console.log(flavorSelection);
        var classes = $(flavorSelection).attr('class').split(" ");
        // the second class is: 'small_flavor' or 'medium_flavor' or 'large_flavor'
        
        $(flavorSelection).parent('li').siblings('li').find('a.chosen_flavor').removeClass('chosen_flavor');
        $(flavorSelection).addClass('chosen_flavor');
        $('.select-flavor').find('dl.cpus span.current, dl.ram span.current, dl.disk span.current').removeClass('current');
        $('.select-flavor').find('.'+classes[1]).addClass('current');

}


ui.pickResources = function(resource) {
        $(resource).parents('dl').find('span').removeClass('current');
        $(resource).addClass('current');
        if(ui.select_flavor == 1){
            if(!$(resource).parents('dl').hasClass('storage')){
            $('.lt-sidebar').find('a.chosen_flavor').removeClass('chosen_flavor');
            select_flavor = 0;
            }
        }
    }


ui.netOptions = function(option) {
    var checkbox = $(option).find('.snf-checkbox-checked, .snf-checkbox-unchecked');
    var list = $(option).closest('ul');
    
    ui.checkAction(checkbox); //allazw to checkbox p pataw
    if(list.hasClass('subnet_options')){
        checkedBefore = $(option).closest('li').siblings('li').find('span.snf-checkbox-checked');
        if($(checkedBefore).closest('li').find('a').hasClass('manual'))
        {
            $(checkedBefore).closest('li').find('.manual_sub').hide();
        }
        ui.checkAction(checkedBefore); //allazw ta alla checkboxes
        
        if($(option).hasClass('manual')) {

            if($(checkbox).hasClass('snf-checkbox-unchecked')) {
                $(option).closest('span').find('.manual_sub').hide();
            }
            else {
                $(option).closest('span').find('.manual_sub').show();
            }
        }
    }
    else if($(option).closest('li').hasClass('dhcp_option')) {
        if($(checkbox).hasClass('snf-checkbox-unchecked')) {
            $('.network_options').find('.subnet_options').hide();
        }
        else {
            $('.network_options').find('.subnet_options').show();
        }
    }
}
    

$(document).ready(function(){

    ui.setSidebarHeight();
    ui.closeDiv($('.info .close'), '.info');
    ui.entitiesActionsInit();
    ui.editable();
    ui.overlay();


    $('.select-os li').click(function(e){
        $('.select-os li').removeClass('selected');
        $(this).addClass('selected');
    })

    
    if ($('.overlay').length >0 ){
        $('body').addClass('with-overlay');
    }

    $('.new-btn a.current').click(function(e){
        e.preventDefault();
    })

    $('.main-actions li a').click(function(e){
        if (!($(this).hasClass('active'))) {
            e.preventDefault();
        }
    })
    $('.scroll-pane').jScrollPane();

    $('.main .items-list .title em').each(function(){
        $(this).html( ui.trimChars($(this).html(), 20) );

    })

    $('.main-actions li a').click(function(e){
        if (!($(this).hasClass('active'))) {
            e.preventDefault();
        }
    })
    $('.overlay-area .close').click(function(e){
        e.preventDefault();
        $(this).parents('.overlay-area').hide();
        $(this).parents('.overlay-area').find($('[data-overlay-id]')).hide();
    })

    $('.browse-files').click(function(e){
        e.preventDefault();
    })

    Dropzone.options.filesDropzone = {
        dictDefaultMessage:'',
        clickable: '.browse-files',
        previewsContainer: '.dropzone-files',
        createImageThumbnails: false,
        dictRemoveFile: "snf-Remove file",
    };


    $('.main .files').magnificPopup({
        delegate: 'a.show.image',
        type: 'image',
        tLoading: 'Loading image #%curr%...',
        mainClass: 'mfp-img-mobile',
        gallery: {
            enabled: true,
            navigateByImgClick: true,
            preload: [0,1] // Will preload 0 - before current, and 1 after the current image
        },
        image: {
            tError: '<a href="%url%">The image #%curr%</a> could not be loaded.',
            titleSrc: function(item) {
                return item.el.data('title');
            }
        }
    });


    // create vm
    // choose resources one by one
    ui.select_flavor =0;
    $('.select-flavor dl span').click(function(e){
        e.preventDefault();
        ui.pickResources(this);
        
        
    });

    // create vm
    // if a predefined flavor has been selected from the user, it highlights the proper resources 
    $('.lt-sidebar li a.flavor_selection').click(function(e){
        e.preventDefault();
        ui.pickFlavor(this);        
    });

    // create network
    // checkbox: basic reaction on click (checked, unchecked)
    $('.network_options .check').click(function(e){
        e.preventDefault();
        ui.netOptions(this);
    })
  
    ui.placementByUser();
   

})


$(window).resize(function(e){
    ui.setSidebarHeight();
    $('.scroll-pane').jScrollPane();
})