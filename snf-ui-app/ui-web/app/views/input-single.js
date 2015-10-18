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
* Note: each of the above actions are handled by a different controller.
*/
export default Ember.View.extend({
	classNames: ['input-with-valid', 'js-input-single'],
	classNameBindings: ['cls'], // cls is provided by parent the template

	templateName: 'input-single',

	oldValue: undefined,
	inputValue: function() {
    console.log('%c[3] InputView: inputValue', 'color:green')
		var value = this.$('input').val();
		if(value) {
			value = value.trim();
		}
		else {
			value = '';
		}
    console.log('value', value)
		return value;
	}.property('controller.validationOnProgress'),

	errorVisible: false,

	notEmpty: function() {
		var value = this.get('inputValue');
		return value ? true : false;
	}.property('inputValue'),

	noSlash: function() {
    console.log('noSlash', this.get('inputValue').indexOf('/') === -1)
		return this.get('inputValue').indexOf('/') === -1;
	}.property('inputValue'),

	notTooLargeName: function() {
		var charLimit = this.get('controller').get('nameMaxLength');
		return this.get('inputValue').length <= charLimit;
	}.property('inputValue'),

	notTooLargePath: function() {
		var charLimit = this.get('controller').get('nameMaxLength');
		var newPath = this.get('controller').get('current_path') + this.get('inputValue');
		return (newPath.length + 1) <= charLimit;
	}.property('inputValue'),

	isModified: function() {
		var oldValue = this.get('oldValue');
		if(oldValue && oldValue === this.get('inputValue')) {
			return false;
		}
		return true;
	}.property('inputValue'),

	/*
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

	validateInput: function() {
    console.log(1)
    var toValidate = this.get('controller').get('validationOnProgress');
    if(toValidate) {
      console.log(2)
			var action = this.get('controller').get('actionToExec');
			var validForm = false;
			var notEmpty, noSlash, notTooLargeName, notTooLargePath;
			var isModified = this.get('isModified');
			this.set('errorVisible', false);

      notEmpty = this.get('notEmpty');
      noSlash = this.get('noSlash');
      notTooLargeName = this.get('notTooLargeName');

      if(action === 'createContainer') {
				validForm = notEmpty && noSlash && notTooLargeName;

				if(validForm) {
					this.get('controller').set('newName', this.get('inputValue'));
				}
			}
			else if(action === 'createDir' || action === 'renameObject') {
				notTooLargePath = this.get('notTooLargePath');
				validForm = notEmpty && noSlash && notTooLargeName && notTooLargePath;
				if(!isModified) {
          console.log('%cNot Modified', 'color:red')
    			this.get('parentView').set('wait', false);
          this.get('parentView').send('reset');
        }
        else if(validForm) {
          this.get('controller').set('newName', this.get('inputValue'));
        }
      }
      if(!validForm && isModified) {
        this.send('showError');
      }
    }

  }.observes('controller.validationOnProgress').on('init'),

  completeValidations: function() {
    var isUnique = this.get('controller').get('isUnique');
    if(isUnique !== undefined) {
      if(!isUnique) {
        this.send('showError', 'notUnique');
      }
      this.get('controller').set('validInput', isUnique);
      this.get('controller').set('validationOnProgress', false);
      // this.get('parentView').set('wait', false);
		}
	}.observes('controller.isUnique'),

	reset: function() {
    console.log('input-single: reset 1!')
    if(this.get('controller').get('resetInput')) {
      console.log('input-single: reset 2!')
			this.set('errorVisible', false);
			this.$('input').val(this.get('value'));
			this.set('errorMsg', '');
      this.get('controller').set('resetInput', false);
			this.get('controller').set('validationOnProgress', false);
      // this.get('parentView').set('wait', false)
		}
	}.observes('controller.resetInput'),

	eventManager: Ember.Object.create({
		keyUp: function(event, view) {
			var escKey = 27;
			event.stopPropagation();
			if(event.keyCode == escKey) {
        $('body .close-reveal-modal').trigger('click');
				view.$().siblings('.js-cancel').trigger('click');
			}
		}
	}),

	actions: {
		showError: function(notUnique) {
			var action = this.get('controller').get('actionToExec');
			this.set('errorVisible', false);
			if(notUnique) {
				this.set('errorMsg', 'Already exists');
			}
			else {
				var notEmpty = this.get('notEmpty');
				var notTooLargeName = this.get('notTooLargeName');
				var noSlash = this.get('noSlash');

        if(!notEmpty) {
          this.set('errorMsg', 'Empty input');
        }
        else if(!notTooLargeName) {
          this.set('errorMsg', 'Too large name. Max: ' + this.get('controller').get('nameMaxLength') + ' bytes');
        }
				if(!noSlash) {
					this.set('errorMsg', '"/" is not allowed');
				}
				else if(action === 'createDir') {
					var notTooLargePath = this.get('notTooLargePath');
					if(!notTooLargePath) {
						this.set('errorMsg', 'Too large path. Max: ' + this.get('controller').get('nameMaxLength') + ' bytes')
					}
				}
			}
			this.set('errorVisible', true);
			this.get('controller').set('validationOnProgress', false);
		},
	},
});
