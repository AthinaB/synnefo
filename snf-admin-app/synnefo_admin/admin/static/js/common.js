snf = {
	modals: {
		performAction: function(modal, notificationArea, warningMsg, itemsCount, countAction) {
			var $modal = $(modal);
			var $notificationArea = $(notificationArea);
			var $actionBtn = $modal.find('.apply-action')
			var url = $actionBtn.attr('data-url');
			var actionName = $actionBtn.find('span').text();
			var logID = 'action-'+countAction;
			var data = {
				op: $actionBtn.attr('data-op'),
				target: $actionBtn.attr('data-target'),
				ids: $actionBtn.attr('data-ids')
			}
			var contactAction = (data.op === 'contact' ? true : false);

			if(contactAction) {
				data['sender'] = $modal.find('input[name="sender"]').val();
				data['subject'] = $modal.find('input[name="subject"]').val();
				data['text'] = $modal.find('textarea[name="text"]').val();
			}
			$.ajax({
				url: url,
				type: 'POST',
				data: JSON.stringify(data),
				contentType: 'application/json',
				timeout: 100000,
				beforeSend: function(jqXHR, settings) {
					var pendingMsg = _.template(snf.modals.html.notifyPending, ({logID: logID, actionName: actionName, removeBtn: snf.modals.html.removeLogLine, itemsCount: itemsCount}));
					if($notificationArea.find('.warning').length === 0) {
						$notificationArea.find('.container').append(pendingMsg);
						$notificationArea.find('.container').append(warningMsg);
					}
					else {
						$notificationArea.find('.warning').before(pendingMsg);
					}
					snf.modals.showBottomModal($notificationArea);
					$notificationArea.find('.warning').fadeIn('slow');
				},
				success: function(response, statusText, jqXHR) {
					var successMsg = _.template(snf.modals.html.notifySuccess, ({actionName: actionName, removeBtn: snf.modals.html.removeLogLine, itemsCount: itemsCount}));
                    $notificationArea.find('#'+logID).replaceWith(successMsg);
                    snf.modals.showBottomModal($notificationArea);
                },
                error: function(jqXHR, statusText) {
                    var htmlErrorSum =_.template(snf.modals.html.notifyErrorSum, ({actionName: actionName, removeBtn: snf.modals.html.removeLogLine, itemsCount: itemsCount}));
                    var htmlErrorReason, htmlErrorIDs, htmlError;
                    if(jqXHR.responseJSON === undefined) {
                        htmlErrorReason = _.template(snf.modals.html.notifyErrorReason, {description: jqXHR.statusText+' (code: '+jqXHR.status+').'});
                        htmlErrorIDs = '';
                    }
                    else {
                        htmlErrorReason = _.template(snf.modals.html.notifyErrorReason, {descrition: jqXHR.responseJSON.result});
                        htmlErrorIDs = _.template(snf.modals.html.notifyErrorIDs, {ids: jqXHR.responseJSON.error_ids.toString().replace(/\,/gi, ', ')});
                    }
                    var logs = htmlErrorSum + _.template(snf.modals.html.notifyErrorDetails, {list: htmlErrorReason+htmlErrorIDs});
                    htmlError = _.template(snf.modals.html.notifyError, {logInfo: logs});
                    $notificationArea.find('#'+logID).replaceWith(htmlError);
                    if($notificationArea.find('.warning').length === 0) {
                        $notificationArea.find('.container').append(warningMsg);
                    }

                    snf.modals.showBottomModal($notificationArea);
                }
		    });
	    },
		showBottomModal: function($modal) {
			var height = -$modal.outerHeight(true);
				$modal.css('bottom', height)
				$modal.animate({'bottom': '0px'}, 'slow');
		},
		hideBottomModal: function($modal) {
			var height = -$modal.outerHeight(true)
			$modal.animate({'bottom': height}, 'slow', function() {
				if($modal.find('.log').length === 0) {
					$modal.find('.warning').remove();
				}
			});
		},
		toggleBottomModal: function($modal) {
			if($modal.css('bottom') !== '0px') {
				snf.modals.showBottomModal($modal);
			}
			else {
				snf.modals.hideBottomModal($modal);
			}
		},
		showError: function(modal, errorSign) {
			var $modal = $(modal);
			var $errorMsg = $modal.find('*[data-error="'+errorSign+'"]');
			$errorMsg.show();
		},
		resetErrors: function (modal) {
			var $modal = $(modal);
			$modal.find('.error-sign').hide();
		},
		checkInput: function(modal, inputArea, errorSign) {
			var $inputArea = $(inputArea);
			var $errorSign = $(modal).find('*[data-error="'+errorSign+'"]');

			$inputArea.keyup(function() {
				if($.trim($inputArea.val())) {
					$errorSign.hide();
				}
			});
		},
		checkEmail: function(modal, inputArea, errorSign) {
			var $inputArea = $(inputArea);
			var $errorSign = $(modal).find('*[data-error="'+errorSign+'"]');

			$inputArea.keyup(function() {
				if(snf.modals.validateEmail($inputArea.val())) {
					$errorSign.hide();
				}
			});
		},
		validateEmail: function(email) {
			var reg = /^(([^<>()[\]\\.,;:\s@\"]+(\.[^<>()[\]\\.,;:\s@\"]+)*)|(\".+\"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
		    return reg.test(email);
		},
		validateContactForm: function(modal) {
			var $modal = $(modal);
			var $emailSubj = $modal.find('*[name="subject"]');
			var $emailBody = $modal.find('*[name="text"]');
			var $emailSender = $modal.find('*[name="sender"]');
			var noError = true;
			if(!$.trim($emailSubj.val())) {
				snf.modals.showError($modal, 'empty-subject');
				snf.modals.checkInput($modal, $emailSubj, 'empty-subject');
				noError = false;
			}
			if(!$.trim($emailBody.val())) {
				snf.modals.showError($modal, 'empty-body')
				snf.modals.checkInput($modal, $emailBody, 'empty-body');
				noError = false;
			}
			if(!$.trim($emailSender.val())) {
				snf.modals.showError($modal, 'empty-sender')
				snf.modals.checkInput($modal, $emailSender, 'empty-sender');
				noError = false;
			}
			if(!snf.modals.validateEmail($emailSender.val()) && $.trim($emailSender.val())) {
				snf.modals.showError($modal, 'invalid-email')
				snf.modals.checkEmail($modal, $emailSender, 'invalid-email');
				noError = false;
			}
			return noError;
		},
		resetInputs: function(modal) {
			var $modal = $(modal);
			$modal.find('input').each(function() {
				$(this).val(snf.modals[$(this).attr('name')]);
			});

			$modal.find('textarea').each(function() {
				$(this).val(snf.modals[$(this).attr('name')]);
			});
		},
		html: {
			singleItemInfo: '<dl class="dl-horizontal info-list"><dt>Name:</dt><dd><%= name %></dd><dt>ID:</dt><dd><%= id %></dd><dl>',
			removeLogLine: '<a href="" class="remove-icon remove-log" title="Remove this line">X</a>',
			notifyPending: '<p class="log" id="<%= logID %>"><span class="pending state-icon snf-font-admin snf-exclamation-sign"></span>Action <b>"<%= actionName %>"</b><% if (itemsCount==1) { %> for <%= itemsCount %> item <% } else if (itemsCount>0) { %> for <%= itemsCount %> items <% } %> is <b class="pending">pending</b>.<%= removeBtn %></p>',
			notifySuccess: '<p class="log"><span class="success state-icon snf-font-admin snf-ok"></span>Action <b>"<%= actionName %>"</b><% if (itemsCount==1) { %> for <%= itemsCount %> item <% } else if (itemsCount>0) { %> for <%= itemsCount %> items <% } %> <b class="succeed">succeeded</b>.<%= removeBtn %></p>',
			notifyError: '<div class="log"><%= logInfo %></div>',
			notifyErrorSum: '<p><span class="error state-icon snf-font-admin snf-remove"></span>Action <b>"<%= actionName %>"</b><% if (itemsCount==1) { %> for <%= itemsCount %> item <% } else if (itemsCount>0) { %> for <%= itemsCount %> items <% } %> <b class="error">failed</b>.<%= removeBtn %></p>',
			notifyErrorDetails: '<dl class="dl-horizontal"><%= list %></dl>',
			notifyErrorReason: '<dt>Reason:</dt><dd><%= description %></dd>',
			notifyErrorIDs: '<dt>IDs:</dt><dd><%= ids %></dd>',
			notifyRefreshPage: '<p class="warning">The data of the page maybe out of date. Refresh it, to update them.</p>',
			notifyReloadTable: '<p class="warning">The data of the table maybe out of date.<a class="snf-refresh-outline reload-table reload-btn" title="reload table"></a></p>',
			warningDuplicates: '<p class="warning-duplicate">Duplicate accounts have been detected</p>',
			commonRow:  '<tr data-itemid=<%= itemID %> <% if(hidden) { %> class="hidden-row" <% } %> ><td class="item-name"><%= itemName %></td><td class="item-id"><%= itemID %></td><td class="owner-name"><%= ownerName %></td><td class="owner-email"><div class="wrap"><a class="remove" title="Remove item from selection">X</a><%= ownerEmail %></div></td></tr>',
			contactRow: '<tr <% if(showAssociations) { %> title="related with: <%= associations %>" <% } %> data-itemid=<%= itemID %> <% if(hidden) { %> class="hidden-row" <% } %> ><td class="full-name"><%= fullName %></td><td class="email"><div class="wrap"><a class="remove" title="Remove item from selection">X</a><%= email %></div></td></tr>',
		}
	},
	tables: {
		html: {
			selectAllBtn: '<a href="" class="select select-all line-btn" data-karma="neutral" data-caution="warning" data-toggle="modal" data-target="#massive-actions-warning"><span>Select All</span></a>',
			selectPageBtn: '<a href="" id="select-page" class="select line-btn" data-karma="neutral" data-caution="none"><span>Select Page</span></a>',
			toggleSelected: '<a href="" class="toggle-selected extra-btn line-btn" data-karma="neutral"><span class="text">Show selected </span><span class="badge num selected-num">0</span></a>',
			reloadTable: '<a href="" class="line-btn reload-table" data-karma="neutral" data-caution="none" title="Reload table"><span class="snf-font-reload"></span></a>',
			clearSelected: '<a href="" id="clear-all" class="disabled deselect line-btn" data-karma="neutral" data-caution="warning" data-toggle="modal" data-target="#clear-all-warning"><span class="snf-font-remove"></span><span>Clear All</span></a>',
			toggleNotifications: '',
			showTips: '',
			trimedCell: '<span title="click to see"><span data-container="body" data-toggle="popover" data-placement="bottom" data-content="<%= data %>"><%= trimmedData %>...</span></span>',
			checkboxCell: '<span class="snf-font-admin snf-checkbox-<%= state %> selection-indicator"></span><%= content %>',
			summary: '<a title="Show summary" href="#" class="summary-expand expand-area"><span class="snf-font-admin snf-angle-down"></span></a><dl class="info-summary dl-horizontal"><%= list %></dl>',
			summaryLine: '<dt><%= key %></dt><dd><%= value %></dd>',
			detailsBtn: '<a title="Details" href="<%= url %>" class="details-link"><span class="snf-font-admin snf-search"></span></a>'
		}
	},
	timer: 0,
	ajaxdelay: 400
};


$(document).ready(function(){
	var $notificationArea = $('.notify');
	$notificationArea.css('bottom', -$notificationArea.outerHeight(true))
	$('.error-sign').click(function(e) {
		e.preventDefault();
	});

    
	$("[data-toggle=popover]").click(function(e) {
		e.preventDefault();
	});
	$("[data-toggle=popover]").popover();
	$("[data-toggle=tooltip]").tooltip();

	$('body').on('click', function (e) {
    //did not click a popover toggle or popover
    if ($(e.target).data('toggle') !== 'popover'
        && $(e.target).parents('.popover.in').length === 0) {
        $('[data-toggle="popover"]').popover('hide');
    }
});

	$('.modal').on('hidden.bs.modal', function () {
		$(this).find('.cancel').trigger('click');
	});

	$('#toggle-notifications').click(function(e) {
		e.preventDefault();
		snf.modals.toggleBottomModal($notificationArea);
	});

	$(document).keyup(function(e) {
		if (!($(e.target).closest("input")[0] || $(e.target).closest("textarea")[0])) {
			if(e.keyCode === 73) {
				$('#toggle-notifications').trigger('click');
			}
		}
	});


	$notificationArea.on('click', '.remove-log', function(e) {
		e.preventDefault();
		var $log = $(this).closest('.log');
		$log.fadeOut('slow', function() {
			$log.remove();
			if($notificationArea.find('.log').length === 0) {
				$notificationArea.find('.close-notifications').trigger('click');

			}
		});
	});

	$notificationArea.on('click', '.close-notifications', function(e) {
		e.preventDefault();
		snf.modals.hideBottomModal($notificationArea);
	});

	$('.modal[data-type="contact"]').find('input, textarea').each(function() {
		snf.modals[$(this).attr('name')] = $(this).val()
	});

    $('.disabled').click(function(e){
        e.preventDefault();
    });
});
