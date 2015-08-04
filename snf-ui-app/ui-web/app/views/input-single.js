import Ember from 'ember';

/*
* For now this view is used for 3 things:
*  - create container
*  - create directory
*  - rename object
* The above actions set or modify the ID of the record.
* The view runs some validations for the input value but the controller
* of the corresponding action checks if there is already another object
* with the new ID.
*
* The view accepts the following parameters:
*  - value: for renaming is the the stripped name of the object
*  - oldValue: for renaming is the the initial stripped name of the object
*    It is used in order to determine if the name of the object has been
*    modified.
*  - cls: class names
*  - placeholder
*
* Note: each of the above actions are handled by a different controller.

* Each controller must have these properties:
* - validationOnProgress
* - isUnique
* - actionToExec
* - newID
* - newName
* Also, should have checkUnique function
*
* If the checks of the view result that the input is in a valid form,
* the controller must check if the ID is unique
*/

export default Ember.View.extend({
  classNames: ['input-with-valid', 'js-input-single'],
  classNameBindings: ['cls'], // cls is provided by parent the template

  templateName: 'input-single',

  oldValue: undefined,


  // inputValue: function() {
  //   console.log('%c[3] InputView: inputValue', 'color:green')
  //   var value = this.$('input').val();
  //   if(value) {
  //     value = value.trim();
  //   }
  //   else {
  //     value = '';
  //   }
  //   console.log('value', value)
  //   return value;
  // },

  errorVisible: false,

  notEmpty: function() {
    var value = this.get('value');
    if(value) {
      value = value.trim();
    }
    else {
      value = null;
    }
    console.log('[notEmpty]', value)
    if(value === null) {
      this.set('value', undefined);
      return false;
    }
    else {
      this.set('value', value);
      return true;
    }
  }.property('value'),


  /* 
  * isModified is used for rename action.
  * For actions that don't check an old value, like create actions,
  * returns true, so that we won't nedd to check for which action we
  * are validating.
  */
  isModified: function() {
    var oldValue = this.get('oldValue');
    if(oldValue && oldValue === this.get('value')) {
      return false;
    }
    else {
      return true;
    }
  }.property('value'),

  isLargeName: function() {
    var charLimit = this.get('controller').get('nameMaxLength');
    return this.get('value').length > charLimit;
  }.property('value'),

  // for objects actions (create, rename)
  isLargePath: function() {
    var charLimit = this.get('controller').get('nameMaxLength');
    // current_path is a prop of ObjectsController
    var currentPath = this.get('controller').get('current_path') || this.get('controller').get('parentController').get('current_path');
    var newPath = currentPath + this.get('value');
    return (newPath.length + 1) > charLimit;
  }.property('value'),

  adjustSize: function() {
    var self = this;
    return function() {
      if(!self.get('errorVisible')) {
        if(self.get('isLargeName')) {
          self.send('showInfo','largeName');
        }
        else if((self.get('controller').get('name') !== 'containers') && self.get('isLargePath')) {
          self.send('showInfo','largePath');
        }
      }
    };
  }.property(), // like partial input but could check and path

  checkSlash: function() {
    var self = this;
    return function() {
      debugger;
      console.log(self.toString(), self.get('value'))
      if(!self.get('errorVisible')) {
        var hasSlash = self.get('value').indexOf('/') !== -1;
        if(hasSlash) {
          self.send('showInfo','hasSlash');
        }
      }
    };
  }.property(),

  isUnique: function() {
    var self = this;
    return function() {
      if(!self.get('errorVisible')) {
        self.get('controller').set('newName', self.get('value'));
        var notUnique = !self.get('controller').get('isUnique');
        var isModified = self.get('isModified');
        if(isModified && notUnique) {
          self.send('showInfo', 'notUnique');
        }
      }
    };
  }.property(), // different for rename and create, works with controller, runs only if isModified is true


  allowAction: function() {
    var self = this;
    return function () {
      if(self.get('isModified') && !self.get('errorVisible')) {
        self.get('controller').set('allowAction', true);
      }
    };
  }.property(),

  didInsertElement: function() {
    console.log('%cdidInsertElement', 'color:green', this.get('value'), this.toString())
  },

  spiounos: function() {
    console.log('[spiounos]', this.get('value'))
  }.observes('value'),

  eventManager: Ember.Object.create({
    keyUp: function(event, view) {
      var escKey = 27;
      // var enterKey =
      event.stopPropagation();
      if(event.keyCode == escKey) {
        console.log('%cClose', 'color:green')
        $('body .close-reveal-modal').trigger('click');
        view.$().siblings('.js-cancel').trigger('click');
      }
      // not sure if it is need it
      // else if(event.keyCode == enterKey) {

      // }
      else {
        view.send('hideInfo')
        var value = view.$('input').val();
        view.set('value', value);
        if(view.get('notEmpty')) {
          // view.get('controller').set('notEmpty', true);
            console.log(view.get('value'), view.toString())
            debugger;
            view.get('checkSlash')();
            view.get('adjustSize')();
            view.get('isUnique')();
            view.get('allowAction')();
          setTimeout(function() {
            console.log(view.get('value'), view.toString())
            console.log(this.get('value'), this.toString())
            debugger;
          }, 300);
            /*
            * Each function checks the trimmed value of the input only if
            * the function before it, hasn't detect an error. We do this
            * because we display one error at the time. 
            */
        }
        else {
          this.get('controller').set('allowAction', false);
        }
      }
    }
  }),

  actions: {
    reset: function() {
    },

    hideInfo: function() {
      this.set('errorVisible', false);
    },

    showInfo: function(type) {
      /*
      * type can take the values:
      *  - hasSlash
      *  - largePath
      *  - largeName
      *  - notUnique
      */

      var messages = {};
      messages['hasSlash'] = '"/" is not allowed',
      messages['largeName'] = 'Too large name. Max: ' + this.get('nameMaxLength') + ' bytes',
      messages['largePath'] = 'Too large path. Max: ' + this.get('nameMaxLength') + ' bytes',
      messages['notUnique'] = 'Already exists';

      this.get('controller').set('allowAction', false);
      this.set('errorMsg', messages[type]);
      this.set('errorVisible', true);
    }
  },
});
