Snf.VolumesRoute = Snf.ElemsRoute.extend({
    modelName: 'volume',
});

Snf.VolumeRoute = Ember.Route.extend({
    renderTemplate: function() {

        this.render('details');

        var controller = this.controllerFor('volumes');
        if (!controller.get('model').get("length")) {
            controller.set('model',this.store.find('volume'));
        }

        this.render('lt-bar', {
            into: 'details',
            outlet: 'lt-bar',
            controller: controller,
        });
    },
});


Snf.VolumeIndexRoute = Ember.Route.extend({
    beforeModel: function() {
        this.transitionTo('volume.info');
    },
});


Snf.VolumeinitRoute = Ember.Route.extend({
    model: function(){
        return this.store.find('volume');
    },
    afterModel: function(model) {
       this.transitionTo('volume', model.get('firstObject').id);
    },
});

Snf.VolumeInfoRoute = Ember.Route.extend({
    renderTemplate: function() {
        this.render('details/info');
    },
    model: function () {
        return this.modelFor("volume");
    },
});

Snf.VolumeVmConnectedRoute = Ember.Route.extend({
    renderTemplate: function() {
        this.render('details/disk-connected');
    },
    model: function () {
        return this.modelFor("volume");
    }
});
