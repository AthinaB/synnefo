/* Demo: Users table */

(function($, Django){

$(function(){
	console.log('init')
	/* Main Table */



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
	table = $(tableDomID+'[data-content="user"]').DataTable({
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
					var detailsCol = 1; // column 1
					var summaryCol = cols[0].length;
					for (var i=0; i<rowL; i++) {
						cols[i][detailsCol] = {
							display_name: cols[i][detailsCol],
							details_url: response.extra[i].details_url.value
						};
						cols[i][summaryCol] = response.extra[i]
					}
				}
				return response.aaData;
			}
		},
		"columnDefs": [
		{
			targets: 1,
			render: function(data, type, rowData) {
				return '<a href="'+data.details_url+'">'+data.display_name+'</a>'; // todo function detailsTemplate(data)
			}
		},
		{
			targets: -1,
			"orderable": false,
			"render": function(data, type, rowData) {
				return summaryTemplate_original(data);
			},
		},
		{
			targets: 0,
			visible: false
		}
		],
		"order": [1, "asc"],
		"createdRow": function(row, data, dataIndex) {
			var extraIndex = data.length - 1;
			row.id = data[extraIndex].id.value; //sets the dom id
			// var selectedL = selected.items.length;
			// if(selectedL !== 0) {
			// 	for(var i = 0; i<selectedL; i++){
			// 		if (selected.items[i].id === row.id) {
			// 			$(row).addClass('selected')
			// 		}
			// 	}
			// }

			clickSummary_original(row);
			clickDetails_2(row);
		},
		"dom": '<"custom-buttons">frtilp',
		"language" : {
			"sLengthMenu": 'Pagination _MENU_'
		}
	});
	$("div.custom-buttons").html('<button class="select-all select">Select All</button>');
	
	

	function summaryTemplate_original(data) {
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

		html = '<a href="#" class="summary-expand expand-area"><span class="snf-icon snf-angle-down"></span></a><dl class="info-summary dl-horizontal">'+ list +'</dl>';
		return html;
	};


	function clickSummary_original(row) {
		$(row).find('a.expand-area').click(function(e) {
			e.preventDefault();
			e.stopPropagation();
			var $summaryTd = $(this).closest('td');
			var $btn = $summaryTd.find('.expand-area span');
			var $summaryContent = $summaryTd.find('.info-summary');
			
			var summaryContentWidth = $summaryTd.closest('tr').width()// - parseInt($summaryContent.css('padding-right').replace("px", "")) - parseInt($summaryContent.css('padding-left').replace("px", ""));
			var summaryContPos = summaryContentWidth - $summaryTd.width() - parseInt($summaryContent.css('padding-left').replace("px", "")) -2; // border width?

			$summaryContent.css({
				width: summaryContentWidth +'px',
				right: summaryContPos +'px'
			});
			$btn.toggleClass('snf-angle-up snf-angle-down');
			$summaryContent.stop().slideToggle(600, function() {
				if ($summaryContent.is(':visible')) {
					$btn.removeClass('snf-angle-down').addClass('snf-angle-up');    
				}
				else {
					$btn.removeClass('snf-angle-up').addClass('snf-angle-down');
				}
			});
		});
	};

	function clickDetails_2(row) {
		$(row).find('a').click(function(e) {
			e.stopPropagation();
		})
	}

});
}(window.jQuery, window.Django));