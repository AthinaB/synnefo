import Ember from 'ember';

// extend from contrllers that have actions that take params
// from form of inputSingleView
export default Ember.Mixin.create({
  value: '',
  //  replace it with:
  // Ember.computed.bool('objectsCount') or
  // Ember.computed.equal('selectedItems.length', 1)
  
  // if i disable the action btn the empty message is not necessary
  // notEmpty: function() {
  //   return this.get('value') ? true : false;
  // }.property('value'),

  withSlash: function() {
    return this.get('value').indexOf('/') !== -1;
  }.property('value'),

  largeName: function() {
    var charLimit = this.get('nameMaxLength');
    return this.get('value').length > charLimit;
  }.property('value'),

  largePath: function() {
    var charLimit = this.get('nameMaxLength');
    var newPath = this.get('current_path') + this.get('value');
    return (newPath.length + 1) > charLimit;
  }.property('value'),

  isModified: function() {
    var oldValue = this.get('oldValue'); // to be replaced with stripped name?
    if(oldValue && oldValue === this.get('value')) {
      return false;
    }
    else {
      return true;
    }
  }.property('value'),

  isUnique: function() {}.property('value'),

  actions: {
    validateInput: function() {
      var validValue;

      switch(this.get('stripped_name')) {
        case 'object': //rename object
        case 'objects': //create directory
          var withSlash = this.get('withSlash'),
              largeName = this.get('largeName'),
              largePath = this.get('largePath'),
              notUnique = !this.get('isUnique'),
              withSlashMsg = '"/" is not allowed',
              largeNameMsg = 'Too large name. Max: ' + this.get('nameMaxLength') + ' bytes',
              largePathMsg = 'Too large path. Max: ' + this.get('nameMaxLength') + ' bytes',
              notUniqueMsg = 'Already exists';

          if(withSlash) {
            this.set('errorMessage', withSlashMsg);
          }
          else if(largeName) {
            this.set('errorMessage', largeNameMsg);
          }
          else if(largePath) {
            this.set('errorMessage', largePathMsg);
          }
          else if(notUnique) {
            this.set('errorMessage', notUniqueMsg);
          }
          else {
            console.log('$c Valid value', 'color:blue',this.get('value'))
            this.set('errorMessage', undefined)
          }
          break;
        case 'containers': // create container
          var withSlash = this.get('withSlash'),
            largeName = this.get('largeName'),
            notUnique = !this.get('isUnique');
            withSlashMsg = '"/" is not allowed',
            largeNameMsg = 'Too large name. Max: ' + this.get('nameMaxLength') + ' bytes',
            notUniqueMsg = 'Already exists';
          
          if(withSlash) {
            this.set('errorMessage', withSlashMsg);
          }
          else if(largeName) {
            this.set('errorMessage', largeNameMsg);
          }
          else if(notUnique) {
            this.set('errorMessage', notUniqueMsg);
          }
          else {
            console.log('$c Valid value', 'color:blue',this.get('value'))
            this.set('errorMessage', undefined)
          }
      }
    }
    // this.set('validValue', validValue)
  }
});
