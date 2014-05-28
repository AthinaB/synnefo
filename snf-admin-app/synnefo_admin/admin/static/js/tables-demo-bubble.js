/* Demo: VMs table */

(function($, Django){

$(function(){
	console.log('init')
	/* Main Table */

	/* Currently not in use */
	/* Sort a colum with checkboxes */
	/* Create an array with the values of all the checkboxes in a column */
	$.fn.dataTableExt.afnSortData['dom-checkbox'] = function  (oSettings, iColumn) {
		return $.map( oSettings.oApi._fnGetTrNodes(oSettings), function (tr, i) {
			return $('td:eq('+iColumn+') input', tr).prop('checked') ? '0' : '1';
		} );
	};

	var url = $('#table-items-total').data("url");
	var serverside = Boolean($('#table-items-total').data("server-side"));
	var table;
	// var tableSelected;
	$.fn.dataTable.ext.legacy.ajax = true;
	var extraData;
	// sets the classes of the btns that are used for navigation throw the pages (next, prev, 1, 2, 3...)
	// $.fn.dataTableExt.oStdClasses.sPageButton = "btn btn-primary";

	var tableDomID = '#table-items-total';
	var tableSelectedDomID = '#table-items-selected'
	table = $(tableDomID+'[data-content="vm"]').DataTable({
		"bPaginate": true,
		//"sPaginationType": "bootstrap",
		"bProcessing": true,
		"serverSide": serverside,
		"ajax": {
			"url": url,
			"data": function(data) {
				// here must be placed the additional data that needs to be send with the ajax call
				// data.extraKey = "extraValue";
			},
			"dataSrc" : function(response) {
				console.log(response);
				mydata = response;
				extraData = response.extra;
				if(response.aaData.length != 0) {
					var cols = response.aaData;
					var rowL = cols.length;
				// 	var detailsCol = cols[0].length;
					var summaryCol = cols[0].length;
					for (var i=0; i<rowL; i++) {
				// 		cols[i][detailsCol] = response.extra[i].details_url;
						cols[i][summaryCol] = response.extra[i]
					}
				}
				return response.aaData;
			}
		},
		"columnDefs": [
		{
			targets: -1,
			"orderable": false,
			"render": function(data, type, rowData) {
				return summaryTemplate_1(data);
			},
		},
		{
			targets: 0,
			visible: false
		}
		],
		"order": [1, "asc"],
		"createdRow": function(row, data, dataIndex) {
			$(row).popover({
				selector: '[rel=popover]',
				placement: 'right',
				content: '<button class="" type="button">Detais</button><button class="expand-area"  type="button">Summary</button>',
				container: 'tr td:last',
				trigger: 'manual',
				html: true
			}).mouseenter(function() {
				$(this).popover('show')
			}).mouseleave(function() {
				console.log('leave nte')
				$(this).popover('hide')
			});

			// var extraIndex = data.length - 1;
			// row.id = data[extraIndex].id.value; //sets the dom id
			// var selectedL = selected.items.length;
			// if(selectedL !== 0) {
			// 	for(var i = 0; i<selectedL; i++){
			// 		if (selected.items[i].id === row.id) {
			// 			$(row).addClass('selected')
			// 		}
			// 	}
			// }

			clickSummary_1(row);
			// // clickDetails(row);
			// console.log($('.mypopover'))
			// $('.mypopover').popover();
			// $(row).find('.mypopover'). click(function(e) {
			// // 	// debugger;
			// 	e.preventDefault();
			// // 	// debugger;
			// 	e.stopPropagation();
			// // 	console.log('almost')
			// // 	console.log(this)
			// console.log($('.mypopover'))

			// });

		},
		"dom": '<"custom-buttons">frtilp',
		"language" : {
			"sLengthMenu": 'Pagination _MENU_'
		}
	});
	$("div.custom-buttons").html('<button class="select-all select">Select All</button>');
	// tableSelected = $(tableSelectedDomID).DataTable({
	// 	"columnDefs": [
	// 	{
	// 		targets: 0,
	// 		visible: false
	// 	}
	// 	],
	// 	"order": [1, "asc"],
	// 	"createdRow": function(row, data, dataIndex) {
	// 		// clickSummary(row);
	// 		// clickDetails(row);
	// 	},
	// 	"lengthMenu": [[5, 10, 25, 50, -1], [5, 10, 25, 50, "All"]],
	// 	"dom": 'frtilp',
	// 	"language" : {
	// 		"sLengthMenu": 'Pagination _MENU_'
	// 	}
	// });


	// function detailsTemplate(data) {
	// 	var html = '<a href="'+ data.value +'" class="details-link">'+ data.display_name+'</a>';
	// 	return html;
	// };

	function summaryTemplate_1(data) {
		var listTemplate = '<dt>{key}:</dt><dd>{value}</dd>';
		var list = '';
		var listItem = listTemplate.replace('{key}', prop).replace('{value}',data[prop]);
		var html;

		for(var prop in data) {
			if(prop !== "details_url") {
				if(data[prop].visible) {
					list += listTemplate.replace('{key}', data[prop].display_name).replace('{value}',data[prop].value);
				}
			}
		}

		html = '<dl class="info-summary dl-horizontal">'+ list +'</dl>';
		console.log('render telos');
		return html;
	};


	function clickSummary_1(row) {
			console.log('click summary 1!', $(row));
			// $(row).find('.expand-area').live('click', function() {
			// 	console.log('LIVE MAN')
			// });
			
		$(tableDomID).on('.expand-area', 'click', function() {
			// e.preventDefault();
			// e.stopPropagation();
		console.log('click summary 1')
		// 	var $summaryTd = $(this).closest('td');
		// 	// var $btn = $summaryTd.find('.expand-area span');
		// 	var $summaryContent = $summaryTd.find('.info-summary');
			
		// 	var summaryContentWidth = $summaryTd.closest('tr').width()// - parseInt($summaryContent.css('padding-right').replace("px", "")) - parseInt($summaryContent.css('padding-left').replace("px", ""));
		// 	var summaryContPos = summaryContentWidth - $summaryTd.width() - parseInt($summaryContent.css('padding-left').replace("px", "")) -2; // border width?

		// 	$summaryContent.css({
		// 		width: summaryContentWidth +'px',
		// 		right: summaryContPos +'px'
		// 	});
			// $btn.toggleClass('snf-angle-up snf-angle-down');
			// $summaryContent.stop().slideToggle(600, function() {
			// 	if ($summaryContent.is(':visible')) {
			// 		$btn.removeClass('snf-angle-down').addClass('snf-angle-up');    
			// 	}
			// 	else {
			// 		$btn.removeClass('snf-angle-up').addClass('snf-angle-down');
			// 	}
			// });

		});
	};

	$(tableDomID).on('.expand-area', 'click', function() {
			// e.preventDefault();
			// e.stopPropagation();
		console.log('click summary 1')
	});

	$('.popover-test').popover({ // prepei o selector na einai to simeio p to kanei trigger gia emfanistei (to koumbi i tr)
		placement: 'right',
		content: '<a>hi</a>',
		container: '.popover-test',
		trigger: 'manual',
		html: true,
		offset: 30
	}).mouseenter(function() {
		$(this).popover('show')
	}).mouseleave(function() {
		console.log('leave nte')
		$(this).popover('hide')
	});
});
}(window.jQuery, window.Django));