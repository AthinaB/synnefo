#
# Copyright (c) 2010 Greek Research and Technology Network
#

from __future__ import with_statement

from collections import defaultdict
from email.utils import parsedate
from random import choice, randint, sample
from time import mktime

from django.utils import simplejson as json
from django.test import TestCase
from django.test.client import Client

from synnefo.db.models import *
from synnefo.logic.utils import get_rsapi_state


class AaiClient(Client):
    def request(self, **request):
        request['HTTP_X_AUTH_TOKEN'] = '46e427d657b20defe352804f0eb6f8a2'
        return super(AaiClient, self).request(**request)


class APITestCase(TestCase):
    fixtures = ['api_test_data']
    test_server_id = 1001
    test_image_id = 1
    test_flavor_id = 1
    test_group_id = 1
    test_wrong_server_id = 99999999
    test_wrong_image_id = 99999999
    test_wrong_flavor_id = 99999999
    test_wrong_group_id = 99999999
    #make the testing with these id's

    def setUp(self):
        self.client = AaiClient()

    def test_api_version(self):
        """Check API version."""
        
        response = self.client.get('/api/v1.1/')
        self.assertEqual(response.status_code, 200)
        api_version = json.loads(response.content)['version']
        self.assertEqual(api_version['id'], 'v1.1')
        self.assertEqual(api_version['status'], 'CURRENT')

    def test_server_list(self):
        """Test if the expected list of servers is returned."""
        
        response = self.client.get('/api/v1.1/servers')
        vms_from_api = json.loads(response.content)['servers']['values']
        vms_from_db = VirtualMachine.objects.filter(deleted=False)
        self.assertEqual(len(vms_from_api), len(vms_from_db))
        self.assertTrue(response.status_code in [200, 203])
        for vm_from_api in vms_from_api:
            vm_from_db = VirtualMachine.objects.get(id=vm_from_api['id'])
            self.assertEqual(vm_from_api['id'], vm_from_db.id)
            self.assertEqual(vm_from_api['name'], vm_from_db.name)

    def test_server_details(self):
        """Test if the expected server is returned."""
        
        response = self.client.get('/api/v1.1/servers/%d' % self.test_server_id)
        vm_from_api = json.loads(response.content)['server']
        vm_from_db = VirtualMachine.objects.get(id=self.test_server_id)
        self.assertEqual(vm_from_api['flavorRef'], vm_from_db.flavor.id)
        self.assertEqual(vm_from_api['hostId'], vm_from_db.hostid)
        self.assertEqual(vm_from_api['id'], vm_from_db.id)
        self.assertEqual(vm_from_api['imageRef'], vm_from_db.flavor.id)
        self.assertEqual(vm_from_api['name'], vm_from_db.name)
        self.assertEqual(vm_from_api['status'], get_rsapi_state(vm_from_db))
        self.assertTrue(response.status_code in [200, 203])

    def test_servers_details(self):
        """Test if the servers details are returned."""
        
        response = self.client.get('/api/v1.1/servers/detail')

        # Make sure both DB and API responses are sorted by id,
        # to allow for 1-1 comparisons
        vms_from_db = VirtualMachine.objects.filter(deleted=False).order_by('id')
        vms_from_api = json.loads(response.content)['servers']['values']
        vms_from_api = sorted(vms_from_api, key=lambda vm: vm['id'])
        self.assertEqual(len(vms_from_db), len(vms_from_api))

        id_list = [vm.id for vm in vms_from_db]
        number = 0
        for vm_id in id_list:
            vm_from_api = vms_from_api[number]
            vm_from_db = VirtualMachine.objects.get(id=vm_id)
            self.assertEqual(vm_from_api['flavorRef'], vm_from_db.flavor.id)
            self.assertEqual(vm_from_api['hostId'], vm_from_db.hostid)
            self.assertEqual(vm_from_api['id'], vm_from_db.id)
            self.assertEqual(vm_from_api['imageRef'], vm_from_db.flavor.id)
            self.assertEqual(vm_from_api['name'], vm_from_db.name)
            self.assertEqual(vm_from_api['status'], get_rsapi_state(vm_from_db))
            number += 1
        for vm_from_api in vms_from_api:
            vm_from_db = VirtualMachine.objects.get(id=vm_from_api['id'])
            self.assertEqual(vm_from_api['flavorRef'], vm_from_db.flavor.id)
            self.assertEqual(vm_from_api['hostId'], vm_from_db.hostid)
            self.assertEqual(vm_from_api['id'], vm_from_db.id)
            self.assertEqual(vm_from_api['imageRef'], vm_from_db.flavor.id)
            self.assertEqual(vm_from_api['name'], vm_from_db.name)
            self.assertEqual(vm_from_api['status'], get_rsapi_state(vm_from_db))
        self.assertTrue(response.status_code in [200,203])

    def test_wrong_server(self):
        """Test 404 response if server does not exist."""
        
        response = self.client.get('/api/v1.1/servers/%d' % self.test_wrong_server_id)
        self.assertEqual(response.status_code, 404)

    def test_create_server_empty(self):
        """Test if the create server call returns a 400 badRequest if
           no attributes are specified."""
        
        response = self.client.post('/api/v1.1/servers', {})
        self.assertEqual(response.status_code, 400)

    def test_create_server(self):
        """Test if the create server call returns the expected response
           if a valid request has been speficied."""
        
        request = {
                    "server": {
                        "name": "new-server-test",
                        "owner": 1,
                        "imageRef": 1,
                        "flavorRef": 1,
                        "metadata": {
                            "My Server Name": "Apache1"
                        },
                        "personality": []
                    }
        }
        response = self.client.post('/api/v1.1/servers', json.dumps(request),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 202)
        #TODO: check response.content
        #TODO: check create server with wrong options (eg non existing flavor)

    def test_server_polling(self):
        """Test if the server polling works as expected."""
        
        response = self.client.get('/api/v1.1/servers/detail')
        vms_from_api_initial = json.loads(response.content)['servers']['values']
        ts = mktime(parsedate(response['Date']))
        since = datetime.datetime.fromtimestamp(ts).isoformat() + 'Z'
        response = self.client.get('/api/v1.1/servers/detail?changes-since=%s' % since)
        self.assertEqual(len(response.content), 0)

        #now create a machine. Then check if it is on the list
        request = {
                    "server": {
                        "name": "new-server-test",
                        "imageRef": 1,
                        "flavorRef": 1,
                        "metadata": {
                            "My Server Name": "Apache1"
                        },
                        "personality": []
                    }
        }
        
        path = '/api/v1.1/servers'
        response = self.client.post(path, json.dumps(request), content_type='application/json')
        self.assertEqual(response.status_code, 202)

        response = self.client.get('/api/v1.1/servers/detail?changes-since=%s' % since)
        self.assertEqual(response.status_code, 200)
        vms_from_api_after = json.loads(response.content)['servers']['values']
        #make sure the newly created server is included on the updated list
        self.assertEqual(len(vms_from_api_after), 1)

    def test_reboot_server(self):
        """Test if the specified server is rebooted."""
        
        request = {'reboot': {'type': 'HARD'}}
        path = '/api/v1.1/servers/%d/action' % self.test_server_id
        response = self.client.post(path, json.dumps(request), content_type='application/json')
        self.assertEqual(response.status_code, 202)
        #server id that does not exist
        path = '/api/v1.1/servers/%d/action' % self.test_wrong_server_id
        response = self.client.post(path, json.dumps(request), content_type='application/json')
        self.assertEqual(response.status_code, 404)

    def test_shutdown_server(self):
        """Test if the specified server is shutdown."""
        
        request = {'shutdown': {}}
        path = '/api/v1.1/servers/%d/action' % self.test_server_id
        response = self.client.post(path, json.dumps(request), content_type='application/json')
        self.assertEqual(response.status_code, 202)
        #server id that does not exist
        path = '/api/v1.1/servers/%d/action' % self.test_wrong_server_id
        response = self.client.post(path, json.dumps(request), content_type='application/json')
        self.assertEqual(response.status_code, 404)

    def test_start_server(self):
        """Test if the specified server is started."""
        
        request = {'start': {}}
        path = '/api/v1.1/servers/%d/action' % self.test_server_id
        response = self.client.post(path, json.dumps(request), content_type='application/json')
        self.assertEqual(response.status_code, 202)
        #server id that does not exist
        path = '/api/v1.1/servers/%d/action' % self.test_wrong_server_id
        response = self.client.post(path, json.dumps(request), content_type='application/json')
        self.assertEqual(response.status_code, 404)

    def test_delete_server(self):
        """Test if the specified server is deleted."""
        response = self.client.delete('/api/v1.1/servers/%d' % self.test_server_id)
        self.assertEqual(response.status_code, 204)
        #server id that does not exist
        response = self.client.delete('/api/v1.1/servers/%d' % self.test_wrong_server_id)
        self.assertEqual(response.status_code, 404)

    def test_flavor_list(self):
        """Test if the expected list of flavors is returned by."""
        
        response = self.client.get('/api/v1.1/flavors')
        flavors_from_api = json.loads(response.content)['flavors']['values']
        flavors_from_db = Flavor.objects.all()
        self.assertEqual(len(flavors_from_api), len(flavors_from_db))
        self.assertTrue(response.status_code in [200, 203])
        for flavor_from_api in flavors_from_api:
            flavor_from_db = Flavor.objects.get(id=flavor_from_api['id'])
            self.assertEqual(flavor_from_api['id'], flavor_from_db.id)
            self.assertEqual(flavor_from_api['name'], flavor_from_db.name)

    def test_flavors_details(self):
        """Test if the flavors details are returned."""
        
        response = self.client.get('/api/v1.1/flavors/detail')
        flavors_from_db = Flavor.objects.all()
        flavors_from_api = json.loads(response.content)['flavors']['values']

        # Assert that all flavors in the db appear inthe API call result
        for i in range(0, len(flavors_from_db)):
            flavor_from_api = flavors_from_api[i]
            flavor_from_db = Flavor.objects.get(id=flavors_from_db[i].id)
            self.assertEqual(flavor_from_api['cpu'], flavor_from_db.cpu)
            self.assertEqual(flavor_from_api['id'], flavor_from_db.id)
            self.assertEqual(flavor_from_api['disk'], flavor_from_db.disk)
            self.assertEqual(flavor_from_api['name'], flavor_from_db.name)
            self.assertEqual(flavor_from_api['ram'], flavor_from_db.ram)

        # Assert that all flavors returned by the API also exist in the db
        for flavor_from_api in flavors_from_api:
            flavor_from_db = Flavor.objects.get(id=flavor_from_api['id'])
            self.assertEqual(flavor_from_api['cpu'], flavor_from_db.cpu)
            self.assertEqual(flavor_from_api['id'], flavor_from_db.id)
            self.assertEqual(flavor_from_api['disk'], flavor_from_db.disk)
            self.assertEqual(flavor_from_api['name'], flavor_from_db.name)
            self.assertEqual(flavor_from_api['ram'], flavor_from_db.ram)

        # Check if we have the right status_code
        self.assertTrue(response.status_code in [200, 203])

    def test_flavor_details(self):
        """Test if the expected flavor is returned."""
        
        response = self.client.get('/api/v1.1/flavors/%d' % self.test_flavor_id)
        flavor_from_api = json.loads(response.content)['flavor']
        flavor_from_db = Flavor.objects.get(id=self.test_flavor_id)
        self.assertEqual(flavor_from_api['cpu'], flavor_from_db.cpu)
        self.assertEqual(flavor_from_api['id'], flavor_from_db.id)
        self.assertEqual(flavor_from_api['disk'], flavor_from_db.disk)
        self.assertEqual(flavor_from_api['name'], flavor_from_db.name)
        self.assertEqual(flavor_from_api['ram'], flavor_from_db.ram)
        self.assertTrue(response.status_code in [200, 203])

    def test_wrong_flavor(self):
        """Test 404 result when requesting a flavor that does not exist."""
        
        response = self.client.get('/api/v1.1/flavors/%d' % self.test_wrong_flavor_id)
        self.assertTrue(response.status_code in [404, 503])

    def test_image_list(self):
        """Test if the expected list of images is returned by the API."""
        
        response = self.client.get('/api/v1.1/images')
        images_from_api = json.loads(response.content)['images']['values']
        images_from_db = Image.objects.all()
        self.assertEqual(len(images_from_api), len(images_from_db))
        self.assertTrue(response.status_code in [200, 203])
        for image_from_api in images_from_api:
            image_from_db = Image.objects.get(id=image_from_api['id'])
            self.assertEqual(image_from_api['id'], image_from_db.id)
            self.assertEqual(image_from_api['name'], image_from_db.name)

    def test_wrong_image(self):
        """Test 404 result if a non existent image is requested."""
        
        response = self.client.get('/api/v1.1/images/%d' % self.test_wrong_image_id)
        self.assertEqual(response.status_code, 404)

    def test_server_metadata(self):
        """Test server's metadata (add, edit)."""
        
        key = 'name'
        request = {'meta': {key: 'a fancy name'}}
        
        path = '/api/v1.1/servers/%d/meta/%s' % (self.test_server_id, key)
        response = self.client.put(path, json.dumps(request), content_type='application/json')
        self.assertEqual(response.status_code, 201)


