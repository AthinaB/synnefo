import Ember from 'ember';
import FilesListMixin from 'snf-ui/mixins/shared-files-list';
import ObjectsController from 'snf-ui/controllers/objects';

var alias = Ember.computed.alias;

export default ObjectsController.extend(FilesListMixin, {
  needs: ['account/container'],
  account: alias('controllers.account/container.account'),
  cont: alias('controllers.account/container.cont'),
  container_id: alias('cont.id'),
  container_name: alias('cont.name'),
  rootPath: alias('cont.name'),
  mine: false,

  canDelete: false,
  canTrash: false,
  canCopy: true,
  canMove: false,
  canUpload: Ember.computed.equal('parent_dir.allowed_to', 'write'),
  canCreate: Ember.computed.equal('parent_dir.allowed_to', 'write'),
  canRestore: false,

  parentPath: function() {
    var path = this.get('current_path');
    if (!path) {
      return false;
    }
  }.property('current_path')
});
