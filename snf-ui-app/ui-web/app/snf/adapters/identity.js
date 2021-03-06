import SnfRestAdapter from 'ui-web/snf/adapters/base';

/*
 * Synnefo Identity adapter.
 * 
 * https://www.synnefo.org/docs/synnefo/latest/identity-api-guide.html
 *
 */
export default SnfRestAdapter.extend({
  apiKey: 'account',
  typePathMap: {
    'user': 'user_catalogs'
  },
  
  optionsForType: function(type, options) {
    if (type == 'user') {
      // at the moment we allow only single user id/email resolving
      var urlParts = options.url.split("/");

      var lastPart = urlParts[urlParts.length - 1];
      var userPart = unescape(lastPart);
  
      if (userPart.indexOf('email=') > -1 || userPart.indexOf("@") > 0) {
        var userEmail = userPart.replace('email=', '');
        return {
          'url': options.url.replace(lastPart, ''),
          'type': 'POST',
          'data': JSON.stringify({
            'displaynames': [userEmail]
          })
        }
     } else {
        var userId = userPart;
        return {
          'url': options.url.replace(userPart, ''),
          'type': 'POST',
          'data': JSON.stringify({
            'uuids': [userId]
          })
        }
      }

    }
  }
});