def create_users(n=1):
    for i in range(n):
        SynnefoUser.objects.create(
            name='User %d' % i,
            credit=0)

def create_flavors(n=1):
    for i in range(n):
        Flavor.objects.create(
            cpu=randint(1, 4),
            ram=randint(1, 8) * 512,
            disk=randint(1, 40))

def create_images(n=1):
    users = SynnefoUser.objects.all()
    for i in range(n):
        Image.objects.create(
            name='Image %d' % (i + 1),
            state='ACTIVE',
            owner=choice(users))

def create_image_metadata(n=1):
    images = Image.objects.all()
    for i in range(n):
        ImageMetadata.objects.create(
            meta_key='Key%d' % (i + 1),
            meta_value='Value %d' % (i + 1),
            image = choice(images))

def create_servers(n=1):
    users = SynnefoUser.objects.all()
    flavors = Flavor.objects.all()
    images = Image.objects.all()
    for i in range(n):
        VirtualMachine.objects.create(
            name='Server %d' % (i + 1),
            owner=choice(users),
            sourceimage=choice(images),
            hostid=str(i),
            ipfour='0.0.0.0',
            ipsix='::1',
            flavor=choice(flavors))

def create_server_metadata(n=1):
    servers = VirtualMachine.objects.all()
    for i in range(n):
        VirtualMachineMetadata.objects.create(
            meta_key='Key%d' % (i + 1),
            meta_value='Value %d' % (i + 1),
            vm = choice(servers))

