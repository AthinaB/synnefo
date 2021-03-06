import DS from 'ember-data';

export default DS.RESTSerializer.extend({
  extractArray: function(store, type, payload) {
    payload = {groups: payload.groups || []};
    return this._super(store, type, payload);
  },
});
