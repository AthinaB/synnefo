;(function(root){

    // root
    var root = root;
    
    // setup namepsaces
    var snf = root.synnefo = root.synnefo || {};
    var models = snf.models = snf.models || {}
    var storage = snf.storage = snf.storage || {};
    var ui = snf.ui = snf.ui || {};

    var views = snf.views = snf.views || {}

    // shortcuts
    var bb = root.Backbone;
    var util = snf.util;
    
    views.ApiInfoView = views.Overlay.extend({
        view_id: "api_info_view",
        
        content_selector: "#api-info-overlay",
        css_class: 'overlay-api-info overlay-info',
        overlay_id: "overlay-api-info",

        subtitle: "",
        title: "API Access",

        beforeOpen: function() {
            var cont = this.$(".copy-content p");
            var token = $.cookie("X-Auth-Token");

            cont.html("");
            cont.text(token);

            var clip = new snf.util.ClipHelper();
            cont.parent().append(clip.cont);
            clip.setText(token);
        },

        onClose: function() {
            var cont = this.$(".copy-content p");
            var token = $.cookie("X-Auth-Token");
            cont.html("");
        }
    });

    // TODO: implement me
    views.NoticeView = views.Overlay.extend({});

    views.MultipleActionsView = views.View.extend({
        view_id: "multiple_actions",

        _actions: {},
        el: '#multiple_actions_container',
        
        initialize: function() {
            this.actions = {};
            this.ns_config = {};

            views.MultipleActionsView.__super__.initialize.call(this);

            this.ns_tpl = this.$(".confirm_multiple_actions-template").clone()

            this.init_handlers();
            this.update_layout();
            
            // for heavy resize/scroll window events
            // do it `like a boss` 
            this.fix_position = _.throttle(this.fix_position, 100);
            this.update_layout = _.throttle(this.update_layout, 100);
            this.show_limit = 1;

            this.init_ns("vms", {
                msg_tpl:"Your actions will affect 1 machine",
                msg_tpl_plural:"Your actions will affect {0} machines",
                actions_msg: {confirm: "Confirm all", cancel: "Cancel all"},
                limit: 1,
                cancel_all: function() { snf.storage.vms.reset_pending_actions(); },
                do_all: function() { snf.storage.vms.do_all_pending_actions(); }
            });
            
            this.init_ns("nets", {
                msg_tpl:"Your actions will affect 1 private network",
                msg_tpl_plural:"Your actions will affect {0} private networks",
                actions_msg: {confirm: "Confirm all", cancel: "Cancel all"},
                limit: 1,
                cancel_all: function() { snf.storage.networks.reset_pending_actions(); },
                do_all: function() { snf.storage.networks.do_all_pending_actions(); }
            });

            this.init_ns("reboots", {
                msg_tpl:"1 machine needs to be rebooted for changes to apply.",
                msg_tpl_plural:"{0} machines needs to be rebooted for changes to apply.",
                actions_msg: {confirm: "Reboot all", cancel: "Cancel all"},
                limit: 0,
                cancel_all: function() { snf.storage.vms.reset_reboot_required(); },
                do_all: function() { snf.storage.vms.do_all_reboots(); }
            });
        },
        
        init_ns: function(ns, params) {
            this.actions[ns] = {};
            var nsconf = this.ns_config[ns] = params || {};
            nsconf.cont = $(this.$("#conirm_multiple_cont_template").clone());
            nsconf.cont.attr("id", "confirm_multiple_cont_" + ns);
            $(this.el).find(".ns-confirms-cont").append(nsconf.cont).addClass(ns);
            $(this.el).find(".ns-confirms-cont").append(nsconf.cont).addClass("confirm-ns");
            nsconf.cont.find(".msg button.yes").text(
                nsconf.actions_msg.confirm).click(_.bind(this.do_all, this, ns));
            nsconf.cont.find(".msg button.no").text(
                nsconf.actions_msg.cancel).click(_.bind(this.cancel_all, this, ns));
        },

        do_all: function(ns) {
            this.ns_config[ns].do_all();
        },

        cancel_all: function(ns) {
            this.ns_config[ns].cancel_all();
        },

        init_handlers: function() {
            var self = this;

            $(window).resize(_.bind(function(){
                this.fix_position();
            }, this));

            $(window).scroll(_.bind(function(){
                this.fix_position();
            }, this));

            storage.vms.bind("change:pending_action", _.bind(this.handle_action_add, this, "vms"));
            storage.vms.bind("change:reboot_required", _.bind(this.handle_action_add, this, "reboots"));
            storage.networks.bind("change:actions", _.bind(this.handle_action_add, this, "nets"));
        },

        handle_action_add: function(type, model, action) {
            var actions = this.actions[type];
            
            // TODO: remove type specific addition code in its own namespace
            if (type == "nets") {
                if (!action || action.is_empty()) {
                    delete actions[model.id];
                } else {
                    actions[model.id] = {model: model, actions: action.actions};
                }
            }

            if (type == "vms") {
                _.each(actions, function(action) {
                    if (action.model.id == model.id) {
                        delete actions[action]
                    }
                });

                var actobject = {};
                actobject[action] = [[]];
                actions[model.id] = {model: model, actions: actobject};
                if (typeof action == "undefined") {
                    delete actions[model.id]
                }
            }

            if (type == "reboots") {
                _.each(actions, function(action) {
                    if (action.model.id == model.id) {
                        delete actions[action]
                    }
                });
                var actobject = {};
                actobject['reboot'] = [[]];
                actions[model.id] = {model: model, actions: actobject};
                if (!action) {
                    delete actions[model.id]
                }
            }
            
            this.update_layout();
        },

        update_actions_content: function(ns) {
            var conf = this.ns_config[ns];
            conf.cont.find(".details").empty();
            conf.cont.find(".msg p").text("");
            
            var count = 0;
            var actionscount = 0;
            _.each(this.actions[ns], function(actions, model_id) {
                count++;
                _.each(actions.actions, function(params, act_name){
                    if (params && params.length) {
                        actionscount += params.length;
                    } else {
                        actionscount++;
                    }
                })
                this.total_confirm_actions++;
            });
            
            var limit = conf.limit;
            if (ui.main.current_view.view_id == "vm_list") {
                limit = 0;
            }

            if (actionscount > limit) {
                conf.cont.show();
                this.confirm_ns_open++;
            } else {
                conf.cont.hide();
            }
            
            var msg = count > 1 ? conf.msg_tpl_plural : conf.msg_tpl;
            conf.cont.find(".msg p").text(msg.format(count));

            return conf.cont;
        },

        fix_position: function() {
            $('.confirm_multiple').removeClass('fixed');
            if (($(this.el).offset().top +$(this.el).height())> ($(window).scrollTop() + $(window).height())) {
                $('.confirm_multiple').addClass('fixed');
            }
        },
        
        update_layout: function() {
            this.confirm_ns_open = 0;
            this.total_confirm_actions = 0;

            $(this.el).show();
            $(this.el).find("#conirm_multiple_cont_template").hide();
            $(this.el).find(".confirm-ns").show();
            
            _.each(this.ns_config, _.bind(function(params, key) {
                this.update_actions_content(key);
            }, this));

            if (this.confirm_ns_open > 0) {
                $(this.el).show();
                this.$(".confirm-all-cont").hide();
                this.$(".ns-confirms-cont").show();
            } else {
                $(this.el).hide();
                this.$(".confirm-all-cont").hide();
                this.$(".ns-confirms-cont").hide();
            }

            $(window).trigger("resize");
        }
    })
    
    // menu wrapper view
    views.SelectView = views.View.extend({
        
        initialize: function(view, router) {
            this.parent = view;
            this.router = router;
            this.pane_view_selector = $(".css-tabs");
            this.machine_view_selector = $("#view-select");
            this.el = $(".css-tabs");
            this.title = $(".tab-name");

            this.set_handlers();
            this.update_layout();

            views.SelectView.__super__.initialize.apply(this, arguments);
        },
        
        clear_active: function() {
            this.pane_view_selector.find("a").removeClass("active");
            this.machine_view_selector.find("a").removeClass("activelink");
        },
        
        // intercept menu links
        set_handlers: function() {
            var self = this;
            this.pane_view_selector.find("a").hover(function(){
                // FIXME: title from href ? omg
                self.title.text($(this).attr("href"));
            }, function(){
                self.title.text(self.parent.get_title());
            });

            this.pane_view_selector.find("a#machines_view_link").click(_.bind(function(ev){
                ev.preventDefault();
                this.router.vms_index();
            }, this))
            this.pane_view_selector.find("a#networks_view_link").click(_.bind(function(ev){
                ev.preventDefault();
                this.router.networks_view();
            }, this))
            this.pane_view_selector.find("a#disks_view_link").click(_.bind(function(ev){
                ev.preventDefault();
                this.router.disks_view();
            }, this))
            
            this.machine_view_selector.find("a#machines_view_icon_link").click(_.bind(function(ev){
                ev.preventDefault();
                var d = $.now();
                this.router.vms_icon_view();
            }, this))
            this.machine_view_selector.find("a#machines_view_list_link").click(_.bind(function(ev){
                ev.preventDefault();
                this.router.vms_list_view();
            }, this))
            this.machine_view_selector.find("a#machines_view_single_link").click(_.bind(function(ev){
                ev.preventDefault();
                this.router.vms_single_view();
            }, this))
        },

        update_layout: function() {
            this.clear_active();

            var pane_index = this.parent.pane_ids[this.parent.current_view_id];
            $(this.pane_view_selector.find("a")).removeClass("active");
            $(this.pane_view_selector.find("a").get(pane_index)).addClass("active");
            
            if (this.parent.current_view && this.parent.current_view.vms_view) {

                if (storage.vms.length > 0) {
                    this.machine_view_selector.show();
                    var machine_index = this.parent.views_ids[this.parent.current_view_id];
                    $(this.machine_view_selector.find("a").get(machine_index)).addClass("activelink");
                } else {
                    this.machine_view_selector.hide();
                }
            } else {
                this.machine_view_selector.hide();
            }

        }
    });

    views.MainView = views.View.extend({
        el: 'body',
        view_id: 'main',
        
        // FIXME: titles belong to SelectView
        views_titles: {
            'icon': 'machines', 'single': 'machines', 
            'list': 'machines', 'networks': 'networks',
            'disks': 'disks'
        },

        // indexes registry
        views_indexes: {0: 'icon', 2:'single', 1: 'list', 3:'networks'},
        views_pane_indexes: {0:'single', 1:'networks', 2:'disks'},

        // views classes registry
        views_classes: {'icon': views.IconView, 'single': views.SingleView, 
            'list': views.ListView, 'networks': views.NetworksView},

        // view ids
        views_ids: {'icon':0, 'single':2, 'list':1, 'networks':3},

        // on which pane id each view exists
        // machine views (icon,single,list) are all on first pane
        pane_ids: {'icon':0, 'single':0, 'list':0, 'networks':1, 'disks':2},
    
        initialize: function(show_view) {
            if (!show_view) { show_view = 'icon' };
            
            this.router = snf.router;
            this.empty_hidden = true;
            // fallback to browser error reporting (true for debug)
            this.skip_errors = true

            // reset views
            this.views = {};

            this.el = $("#app");
            // reset main view status
            this._loaded = false;
            this.status = "Initializing...";

            // initialize handlers
            this.init_handlers();

            // identify initial view from user cookies
            // this view will be visible after loading of
            // main view
            this.initial_view = this.session_view();

            views.MainView.__super__.initialize.call(this);

            $(window).focus(_.bind(this.handle_window_focus, this, "focus"));
            $(window).blur(_.bind(this.handle_window_focus, this, "out"));

            this.focused = true;
        },

        handle_window_focus: function(focus) {
            if (!snf.config.delay_on_blur) { return };

            if (focus === "focus") {
                this.focused = true;
                this.set_interval_timeouts(snf.config.update_interval);
            } else {
                this.focused = false;
                this.set_interval_timeouts(snf.config.blur_delay);
            }
        },

        set_interval_timeouts: function(time) {
            _.each([this._networks, this._vms], function(fetcher){
                if (!fetcher) { return };
                fetcher.timeout = time;
                fetcher.stop().start();
            })
        },
        
        vms_handlers_registered: false,

        // register event handlers
        // 
        // vms storage events to identify if vms list 
        // is empty and display empty view if user viewing
        // a machine view
        //
        // api/ui error event handlers
        init_handlers: function() {
            // vm handlers
            storage.vms.bind("remove", _.bind(this.check_empty, this));
            storage.vms.bind("add", _.bind(this.check_empty, this));
            storage.vms.bind("change:status", _.bind(this.check_empty, this));
            storage.vms.bind("reset", _.bind(this.check_empty, this));
            
            // api calls handlers
            synnefo.api.bind("error", _.bind(this.handle_api_error, this));
            synnefo.api.bind("change:error_state", _.bind(this.handle_api_error_state, this));
            synnefo.ui.bind("error", _.bind(this.handle_ui_error, this));
        },
        
        handle_api_error_state: function(state) {
            if (snf.api.error_state === snf.api.STATES.ERROR) {
                this.stop_intervals();
            } else {
                if (this.intervals_stopped) {
                    this.update_intervals();
                }
            }
        },
        
        handle_api_error: function(args) {
            if (arguments.length == 1) { arguments = _.toArray(arguments[0])};

            if (!_.last(arguments).display) {
                return;
            }

            this.error_state = true;
            
            var xhr = arguments[0];
            var args = util.parse_api_error.apply(util, arguments);
            
            // force logout if UNAUTHORIZED request arrives
            if (args.code == 401) { snf.ui.logout(); return };

            var error_entry = [args.ns, args.code, args.message, args.type, args.details, args];
            this.error_view.show_error.apply(this.error_view, error_entry);
        },

        handle_ui_error: function(data) {
            var msg = data.msg, code = data.code, err_obj = data.error;
            error = msg + "<br /><br />" + snf.util.stacktrace().replace("at", "<br /><br />at");
            params = { title: "UI error", extra_details: data.extra };
            params.allow_close = data.extra.allow_close === undefined ? true : data.extra.allow_close;
            this.error_view.show_error("UI", -1, msg, "JS Exception", error, params);
        },

        init_overlays: function() {
            this.create_vm_view = new views.CreateVMView();
            this.api_info_view = new views.ApiInfoView();
            //this.notice_view = new views.NoticeView();
        },
        
        show_loading_view: function() {
            $("#container #content").hide();
            $("#loading-view").show();
        },

        hide_loading_view: function() {
            $("#container #content").show();
            $("#loading-view").hide();
            $(".css-panes").show();
        },
        
        items_to_load: 4,
        completed_items: 0,
        check_status: function(loaded) {
            this.completed_items++;
            // images, flavors loaded
            if (this.completed_items == 2) {
                this.load_nets_and_vms();
            }

            if (this.completed_items == this.items_to_load) {
                this.update_status("Rendering layout...");
                var self = this;
                window.setTimeout(function(){
                    self.after_load();
                }, 10)
            }
        },

        load_nets_and_vms: function() {
            var self = this;
            this.update_status("Loading vms...");
            storage.vms.fetch({refresh:true, update:false, success: function(){
                self.update_status("VMS Loaded.");
                self.check_status();
            }});

            this.update_status("Loading networks...");
            storage.networks.fetch({refresh:true, update:false, success: function(){
                self.update_status("Networks loaded.");
                self.check_status();
            }});
        },  

        init_intervals: function() {
            this._networks = storage.networks.get_fetcher(snf.config.update_interval, 
                                                          snf.config.update_interval / 2, 
                                                          1, true, undefined);
            this._vms = storage.vms.get_fetcher(snf.config.update_interval, 
                                                snf.config.update_interval / 2, 
                                                1, true, undefined);
        },

        stop_intervals: function() {
            if (this._networks) { this._networks.stop(); }
            if (this._vms) { this._vms.stop(); }
            this.intervals_stopped = true;
        },

        update_intervals: function() {
            if (this._networks) {
                this._networks.stop();
                this._networks.start();
            } else {
                this.init_intervals();
            }

            if (this._vms) {
                this._vms.stop();
                this._vms.start();
            } else {
                this.init_intervals();
            }

            this.intervals_stopped = false;
        },

        after_load: function() {
            var self = this;
            this.update_status("Setting vms update interval...");
            this.init_intervals();
            this.update_intervals();
            this.update_status("Showing initial view...");
            
            // bypass update_hidden_views in initial view
            // rendering to force all views to get render
            // on their creation
            var uhv = snf.config.update_hidden_views;
            snf.config.update_hidden_views = true;
            this.initialize_views();
            snf.config.update_hidden_views = uhv;

            window.setTimeout(function() {
                self.update_status("Initializing overlays...");
                self.load_initialize_overlays();
            }, 20);
        },

        load_initialize_overlays: function() {
            this.init_overlays();
            // display initial view
            this.loaded = true;
            
            // application start point
            this.show_initial_view();

            this.check_empty();
        },

        load: function() {
            this.error_view = new views.ErrorView();
            this.feedback_view = new views.FeedbackView();
            this.invitations_view = new views.InvitationsView();
            var self = this;
            // initialize overlay views
            
            // display loading message
            this.show_loading_view();
            // sync load initial data
            this.update_status("Loading images...");
            storage.images.fetch({refresh:true, update:false, success: function(){
                self.check_status()
            }});
            this.update_status("Loading flavors...");
            storage.flavors.fetch({refresh:true, update:false, success:function(){
                self.check_status()
            }});
        },

        update_status: function(msg) {
            this.log.debug(msg)
            this.status = msg;
            $("#loading-view .info").removeClass("hidden")
            $("#loading-view .info").text(this.status);
        },

        initialize_views: function() {
            this.select_view = new views.SelectView(this, this.router);
            this.empty_view = new views.EmptyView();
            this.metadata_view = new views.MetadataView();
            this.multiple_actions_view = new views.MultipleActionsView();
            
            this.add_view("icon");
            this.add_view("list");
            this.add_view("single");
            this.add_view("networks");

            this.init_menu();
        },

        init_menu: function() {
            $(".usermenu .invitations").click(_.bind(function(){
                this.invitations_view.show();
            }, this));
            $(".usermenu .feedback").click(_.bind(function(){
                this.feedback_view.show();
            }, this));
        },
        
        // initial view based on user cookie
        show_initial_view: function() {
          this.set_vm_view_handlers();
          this.hide_loading_view();
          
          bb.history.start();

          this.trigger("initial");
        },

        show_vm_details: function(vm) {
            snf.ui.main.show_view("single")
            snf.ui.main.current_view.show_vm(vm);
        },

        set_vm_view_handlers: function() {
            var self = this;
            $("#createcontainer #create").click(function(e){
                e.preventDefault();
                self.router.vm_create_view();
            })
        },

        check_empty: function() {
            if (!this.loaded) { return }
            if (storage.vms.length == 0) {
                this.show_view("machines");
                this.router.show_welcome();
                this.empty_hidden = false;
            } else {
                this.hide_empty();
            }
        },

        show_empty: function() {
            if (!this.empty_hidden) { return };
            $("#machines-pane-top").addClass("empty");

            this.$(".panes").hide();
            this.$("#machines-pane").show();

            this.hide_views([]);
            this.empty_hidden = false;
            this.empty_view.show();
            this.select_view.update_layout();
            this.empty_hidden = false;
        },

        hide_empty: function() {
            if (this.empty_hidden) { return };
            $("#machines-pane-top").removeClass("empty");

            this.empty_view.hide(true);
            this.router.vms_index();
            this.empty_hidden = true;
            this.select_view.update_layout();
        },
        
        get_title: function(view_id) {
            var view_id = view_id || this.current_view_id;
            return this.views_titles[view_id];
        },

        // return class object for the given view or false if
        // the view is not registered
        get_class_for_view: function (view_id) {
            if (!this.views_classes[view_id]) {
                return false;
            }
            return this.views_classes[view_id];
        },

        view: function(view_id) {
            return this.views[view_id];
        },

        add_view: function(view_id) {
            if (!this.views[view_id]) {
                var cls = this.get_class_for_view(view_id);
                if (this.skip_errors) {
                    this.views[view_id] = new cls();
                    $(this.views[view_id]).bind("resize", _.bind(function() {
                        window.positionFooter();
                        this.multiple_actions_view.fix_position();
                    }, this));
                } else {
                    // catch ui errors
                    try {
                        this.views[view_id] = new cls();
                        $(this.views[view_id]).bind("resize", _.bind(function() {
                            window.positionFooter();
                            this.multiple_actions_view.fix_position();
                        }, this));
                    } catch (err) {snf.ui.trigger_error(-1, "Cannot add view", err)}
                }
            } else {
            }

            if (this.views[view_id].vms_view) {
                this.views[view_id].metadata_view = this.metadata_view;
            }
            return this.views[view_id];
        },
            
        hide_views: function(skip) {
            _.each(this.views, function(view) {
                if (skip.indexOf(view) === -1) {
                    $(view.el).hide();
                }
            }, this)
        },
        
        get: function(view_id) {
            return this.views[view_id];
        },
        
        session_view: function() {
            if (this.pane_view_from_session() > 0) {
                return this.views_pane_indexes[this.pane_view_from_session()];
            } else {
                return this.views_indexes[this.machine_view_from_session()];
            }
        },

        pane_view_from_session: function() {
            return $.cookie("pane_view") || 0;
        },

        machine_view_from_session: function() {
            return $.cookie("machine_view") || 0;
        },

        update_session: function() {
            $.cookie("pane_view", this.pane_ids[this.current_view_id]);
            if (this.current_view.vms_view) {
                $.cookie("machine_view", this.views_ids[this.current_view_id]);
            }
        },

        identify_view: function(view_id) {
            // machines view_id is an alias to
            // one of the 3 machines view
            // identify which one (if no cookie set defaults to icon)
            if (view_id == "machines") {
                var index = this.machine_view_from_session();
                view_id = this.views_indexes[index];
            }
            return view_id;
        },
        
        // switch to current view pane
        // if differs from the visible one
        show_view_pane: function() {
            if (this.current_view.pane != this.current_pane) {
                $(this.current_view.pane).show();
                $(this.current_pane).hide();
                this.current_pane = this.current_view.pane;
            }
        },
        
        show_view: function(view_id) {
            //var d = new Date;
            var ret = this._show_view(view_id);
            //console.log((new Date)-d)
            return ret;
        },

        _show_view: function(view_id) {
                // same view, visible
                // get out of here asap
                if (this.current_view && 
                    this.current_view.id == view_id && 
                    this.current_view.visible()) {
                    return;
                }
                
                // choose proper view_id
                view_id = this.identify_view(view_id);

                // add/create view and update current view
                var view = this.add_view(view_id);
                
                // set current view
                this.current_view = view;
                this.current_view_id = view_id;

                // hide all other views
                this.hide_views([this.current_view]);
                
                // FIXME: depricated
                $(".large-spinner").remove();

                storage.vms.reset_pending_actions();
                storage.networks.reset_pending_actions();
                storage.vms.stop_stats_update();

                // show current view
                this.show_view_pane();
                view.show();
                
                // update menus
                if (this.select_view) {
                    this.select_view.update_layout();
                }
                this.current_view.__update_layout();

                // update cookies
                this.update_session();
                
                // machines view subnav
                if (this.current_view.vms_view) {
                    $("#machines-pane").show();
                } else {
                    $("#machines-pane").hide();
                }
                
                // fix footer position
                // TODO: move footer handlers in
                // main view (from home.html)
                if (window.positionFooter) {
                    window.positionFooter();
                }

                // trigger view change event
                this.trigger("view:change", this.current_view.view_id);
                this.select_view.title.text(this.get_title());
                $(window).trigger("view:change");
                return view;
        },

        reset_vm_actions: function() {
        
        },
        
        // identify current view
        // based on views element visibility
        current_view_id: function() {
            var found = false;
            _.each(this.views, function(key, value) {
                if (value.visible()) {
                    found = value;
                }
            })
            return found;
        }

    });

    snf.ui.main = new views.MainView();
    
    snf.ui.logout = function() {
        $.cookie("X-Auth-Token", null);
        if (snf.config.logout_url !== undefined)
        {
            window.location = snf.config.logout_url;
        } else {
            window.location.reload();
        }
    }

    snf.ui.init = function() {
        if (snf.config.handle_window_exceptions) {
            window.onerror = function(msg, file, line) {
                snf.ui.trigger_error("CRITICAL", msg, {}, { file:file + ":" + line, allow_close: false });
            };
        }
        snf.ui.main.load();
    }

})(this);
