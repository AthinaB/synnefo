// Copyright 2014 GRNET S.A. All rights reserved.
// 
// Redistribution and use in source and binary forms, with or
// without modification, are permitted provided that the following
// conditions are met:
// 
//   1. Redistributions of source code must retain the above
//      copyright notice, this list of conditions and the following
//      disclaimer.
// 
//   2. Redistributions in binary form must reproduce the above
//      copyright notice, this list of conditions and the following
//      disclaimer in the documentation and/or other materials
//      provided with the distribution.
// 
// THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
// OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
// WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
// PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
// CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
// SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
// LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
// USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
// AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
// LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
// ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
// POSSIBILITY OF SUCH DAMAGE.
// 
// The views and conclusions contained in the software and
// documentation are those of the authors and should not be
// interpreted as representing official policies, either expressed
// or implied, of GRNET S.A.
// 

;(function(root){
    
    // root
    var root = root;
    
    // setup namepsaces
    var snf = root.synnefo = root.synnefo || {};
    var models = snf.models = snf.models || {}
    var storage = snf.storage = snf.storage || {};
    var ui = snf.ui = snf.ui || {};
    var util = snf.util || {};
    var views = snf.views = snf.views || {}

    // shortcuts
    var bb = root.Backbone;
    
    // logging
    var logger = new snf.logging.logger("SNF-VIEWS");
    var debug = _.bind(logger.debug, logger);

    // Extended views module
    // View objects to provide more sophisticated base objects for views 
    // that are bind to existing storage model/collection objects.
    views.ext = {};
    
    views.ext.View = views.View.extend({
      rivets_view: false,
      rivets: undefined,
      container: undefined,
      classes:'',

      storage_handlers: {},

      init: function() {},
      post_init: function() {},

      initialize: function(options) {
        views.ext.View.__super__.initialize.apply(this, arguments);
        this.container = options && options.container;
        this._subviews = [];
        if (this.tpl) {
          var tpl = $(this.tpl);
          if (tpl.hasClass("inner-tpl")) { tpl = tpl.children().get(0); }
          this.el = $(tpl).clone().removeClass("hidden").removeAttr('id');
        }
        this.init.apply(this, arguments);
        this.post_init.apply(this, arguments);
        this.append_to_container();
        $(this.el).addClass(this.classes);
        _.bindAll(this);
      },
      
      append_to_container: function() {
        if (!this.container) { return }
        var cont = $(this.container);
        cont.append(this.el);
      },
      
      create_view: function(view_cls, options) {
        var options = _.extend({}, options);
        options.parent_view = this;
        var view = new view_cls(options);
        if (view.css_classes) {
          view.el.addClass(view.css_classes)
        }
        return view;
      },

      add_subview: function(view) {
        view.parent_view = this;
        this._subviews.push(view);
      },

      remove_view: function(view) {
        this._subviews = _.without(this._subviews, view);
      },
      
      hide_subviews: function() {
        _.each(this._subviews, function(view) { 
          view.hide(true); 
        });
      },

      show_subviews: function() {
        _.each(this._subviews, function(view) { 
          view.show(true); 
        });
      },
      
      pre_hide: function() {
        this.rivets_unbind();
        this.remove_handlers();
      },
      
      get_extra_rivet_models: function() {},

      get_rivet_object: function() {
        return this.rivet_object;
      },

      post_hide: function() {
        this.hide_subviews();
        this.trigger("hide");
      },
      
      rivets_init: function() {
        if (!this.rivets_view) { return }
        var rivet_object = this.get_rivet_object();
        rivet_object['view'] = this;
        if (this.el != $("body").get(0)) {
          this.rivets = rivets.bind(this.el, rivet_object);
        } else {
        }
      },
      
      rivets_update: function() {
        if (!this.rivets_view) { return }
        this.rivets.update();
      },

      rivets_bind: function() {
        if (!this.rivets_view) { return }
        if (!this.rivets) { this.rivets_init(); return }
        var rivet_object = this.get_rivet_object();
        rivet_object['view'] = this;
        this.rivets.models = rivet_object;
        //this.rivets.build();
        this.rivets.bind();
      },

      rivets_unbind: function() {
        if (!this.rivets_view) { return }
        if (!this.rivets) { return }
        this.rivets.unbind();
      },

      pre_show: function() {
        this.set_handlers();
        this.rivets_bind();
        this.show_subviews();
      },
      
      resolve_storage_object: function(id) {
        var result;
        if (this['resolve_' + id + '_storage_object']) {
          return this['resolve_' + id + '_storage_object']();
        }
        result = synnefo.storage[id];
        return result ? result : this.collection
      },
      
      each_storage_handler: function(cb, context) {
        if (!context) { context = this }
        _.each(this.storage_handlers, function(handlers, object_name) {
          _.each(handlers, function(events, handler_name) {
            _.each(events, function(event) {
              object = this.resolve_storage_object(object_name);
              handler = this['handle_' + handler_name];
              if (!handler) {
                throw "Handler " + handler_name + " does not exist";
              }
              if (!object) {
                throw "Storage object " + object_name + " does not exist";
              }
              cb.call(context, object, event, handler);
            }, this);
          }, this);
        }, this);
      },
      
      get_handler: function(id) {
      },

      set_handlers: function() {
        this.each_storage_handler(this.set_handler, this);
      },

      remove_handlers: function() {
        this.each_storage_handler(this.remove_handler, this);
      },
      
      set_handler: function(object, event, handler) {
        object.bind(event, handler);
      },

      remove_handler: function(object, event, handler) {
        object.unbind(event, handler);
      }
    });

    views.ext.PaneView = views.ext.View.extend({
      collection_view_cls: null,
      collection_view_selector: '.collection',
      init: function() {
        var options = {};
        options['el'] = $(this.$(this.collection_view_selector).get(0));
        this.collection_view = this.create_view(this.collection_view_cls, options);
        this.add_subview(this.collection_view);
      },
    });

    views.ext.CollectionView = views.ext.View.extend({
      collection: undefined,
      model_view_cls: undefined,
      animation_speed: 200,
      quota_key: undefined,
      quota_limit_message: undefined,
      list_el_selector: '.items-list',
      init: function() {
        var handlers = {};
        handlers[this.collection_name] = {
          'collection_change': ['update', 'sort'],
          'collection_reset': ['reset'],
          'model_change': ['change'],
          'model_add': ['add'],
          'model_remove': ['remove']
        }
        this.storage_handlers = _.extend(handlers, this.storage_handlers)
        this._model_views = {};
        this.list_el = $(this.$(".items-list").get(0));
        this.empty_el = $(this.$(".empty-list").get(0));
        if (this._id) { debugger }
        if (this.create_view_cls) {
          this._create_view = new this.create_view_cls();
          this._create_view.parent_view = this;
        }

        this.create_button = this.$(".create-button a");
        this.create_button.click(_.bind(function(e) {
          e.preventDefault();
          if (this.$(".create-button a").hasClass("disabled")) {
            return;
          }
          this.handle_create_click();
        }, this));
        
        if (this.quota_key) {
          synnefo.storage.quotas.bind("change", 
                                      _.bind(this.update_quota, this));
          this.update_quota();
        }
      },
      
      update_quota: function() {
        var can_create = synnefo.storage.quotas.can_create(this.quota_key);
        if (can_create) {
          this.create_button.removeClass("disabled");
          this.create_button.attr("title", "");
        } else {
          this.create_button.addClass("disabled");
          this.create_button.attr("title", 
                                  this.quota_limit_message || "Quota limit reached")
        }
      },
      
      handle_create_click: function() {
        if (this.create_button.hasClass("disabled")) { return }

        if (this._create_view) {
          this._create_view.show();
        }
      },
      
      post_hide: function() {
        this.each_model_view(function(model, view) {
          this.unbind_custom_view_handlers(view, model);
        }, this);
        views.ext.CollectionView.__super__.pre_hide.apply(this, arguments);
      },

      pre_show: function() {
        this.each_model_view(function(model, view) {
          this.bind_custom_view_handlers(view, model);
        }, this);
        views.ext.CollectionView.__super__.pre_show.apply(this, arguments);
        this.update_models();
      },
      
      handle_collection_reset: function() {
        this.update_models();
      },

      handle_model_change: function(model) {
        var el, index, model, parent, view, anim;
        view = this._model_views[model.id];
        if (!view) { return }
        el = view.el;
        parent = this.parent_for_model(model);
        index = this.collection.indexOf(model);
        if (!parent.find(el).length) {
          anim = true;
          this.place_in_parent(parent, el, model, index, anim);
        }
        if (index != view.el.data('index')) {
          this.place_in_parent(parent, el, model, index, false);
        }
      },

      handle_collection_change: function() {
        this.update_models();
      },

      handle_model_add: function(model, collection, options) {
        this.add_model(model);
        $(window).trigger("resize");
      },

      handle_model_remove: function(model, collection, options) {
        this.remove_model(model);
      },
      
      show_empty: function() {
        this.empty_el.show();
      },

      hide_empty: function() {
        this.empty_el.hide();
      },

      check_empty: function() {
        if (this.collection.length == 0) {
          this.show_empty();
          this.list_el.hide();
        } else {
          this.list_el.show();
          this.hide_empty();
        }
      },
      
      parent_for_model: function(model) {
        return this.list_el;
      },
      
      place_in_parent: function(parent, el, m, index, anim) {
        var place_func, place_func_context, position_found, exists;

        _.each(parent.find(">.model-item"), function(el) {
          var el = $(el);
          var el_index = el.data('index');
          if (!el_index || position_found) { return };
          if (parseInt(el_index) < index) {
            place_func = el.before;
            place_func_context = el;
            position_found = true;
          }
        });
        
        if (!position_found) {
          place_func = parent.append;
          place_func_context = parent;
        }

        if (anim) {
          var self = this;
          el.fadeOut(this.animation_speed, function() {
            place_func.call(place_func_context, el);
            el.fadeIn(self.animation_speed);
          });
        } else {
          place_func.call(place_func_context, el);
        }
        el.attr("data-index", index);
      },
      
      get_model_view_cls: function(m) {
        return this.model_view_cls
      },
      
      model_view_options: function(m) { return {} },

      add_model: function(m, index) {
        // if no available class for model exists, skip model add
        var view_cls = this.get_model_view_cls(m);
        if (!view_cls) { return }
        
        // avoid duplicate entries
        if (this._model_views[m.id]) { return }
        
        // handle empty collection
        this.check_empty();
        
        // initialize view
        var model_view_options = {model: m}
        var extra_options = this.model_view_options(m);
        _.extend(model_view_options, extra_options);
        var view = this.create_view(this.get_model_view_cls(m),
                                    model_view_options);
        this.add_model_view(view, m, index);
      },

      add_model_view: function(view, model, index) {
        // append html element to the parent
        var el = view.init_element();
        // append to registry object
        this._model_views[model.id] = view;
        el.addClass("model-item");
        // where to place ?
        var parent = this.parent_for_model(model);
        // append
        this.place_in_parent(parent, el, model, index);
        // make it visible by default
        this.add_subview(view);
        view.show(true);
        this.post_add_model_view(view, model);
        this.bind_custom_view_handlers(view, model);
      },

      post_add_model_view: function() {},

      each_model_view: function(cb, context) {
        if (!context) { context = this };
        _.each(this._model_views, function(view, model_id){
          var model = this.collection.get(model_id);
          cb.call(this, model, view, model_id);
        }, this);
      },

      remove_model: function(m) {
        var model_view = this._model_views[m.id];
        if (!model_view) {
          console.error("no view found");
          return;
        }
        model_view.hide();
        model_view.el.remove();
        this.remove_view(model_view);
        this.unbind_custom_view_handlers(model_view, m);
        this.post_remove_model_view(model_view, m);
        $(window).trigger("resize");
        delete this._model_views[m.id];
        this.check_empty();
      },
      
      bind_custom_view_handlers: function(view, model) {},
      unbind_custom_view_handlers: function(view, model) {},
      post_remove_model_view: function() {},

      update_models: function(m) {
        this.check_empty();
        this.collection.each(function(model, index) {
          if (!(model.id in this._model_views)) {
            this.add_model(model, index);
          } else {
            if (model != this._model_views[model.id].model) {
              this._model_views[model.id].model = model;
              this._model_views[model.id].rivets_unbind();
              this._model_views[model.id].rivets_bind();
            }
            this.handle_model_change(model);
          }
        }, this);
        
        this.each_model_view(function(model, view, model_id){
          if (!model) {
            model = {'id': model_id};
            this.remove_model(model);
          }
        })
      }
    });

    views.ext.CollectionSelectView = views.ext.CollectionView.extend({
      allow_multiple: false,
      initialize: function(options) {
        views.ext.CollectionSelectView.__super__.initialize.apply(this, [options]);
        this.allow_multiple = options.allow_multiple != undefined ? options.allow_multiple : this.allow_multiple;
        this.current = options.current != undefined ? options.current : undefined;
      },

      select: function(model) {
        if (!this.allow_multiple) {
          this.deselect_all();
        }
        this._model_views[model.id].select();
      },

      deselect: function(model) {
        this._model_views[model.id].deselect();
      },

      deselect_all: function(model) {
        _.each(this._model_views, function(view) {
          view.deselect();
        })
      },    
      
      get_selected: function() {
        var models = _.map(this._model_views, function(view) {
          if (view.selected) { 
            return view.model
          }
        });
        return _.filter(models, function(m) { return m });
      },
      
      handle_click: function(view) {
        if (!view.selected && !view.disabled) {
          if (!this.allow_multiple) {
            this.deselect_all();
          }
        }
      },

      post_add_model_view: function(view, model) {
        view.bind('click', function() {
          this.handle_click(view);
        }, this);

        view.bind('selected', function(view) {
          if (this.current != view.model) {
            this.current = view.model;
            this.trigger("change", this.get_selected());
          }
        }, this);
      },

      set_current: function(model) {
        this._model_views[model.id].select();
      }

    });

    views.ext.ModelView = views.ext.View.extend({
      rivets_view: true,
      
      initialize: function() {
        views.ext.ModelView.__super__.initialize.apply(this, arguments);
        var actions = this.model.get('actions');
        if (actions) {
          this.init_action_methods(this.model.get('actions'));
          this.bind("hide", function() {
            actions.reset_pending();
          });
        }
      },
      
      action_cls_map: {
        'remove': 'destroy'
      },

      _set_confirm: function(action) {
        this.pending_action = action;
        this.set_action_indicator(action);
      },

      _unset_confirm: function(action) {
        this.pending_action = undefined;
        this.reset_action_indicator(action);
      },

      set_action_indicator: function(action) {
        action = this.action_cls_map[action] || action;
        var indicator = this.el.find(".action-indicator");
        indicator = $(indicator[indicator.length - 1]);
        indicator.attr("class", "").addClass("state action-indicator " + action);
      },

      reset_action_indicator: function() {
        var indicator = this.el.find(".action-indicator");
        indicator = $(indicator[indicator.length - 1]);
        indicator.attr("class", "").addClass("state action-indicator");
        if (this.pending_action) {
          this.set_action_indicator(this.pending_action);
        }
      },

      set_confirm: function() {},
      unset_confirm: function() {},

      init_action_methods: function(actions) {
        var self = this;
        if (this.model && this.model.actions) {
          this.model.actions.bind("reset-pending", function() {
            this._unset_confirm();
          }, this);
          this.model.actions.bind("set-pending", function(action) {
            this._set_confirm(action)
          }, this);
        }
        _.each(actions.actions, function(action) {
          this.el.find(".action-container." + action).hover(function() {
            self.set_action_indicator(action);
          }, function() {
            self.reset_action_indicator();
          });
          var method;
          method = 'set_{0}_confirm'.format(action);
          if (this[method]) { return }
          this[method] = _.bind(function(model, ev) {
            if (ev) { ev.stopPropagation() }
            var data = {};
            this._set_confirm(action);
            this.set_confirm(action);
            this.model.actions.set_pending_action(action);
          }, this);
          method = 'unset_{0}_confirm'.format(action);
          if (this[method]) { return }
          this[method] = _.bind(function(model, ev) {
            if (ev) { ev.stopPropagation() }
            var data = {};
            this._unset_confirm(action);
            this.unset_confirm(action);
            this.model.actions.unset_pending_action(action);
          }, this);
        }, this);
      },

      get_rivet_object: function() {
        var model = {
          model: this.model
        }
        return model
      },

      post_init_element: function() {},

      init_element: function() {
        this.el.attr("id", "model-" + this.model.id);
        this.post_init_element();
        this.update_layout();
        return this.el;
      },

      update_layout: function() {}

    });
    
    views.ModelRenameView = views.ext.ModelView.extend({
      tpl: '#rename-view-tpl',
      title_attr: 'name',

      init: function() {
        views.ModelRenameView.__super__.init.apply(this, arguments);
        this.name_cont = this.$(".model-name");
        this.edit_cont = this.$(".edit");

        this.edit_btn = this.$(".edit-btn");
        this.value = this.$(".value");
        this.input = this.$("input");
        this.confirm = this.edit_cont.find(".confirm");
        this.cancel = this.edit_cont.find(".cancel");
        
        if (this.model.get('rename_disabled')) {
          this.edit_btn.remove();
        }

        this.value.dblclick(_.bind(function(e) {
          this.set_edit();
        }, this));
        this.input.bind('keyup', _.bind(function(e) {
          // enter keypress
          if (e.which == 13) { this.rename(); }
          // esc keypress
          if (e.which == 27) { this.unset_edit(); }
        }, this));
        // initial state
        this.unset_edit();
      },
      
      post_hide: function() {
        this.unset_edit();
      },

      set_edit: function() {
        if (this.model.get('rename_disabled')) { return }
        var self = this;
        this.input.val(this.model.get('name'));
        window.setTimeout(function() {
          self.input.focus();
        }, 20);
        this.name_cont.hide();
        this.edit_cont.show();
      },

      unset_edit: function() {
        this.name_cont.show();
        this.edit_cont.hide();
      },

      rename: function() {
        var value = _.trim(this.input.val());
        if (value) {
          this.model.rename(value);
          this.unset_edit();
        }
      }
    });

    views.ext.SelectModelView = views.ext.ModelView.extend({
      can_deselect: true,
      select: function() {
        if (!this.delegate_checked) {
          this.input.attr("checked", true);
          this.item.addClass("selected");
          this.item.attr("selected", true);
        }
        this.selected = true;
        this.trigger("change:select", this, this.selected);
        this.trigger("selected", this, this.selected);
        this.parent_view && this.parent_view.trigger("change:select", this, this.selected);
      },

      deselect: function() {
        if (!this.delegate_checked) {
          this.input.attr("checked", false);
          this.item.removeClass("selected");
          this.item.attr("selected", false);
        }
        this.selected = false;
        this.trigger("change:select", this, this.selected);
        this.trigger("deselected", this, this.selected);
        this.parent_view && this.parent_view.trigger("change:select", this, this.selected);
      },
      
      toggle_select: function() {
        if (!this.can_deselect) {
          this.select();
          return;
        }
        if (this.selected) { 
          this.deselect();
        } else {
          this.select();
        }
      },

      post_init_element: function() {
        this.input = $(this.$("input").get(0));
        this.item = $(this.$(".select-item").get(0));
        if (!this.item.length) {
          this.item = $(this.el);
        }
        this.delegate_checked = this.model.get('noselect');
        this.deselect();

        var self = this;
        if (self.model.get('forced')) {
          this.select();
          this.input.attr("disabled", true);
          $(this.el).attr('title', this.forced_title);
          $(this.el).tooltip({
            'tipClass': 'tooltip', 
            'position': 'top center',
            'offset': [29, 0]
          });
        }
        
        $(this.item).click(function(e) {
          self.trigger('click');
          if (self.model.get('forced')) { return }
          if (self.input.attr('disabled')) { return }
          if (self.disabled) { return }
          e.stopPropagation();
          self.toggle_select();
        });
        
        views.ext.SelectModelView.__super__.post_init_element.apply(this,
                                                                    arguments);
      },

      set_disabled: function() {
        this.disabled = true;
        this.input.attr("disabled", true);
        this.item.addClass("disabled");
        this.item.attr("disabled", true);
      },

      set_enabled: function() {
        this.disabled = false;
        this.input.attr("disabled", false);
        this.item.removeClass("disabled");
        this.item.attr("disabled", false);
      }

    });

    views.ext.ModelCreateView = views.ext.ModelView.extend({});
    views.ext.ModelEditView = views.ext.ModelCreateView.extend({});

})(this);