def create_networks(n):
    users = SynnefoUser.objects.all()
    for i in range(n):
        Network.objects.create(
            name='Network%d' % (i + 1),
            owner=choice(users))


class AssertInvariant(object):
    def __init__(self, callable, *args, **kwargs):
        self.callable = callable
        self.args = args
        self.kwargs = kwargs
    
    def __enter__(self):
        self.value = self.callable(*self.args, **self.kwargs)
        return self.value
    
    def __exit__(self, type, value, tb):
        assert self.value == self.callable(*self.args, **self.kwargs)


class BaseTestCase(TestCase):
    USERS = 0
    FLAVORS = 1
    IMAGES = 1
    SERVERS = 1
    SERVER_METADATA = 0
    IMAGE_METADATA = 0
    NETWORKS = 0
    
    def setUp(self):
        self.client = AaiClient()
        create_users(self.USERS)
        create_flavors(self.FLAVORS)
        create_images(self.IMAGES)
        create_image_metadata(self.IMAGE_METADATA)
        create_servers(self.SERVERS)
        create_server_metadata(self.SERVER_METADATA)
        create_networks(self.NETWORKS)
    
    def assertFault(self, response, status_code, name):
        self.assertEqual(response.status_code, status_code)
        fault = json.loads(response.content)
        self.assertEqual(fault.keys(), [name])
    
    def assertBadRequest(self, response):
        self.assertFault(response, 400, 'badRequest')

    def assertItemNotFound(self, response):
        self.assertFault(response, 404, 'itemNotFound')
    
    
    def list_images(self, detail=False):
        path = '/api/v1.1/images'
        if detail:
            path += '/detail'
        response = self.client.get(path)
        self.assertTrue(response.status_code in (200, 203))
        reply = json.loads(response.content)
        self.assertEqual(reply.keys(), ['images'])
        self.assertEqual(reply['images'].keys(), ['values'])
        return reply['images']['values']
    
    def list_metadata(self, path):
        response = self.client.get(path)
        self.assertTrue(response.status_code in (200, 203))
        reply = json.loads(response.content)
        self.assertEqual(reply.keys(), ['metadata'])
        self.assertEqual(reply['metadata'].keys(), ['values'])
        return reply['metadata']['values']
    
    def list_server_metadata(self, server_id):
        path = '/api/v1.1/servers/%d/meta' % server_id
        return self.list_metadata(path)
    
    def list_image_metadata(self, image_id):
        path = '/api/v1.1/images/%d/meta' % image_id
        return self.list_metadata(path)
    
    def update_metadata(self, path, metadata):
        data = json.dumps({'metadata': metadata})
        response = self.client.post(path, data, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        reply = json.loads(response.content)
        self.assertEqual(reply.keys(), ['metadata'])
        return reply['metadata']
    
    def update_server_metadata(self, server_id, metadata):
        path = '/api/v1.1/servers/%d/meta' % server_id
        return self.update_metadata(path, metadata)
    
    def update_image_metadata(self, image_id, metadata):
        path = '/api/v1.1/images/%d/meta' % image_id
        return self.update_metadata(path, metadata)
    
    def create_server_meta(self, server_id, meta):
        key = meta.keys()[0]
        path = '/api/v1.1/servers/%d/meta/%s' % (server_id, key)
        data = json.dumps({'meta': meta})
        response = self.client.put(path, data, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        reply = json.loads(response.content)
        self.assertEqual(reply.keys(), ['meta'])
        response_meta = reply['meta']
        self.assertEqual(response_meta, meta)
    
    def get_all_server_metadata(self):
        metadata = defaultdict(dict)
        for m in VirtualMachineMetadata.objects.all():
            metadata[m.vm.id][m.meta_key] = m.meta_value
        return metadata
    
    def get_all_image_metadata(self):
        metadata = defaultdict(dict)
        for m in ImageMetadata.objects.all():
            metadata[m.image.id][m.meta_key] = m.meta_value
        return metadata
    
    def list_networks(self, detail=False):
        path = '/api/v1.1/networks'
        if detail:
            path += '/detail'
        response = self.client.get(path)
        self.assertTrue(response.status_code in (200, 203))
        reply = json.loads(response.content)
        self.assertEqual(reply.keys(), ['networks'])
        self.assertEqual(reply['networks'].keys(), ['values'])
        return reply['networks']['values']
    
    def create_network(self, name):
        path = '/api/v1.1/networks'
        data = json.dumps({'network': {'name': name}})
        response = self.client.post(path, data, content_type='application/json')
        self.assertEqual(response.status_code, 202)
        reply = json.loads(response.content)
        self.assertEqual(reply.keys(), ['network'])
        return reply
    
    def get_network_details(self, network_id):
        path = '/api/v1.1/networks/%d' % network_id
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        reply = json.loads(response.content)
        self.assertEqual(reply.keys(), ['network'])
        return reply['network']
    
    def update_network_name(self, network_id, new_name):
        path = '/api/v1.1/networks/%d' % network_id
        data = json.dumps({'network': {'name': new_name}})
        response = self.client.put(path, data, content_type='application/json')
        self.assertEqual(response.status_code, 204)
    
    def delete_network(self, network_id):
        path = '/api/v1.1/networks/%d' % network_id
        response = self.client.delete(path)
        self.assertEqual(response.status_code, 204)
    
    def add_to_network(self, network_id, server_id):
        path = '/api/v1.1/networks/%d/action' % network_id
        data = json.dumps({'add': {'serverRef': server_id}})
        response = self.client.post(path, data, content_type='application/json')
        self.assertEqual(response.status_code, 202)
    
    def remove_from_network(self, network_id, server_id):
        path = '/api/v1.1/networks/%d/action' % network_id
        data = json.dumps({'remove': {'serverRef': server_id}})
        response = self.client.post(path, data, content_type='application/json')
        self.assertEqual(response.status_code, 202)


def popdict(l, **kwargs):
    """Pops a dict from list `l` based on the predicates given as `kwargs`."""
    
    for i in range(len(l)):
        item = l[i]
        match = True
        for key, val in kwargs.items():
            if item[key] != val:
                match = False
                break
        if match:
            del l[i]
            return item
    return None


class ListImages(BaseTestCase):
    IMAGES = 10
    
    def test_list_images(self):
        images = self.list_images()
        keys = set(['id', 'name'])
        for img in Image.objects.all():
            image = popdict(images, id=img.id)
            self.assertTrue(image is not None)
            self.assertEqual(set(image.keys()), keys)
            self.assertEqual(image['id'], img.id)
            self.assertEqual(image['name'], img.name)
        self.assertEqual(images, [])
    
    def test_list_images_detail(self):
        images = self.list_images(detail=True)
        keys = set(['id', 'name', 'updated', 'created', 'status', 'progress'])
        for img in Image.objects.all():
            image = popdict(images, id=img.id)
            self.assertTrue(image is not None)
            self.assertEqual(set(image.keys()), keys)
            self.assertEqual(image['id'], img.id)
            self.assertEqual(image['name'], img.name)
            self.assertEqual(image['status'], img.state)
            self.assertEqual(image['progress'], 100 if img.state == 'ACTIVE' else 0)
        self.assertEqual(images, [])


class ListServerMetadata(BaseTestCase):
    SERVERS = 5
    SERVER_METADATA = 100
    
    def test_list_metadata(self):
        with AssertInvariant(self.get_all_server_metadata) as metadata:
            for vm in VirtualMachine.objects.all():
                response_metadata = self.list_server_metadata(vm.id)
                self.assertEqual(response_metadata, metadata[vm.id])
    
    def test_invalid_server(self):
        with AssertInvariant(self.get_all_server_metadata):
            response = self.client.get('/api/v1.1/servers/0/meta')
            self.assertItemNotFound(response)


class UpdateServerMetadata(BaseTestCase):
    SERVER_METADATA = 10
    
    def test_update_metadata(self):
        metadata = self.get_all_server_metadata()
        server_id = choice(metadata.keys())
        new_metadata = {}
        for key in sample(metadata[server_id].keys(), 3):
            new_metadata[key] = 'New %s value' % key
        response_metadata = self.update_server_metadata(server_id, new_metadata)
        self.assertEqual(response_metadata, new_metadata)
        metadata[server_id].update(new_metadata)
        self.assertEqual(metadata, self.get_all_server_metadata())
    
    def test_does_not_create(self):
        with AssertInvariant(self.get_all_server_metadata) as metadata:
            server_id = choice(metadata.keys())
            new_metadata = {'Foo': 'Bar'}
            response_metadata = self.update_server_metadata(server_id, new_metadata)
            self.assertEqual(response_metadata, {})
    
    def test_invalid_data(self):
        with AssertInvariant(self.get_all_server_metadata) as metadata:
            server_id = choice(metadata.keys())
            path = '/api/v1.1/servers/%d/meta' % server_id
            response = self.client.post(path, 'metadata', content_type='application/json')
            self.assertBadRequest(response)
    
    def test_invalid_server(self):
        with AssertInvariant(self.get_all_server_metadata):
            path = '/api/v1.1/servers/0/meta'
            data = json.dumps({'metadata': {'Key1': 'A Value'}})
            response = self.client.post(path, data, content_type='application/json')
            self.assertItemNotFound(response)


class GetServerMetadataItem(BaseTestCase):
    SERVERS = 5
    SERVER_METADATA = 100
    
    def test_get_metadata_item(self):
        with AssertInvariant(self.get_all_server_metadata) as metadata:
            server_id = choice(metadata.keys())
            key = choice(metadata[server_id].keys())
            path = '/api/v1.1/servers/%d/meta/%s' % (server_id, key)
            response = self.client.get(path)
            self.assertTrue(response.status_code in (200, 203))
            reply = json.loads(response.content)
            self.assertEqual(reply['meta'], {key: metadata[server_id][key]})
    
    def test_invalid_key(self):
        with AssertInvariant(self.get_all_server_metadata) as metadata:
            server_id = choice(metadata.keys())
            response = self.client.get('/api/v1.1/servers/%d/meta/foo' % server_id)
            self.assertItemNotFound(response)
    
    def test_invalid_server(self):
        with AssertInvariant(self.get_all_server_metadata):
            response = self.client.get('/api/v1.1/servers/0/meta/foo')
            self.assertItemNotFound(response)


class CreateServerMetadataItem(BaseTestCase):
    SERVER_METADATA = 10
    
    def test_create_metadata(self):
        metadata = self.get_all_server_metadata()
        server_id = choice(metadata.keys())
        meta = {'Foo': 'Bar'}
        self.create_server_meta(server_id, meta)
        metadata[server_id].update(meta)
        self.assertEqual(metadata, self.get_all_server_metadata())
    
    def test_update_metadata(self):
        metadata = self.get_all_server_metadata()
        server_id = choice(metadata.keys())
        key = choice(metadata[server_id].keys())
        meta = {key: 'New Value'}
        self.create_server_meta(server_id, meta)
        metadata[server_id].update(meta)
        self.assertEqual(metadata, self.get_all_server_metadata())
    
    def test_invalid_server(self):
        with AssertInvariant(self.get_all_server_metadata):
            path = '/api/v1.1/servers/0/meta/foo'
            data = json.dumps({'meta': {'foo': 'bar'}})
            response = self.client.put(path, data, content_type='application/json')
            self.assertItemNotFound(response)
    
    def test_invalid_key(self):
        with AssertInvariant(self.get_all_server_metadata) as metadata:
            server_id = choice(metadata.keys())
            path = '/api/v1.1/servers/%d/meta/baz' % server_id
            data = json.dumps({'meta': {'foo': 'bar'}})
            response = self.client.put(path, data, content_type='application/json')
            self.assertBadRequest(response)
    
    def test_invalid_data(self):
        with AssertInvariant(self.get_all_server_metadata) as metadata:
            server_id = choice(metadata.keys())
            path = '/api/v1.1/servers/%d/meta/foo' % server_id
            response = self.client.put(path, 'meta', content_type='application/json')
            self.assertBadRequest(response)


class DeleteServerMetadataItem(BaseTestCase):
    SERVER_METADATA = 10
    
    def test_delete_metadata(self):
        metadata = self.get_all_server_metadata()
        server_id = choice(metadata.keys())
        key = choice(metadata[server_id].keys())
        path = '/api/v1.1/servers/%d/meta/%s' % (server_id, key)
        response = self.client.delete(path)
        self.assertEqual(response.status_code, 204)
        metadata[server_id].pop(key)
        self.assertEqual(metadata, self.get_all_server_metadata())
    
    def test_invalid_server(self):
        with AssertInvariant(self.get_all_server_metadata):
            response = self.client.delete('/api/v1.1/servers/9/meta/Key1')
            self.assertItemNotFound(response)
    
    def test_invalid_key(self):
        with AssertInvariant(self.get_all_server_metadata) as metadata:
            server_id = choice(metadata.keys())
            path = '/api/v1.1/servers/%d/meta/foo' % server_id
            response = self.client.delete(path)
            self.assertItemNotFound(response)


class ListImageMetadata(BaseTestCase):
    IMAGES = 5
    IMAGE_METADATA = 100

    def test_list_metadata(self):
        with AssertInvariant(self.get_all_image_metadata) as metadata:
            for image in Image.objects.all():
                response_metadata = self.list_image_metadata(image.id)
                self.assertEqual(response_metadata, metadata[image.id])

    def test_invalid_image(self):
        with AssertInvariant(self.get_all_image_metadata):
            response = self.client.get('/api/v1.1/images/0/meta')
            self.assertItemNotFound(response)

class UpdateImageMetadata(BaseTestCase):
    IMAGE_METADATA = 10

    def test_update_metadata(self):
        metadata = self.get_all_image_metadata()
        image_id = choice(metadata.keys())
        new_metadata = {}
        for key in sample(metadata[image_id].keys(), 3):
            new_metadata[key] = 'New %s value' % key
        response_metadata = self.update_image_metadata(image_id, new_metadata)
        self.assertEqual(response_metadata, new_metadata)
        metadata[image_id].update(new_metadata)
        self.assertEqual(metadata, self.get_all_image_metadata())

    def test_does_not_create(self):
        with AssertInvariant(self.get_all_image_metadata) as metadata:
            image_id = choice(metadata.keys())
            new_metadata = {'Foo': 'Bar'}
            response_metadata = self.update_image_metadata(image_id, new_metadata)
            self.assertEqual(response_metadata, {})

    def test_invalid_data(self):
        with AssertInvariant(self.get_all_image_metadata) as metadata:
            image_id = choice(metadata.keys())
            path = '/api/v1.1/images/%d/meta' % image_id
            response = self.client.post(path, 'metadata', content_type='application/json')
            self.assertBadRequest(response)

    def test_invalid_server(self):
        with AssertInvariant(self.get_all_image_metadata):
            path = '/api/v1.1/images/0/meta'
            data = json.dumps({'metadata': {'Key1': 'A Value'}})
            response = self.client.post(path, data, content_type='application/json')
            self.assertItemNotFound(response)


class ServerVNCConsole(BaseTestCase):
    SERVERS = 1

    def test_not_active_server(self):
        """Test console req for server not in ACTIVE state returns badRequest"""
        server_id = choice(VirtualMachine.objects.all()).id
        path = '/api/v1.1/servers/%d/action' % server_id
        data = json.dumps({'console': {'type': 'vnc'}})
        response = self.client.post(path, data, content_type='application/json')
        self.assertBadRequest(response)

    def test_active_server(self):
        """Test console req for ACTIVE server"""
        server_id = choice(VirtualMachine.objects.all()).id
        # FIXME: Start the server properly, instead of tampering with the DB
        vm = choice(VirtualMachine.objects.all())
        vm.operstate = 'STARTED'
        vm.save()
        server_id = vm.id
	
        path = '/api/v1.1/servers/%d/action' % server_id
        data = json.dumps({'console': {'type': 'vnc'}})
        response = self.client.post(path, data, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        reply = json.loads(response.content)
        self.assertEqual(reply.keys(), ['console'])
        console = reply['console']
        self.assertEqual(console['type'], 'vnc')
        self.assertEqual(set(console.keys()), set(['type', 'host', 'port', 'password']))


class AaiTestCase(TestCase):
    fixtures = ['api_test_data', 'auth_test_data']
    apibase = '/api/v1.1'

    def setUp(self):
        self.client = Client()

    def test_auth_cookie(self):
        user = SynnefoUser.objects.get(uniq = "test@synnefo.gr")
        self.client.cookies['X-Auth-Token'] = user.auth_token
        response = self.client.get('/index.html', {},
                                   **{'X-Auth-Token': user.auth_token,
                                      'TEST-AAI' : 'true'})
        self.assertTrue(response.status_code, 200)
        self.assertTrue('Vary' in response)
        self.assertTrue('X-Auth-Token' in response['Vary'])

    def test_fail_oapi_auth(self):
        """ test authentication from not registered user using OpenAPI
        """
        response = self.client.get(self.apibase + '/servers', {},
                                   **{'X-Auth-User': 'notme',
                                      'X-Auth-Key': '0xdeadbabe',
                                      'TEST-AAI' : 'true'})
        self.assertEquals(response.status_code, 401)

    def test_oapi_auth(self):
        """authentication with user registration
        """
        response = self.client.get(self.apibase + '/index.html', {},
                                   **{'X-Auth-User': 'testdbuser',
                                      'X-Auth-Key': 'test@synnefo.gr',
                                      'TEST-AAI' : 'true'})
        self.assertEquals(response.status_code, 204)
        self.assertNotEqual(response['X-Auth-Token'], None)
        self.assertEquals(response['X-Server-Management-Url'], '')
        self.assertEquals(response['X-Storage-Url'], '')
        self.assertEquals(response['X-CDN-Management-Url'], '')

    def test_unauthorized_call(self):
        request = {'reboot': {'type': 'HARD'}}
        path = '/api/v1.1/servers/%d/action' % 1
        response = self.client.post(path, json.dumps(request), content_type='application/json')
        self.assertEquals(response.status_code, 401)


class ListNetworks(BaseTestCase):
    SERVERS = 5
    NETWORKS = 5
    
    def setUp(self):
        BaseTestCase.setUp(self)
        machines = VirtualMachine.objects.all()
        for network in Network.objects.all():
            n = randint(0, self.SERVERS)
            network.machines.add(*sample(machines, n))
            network.save()
    
    def test_list_networks(self):
        networks = self.list_networks()
        for net in Network.objects.all():
            network = popdict(networks, id=net.id)
            self.assertEqual(network['name'], net.name)
        self.assertEqual(networks, [])
    
    def test_list_networks_detail(self):
        networks = self.list_networks(detail=True)
        for net in Network.objects.all():
            network = popdict(networks, id=net.id)
            self.assertEqual(network['name'], net.name)
            machines = set(vm.id for vm in net.machines.all())
            self.assertEqual(set(network['servers']['values']), machines)
        self.assertEqual(networks, [])


class CreateNetwork(BaseTestCase):
    def test_create_network(self):
        self.assertEqual(self.list_networks(), [])
        self.create_network('net')
        networks = self.list_networks()
        self.assertEqual(len(networks), 1)
        network = networks[0]
        self.assertEqual(network['name'], 'net')


class GetNetworkDetails(BaseTestCase):
    SERVERS = 5
    NETWORKS = 1
    
    def test_get_network_details(self):
        servers = VirtualMachine.objects.all()
        network = Network.objects.all()[0]
        
        net = self.get_network_details(network.id)
        self.assertEqual(net['name'], network.name)
        self.assertEqual(net['servers']['values'], [])
        
        server_id = choice(servers).id
        self.add_to_network(network.id, server_id)
        net = self.get_network_details(network.id)
        self.assertEqual(net['name'], network.name)
        self.assertEqual(net['servers']['values'], [server_id])


class UpdateNetworkName(BaseTestCase):
    NETWORKS = 5
    
    def test_update_network_name(self):
        networks = self.list_networks(detail=True)
        network = choice(networks)
        network_id = network['id']
        new_name = network['name'] + '_2'
        self.update_network_name(network_id, new_name)
        
        network['name'] = new_name
        self.assertEqual(self.get_network_details(network_id), network)


class DeleteNetwork(BaseTestCase):
    NETWORKS = 5
    
    def test_delete_network(self):
        networks = self.list_networks()
        network = choice(networks)
        network_id = network['id']
        self.delete_network(network_id)
        
        response = self.client.get('/api/v1.1/networks/%d' % network_id)
        self.assertItemNotFound(response)
        
        networks.remove(network)
        self.assertEqual(self.list_networks(), networks)


class NetworkActions(BaseTestCase):
    SERVERS = 20
    NETWORKS = 1
    
    def test_add_remove_server(self):
        server_ids = [vm.id for vm in VirtualMachine.objects.all()]
        network = self.list_networks(detail=True)[0]
        network_id = network['id']
        
        to_add = set(sample(server_ids, 10))
        for server_id in to_add:
            self.add_to_network(network_id, server_id)
            net = self.get_network_details(network_id)
            self.assertTrue(server_id in net['servers']['values'])
        
        net = self.get_network_details(network_id)
        self.assertEqual(set(net['servers']['values']), to_add)
        
        to_remove = set(sample(to_add, 5))
        for server_id in to_remove:
            self.remove_from_network(network_id, server_id)
            net = self.get_network_details(network_id)
            self.assertTrue(server_id not in net['servers']['values'])
        
        net = self.get_network_details(network_id)
        self.assertEqual(set(net['servers']['values']), to_add - to_remove)

