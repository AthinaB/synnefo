import Ember from 'ember';

export default Ember.ObjectController.extend({
  usersExtended: [],
  allUsersValid: false,

  horror: function() {
    console.log('%c[HORROR]', 'color:red', this.toString())
    console.log('%c[HORROR]', 'color:red', this.get('usersExtended').length)
  }.observes('this.usersExtended.@each'),

  init: function() {
    this.set('usersExtended', [])
  },

  actions: {
    addUser: function(user) {
      console.log('%c[GROUP]', 'color:green', this.toString())
      var usersExtended = this.get('usersExtended');

      if(this.get('usersExtended').filterBy('email', user.email).get('length') === 0) {

        var userExtended = Ember.Object.create({
          email: user.email,
          status: user.status,
          errorMsg: user.errorMsg,
        });

        usersExtended.pushObject(userExtended);
        // usersExtended.addObject({'xo': 'xo'});
        this.set('usersExtended', usersExtended)

        if(user.status !== 'error') {
          this.send('findUser', user.email);
        }
      }
    },

    updateUser: function(email, data) {

      // for(var prop in data) {
      //   this.get('usersExtended').findBy('email', email).set(prop, data[prop]);
      // }

    },

    removeUser: function(email) {

      // var user = this.get('usersExtended').findBy('email', email);

      // this.get('usersExtended').removeObject(user);

    },

    findUser: function(email) {

    //   var self = this;
    //   var userEmail = 'email='+email;

    //   this.store.find('user', userEmail).then(function(user) {

    //     var userExtended = self.get('usersExtended').findBy('email', email);

    //       if(userExtended) {
    //         self.send('updateUser', email, {uuid: user.get('uuid'), status: 'success'});
    //       }
    // },function(error) {

    //     var userExtended = self.get('usersExtended').findBy('email', email);

    //       if(userExtended) {
    //         self.send('updateUser', email, {uuid: undefined, status: 'error', 'errorMsg': 'Not found'});
    //       }
    //   });
    },
    deleteGroup: function(){
      // var group = this.get('model');

      // var onSuccess = function(data) {
      //   console.log('success');
      // };

      // var onFail = function(reason){
      //   console.log('reason:', reason);
      //   self.send('showActionFail', reason);
      // };

      // group.deleteRecord();

      // group.save().then(onSuccess, onFail);
    },

    removeUserFromGroup: function(user){
      // var self = this;
      // var group = this.get('model');

      // var onSuccess = function(data) {
      //   console.log('success');
      // };

      // var onFail = function(reason){
      //   console.log('reason:', reason);
      //   self.send('showActionFail', reason);
      // };

      // group.get("users").then(function(users){
      //   users.removeObject(user);
      //   if (users.content.length === 0) {
      //     self.send('deleteGroup');
      //   } else {
      //     group.save().then(onSuccess, onFail);
      //   }
      // }, onFail);
   },

    addUsers: function(){
    //   var self = this;
    //   var group = this.get('model');
    //   var newEmails = this.get('newEmails') || '';
    //   if (!newEmails.trim()) { return; }

    //   newEmails = newEmails.split(',');
    //   if (newEmails.length <1 ) { return; }

    //   var onSuccess = function(data) {
    //     self.set('newEmails', '');
    //   };
 
    //   var onFail = function(reason){
    //     console.log('reason:', reason);
    //     self.send('showActionFail', reason);
    //   };

    //   var newUsers = newEmails.map(function(email) {
    //     var userEmail = 'email='+email.trim();
    //     return self.store.find('user', userEmail);
    //   });

    //   return Ember.RSVP.all(newUsers).then(function(res){ 
    //     group.get('users').pushObjects(res).then(function() {
    //       group.save().then(onSuccess, onFail);
    //     });
    //   }, onFail);

    }

  },
});
