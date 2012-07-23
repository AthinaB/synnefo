# Copyright 2011-2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation are
# those of the authors and should not be interpreted as representing official
# policies, either expressed or implied, of GRNET S.A.

import datetime

from django.conf import settings
from django.db import models
from django.db import IntegrityError

from hashlib import sha1
from synnefo.api.faults import ServiceUnavailable
from synnefo.util.rapi import GanetiRapiClient
from synnefo.logic.ippool import IPPool
from synnefo import settings as snf_settings
from aes_encrypt import encrypt_db_charfield, decrypt_db_charfield

BACKEND_CLIENTS = {}  # {hash:Backend client}
BACKEND_HASHES = {}   # {Backend.id:hash}


def get_client(hash, backend):
    """Get a cached backend client or create a new one.

    @param hash: The hash of the backend
    @param backend: Either a backend object or backend ID
    """

    if backend is None:
        raise Exception("Backend is None. Cannot create a client.")

    if hash in BACKEND_CLIENTS:
        # Return cached client
        return BACKEND_CLIENTS[hash]

    # Always get a new instance to ensure latest credentials
    if isinstance(backend, Backend):
        backend = backend.id

    backend = Backend.objects.get(id=backend)
    hash = backend.hash
    clustername = backend.clustername
    port = backend.port
    user = backend.username
    password = backend.password

    # Check client for updated hash
    if hash in BACKEND_CLIENTS:
        return BACKEND_CLIENTS[hash]

    # Delete old version of the client
    if backend in BACKEND_HASHES:
        del BACKEND_CLIENTS[BACKEND_HASHES[backend]]

    # Create the new client
    client = GanetiRapiClient(clustername, port, user, password)

    # Store the client and the hash
    BACKEND_CLIENTS[hash] = client
    BACKEND_HASHES[backend] = hash

    return client


def clear_client_cache():
    BACKEND_CLIENTS.clear()
    BACKEND_HASHES.clear()


class Flavor(models.Model):
    cpu = models.IntegerField('Number of CPUs', default=0)
    ram = models.IntegerField('RAM size in MiB', default=0)
    disk = models.IntegerField('Disk size in GiB', default=0)
    disk_template = models.CharField('Disk template', max_length=32,
            default=settings.DEFAULT_GANETI_DISK_TEMPLATE)
    deleted = models.BooleanField('Deleted', default=False)

    class Meta:
        verbose_name = u'Virtual machine flavor'
        unique_together = ('cpu', 'ram', 'disk', 'disk_template')

    @property
    def name(self):
        """Returns flavor name (generated)"""
        return u'C%dR%dD%d' % (self.cpu, self.ram, self.disk)

    def __unicode__(self):
        return self.name


class BackendQuerySet(models.query.QuerySet):
    def delete(self):
        for backend in self._clone():
            backend.delete()


class ProtectDeleteManager(models.Manager):
    def get_query_set(self):
        return BackendQuerySet(self.model, using=self._db)


class Backend(models.Model):
    clustername = models.CharField('Cluster Name', max_length=128, unique=True)
    port = models.PositiveIntegerField('Port', default=5080)
    username = models.CharField('Username', max_length=64, blank=True,
                                null=True)
    password_hash = models.CharField('Password', max_length=64, blank=True,
                                null=True)
    # Sha1 is up to 40 characters long
    hash = models.CharField('Hash', max_length=40, editable=False, null=False)
    drained = models.BooleanField('Drained', default=False, null=False)
    offline = models.BooleanField('Offline', default=False, null=False)
    # Last refresh of backend resources
    updated = models.DateTimeField(auto_now_add=True)
    # Backend resources
    mfree = models.PositiveIntegerField('Free Memory', default=0, null=False)
    mtotal = models.PositiveIntegerField('Total Memory', default=0, null=False)
    dfree = models.PositiveIntegerField('Free Disk', default=0, null=False)
    dtotal = models.PositiveIntegerField('Total Disk', default=0, null=False)
    pinst_cnt = models.PositiveIntegerField('Primary Instances', default=0,
                                            null=False)
    ctotal = models.PositiveIntegerField('Total number of logical processors',
                                         default=0, null=False)
    # Custom object manager to protect from cascade delete
    objects = ProtectDeleteManager()

    class Meta:
        verbose_name = u'Backend'
        ordering = ["clustername"]

    def __unicode__(self):
        return self.clustername

    @property
    def backend_id(self):
        return self.id

    @property
    def client(self):
        """Get or create a client. """
        if not self.offline:
            return get_client(self.hash, self)
        else:
            raise ServiceUnavailable

    def create_hash(self):
        """Create a hash for this backend. """
        return sha1('%s%s%s%s' % \
                (self.clustername, self.port, self.username, self.password)) \
                .hexdigest()

    @property
    def password(self):
        return decrypt_db_charfield(self.password_hash)

    @password.setter
    def password(self, value):
        self.password_hash = encrypt_db_charfield(value)

    def save(self, *args, **kwargs):
        # Create a new hash each time a Backend is saved
        old_hash = self.hash
        self.hash = self.create_hash()
        super(Backend, self).save(*args, **kwargs)
        if self.hash != old_hash:
            # Populate the new hash to the new instances
            self.virtual_machines.filter(deleted=False).update(backend_hash=self.hash)

    def delete(self, *args, **kwargs):
        # Integrity Error if non-deleted VMs are associated with Backend
        if self.virtual_machines.filter(deleted=False).count():
            raise IntegrityError("Non-deleted virtual machines are associated "
                                 "with backend: %s" % self)
        else:
            # ON_DELETE = SET NULL
            self.virtual_machines.all().backend = None
            super(Backend, self).delete(*args, **kwargs)


# A backend job may be in one of the following possible states
BACKEND_STATUSES = (
    ('queued', 'request queued'),
    ('waiting', 'request waiting for locks'),
    ('canceling', 'request being canceled'),
    ('running', 'request running'),
    ('canceled', 'request canceled'),
    ('success', 'request completed successfully'),
    ('error', 'request returned error')
)


class VirtualMachine(models.Model):
    # The list of possible actions for a VM
    ACTIONS = (
       ('CREATE', 'Create VM'),
       ('START', 'Start VM'),
       ('STOP', 'Shutdown VM'),
       ('SUSPEND', 'Admin Suspend VM'),
       ('REBOOT', 'Reboot VM'),
       ('DESTROY', 'Destroy VM')
    )

    # The internal operating state of a VM
    OPER_STATES = (
        ('BUILD', 'Queued for creation'),
        ('ERROR', 'Creation failed'),
        ('STOPPED', 'Stopped'),
        ('STARTED', 'Started'),
        ('DESTROYED', 'Destroyed')
    )

    # The list of possible operations on the backend
    BACKEND_OPCODES = (
        ('OP_INSTANCE_CREATE', 'Create Instance'),
        ('OP_INSTANCE_REMOVE', 'Remove Instance'),
        ('OP_INSTANCE_STARTUP', 'Startup Instance'),
        ('OP_INSTANCE_SHUTDOWN', 'Shutdown Instance'),
        ('OP_INSTANCE_REBOOT', 'Reboot Instance'),

        # These are listed here for completeness,
        # and are ignored for the time being
        ('OP_INSTANCE_SET_PARAMS', 'Set Instance Parameters'),
        ('OP_INSTANCE_QUERY_DATA', 'Query Instance Data'),
        ('OP_INSTANCE_REINSTALL', 'Reinstall Instance'),
        ('OP_INSTANCE_ACTIVATE_DISKS', 'Activate Disks'),
        ('OP_INSTANCE_DEACTIVATE_DISKS', 'Deactivate Disks'),
        ('OP_INSTANCE_REPLACE_DISKS', 'Replace Disks'),
        ('OP_INSTANCE_MIGRATE', 'Migrate Instance'),
        ('OP_INSTANCE_CONSOLE', 'Get Instance Console'),
        ('OP_INSTANCE_RECREATE_DISKS', 'Recreate Disks'),
        ('OP_INSTANCE_FAILOVER', 'Failover Instance')
    )


    # The operating state of a VM,
    # upon the successful completion of a backend operation.
    # IMPORTANT: Make sure all keys have a corresponding
    # entry in BACKEND_OPCODES if you update this field, see #1035, #1111.
    OPER_STATE_FROM_OPCODE = {
        'OP_INSTANCE_CREATE': 'STARTED',
        'OP_INSTANCE_REMOVE': 'DESTROYED',
        'OP_INSTANCE_STARTUP': 'STARTED',
        'OP_INSTANCE_SHUTDOWN': 'STOPPED',
        'OP_INSTANCE_REBOOT': 'STARTED',
        'OP_INSTANCE_SET_PARAMS': None,
        'OP_INSTANCE_QUERY_DATA': None,
        'OP_INSTANCE_REINSTALL': None,
        'OP_INSTANCE_ACTIVATE_DISKS': None,
        'OP_INSTANCE_DEACTIVATE_DISKS': None,
        'OP_INSTANCE_REPLACE_DISKS': None,
        'OP_INSTANCE_MIGRATE': None,
        'OP_INSTANCE_CONSOLE': None,
        'OP_INSTANCE_RECREATE_DISKS': None,
        'OP_INSTANCE_FAILOVER': None
    }

    # This dictionary contains the correspondence between
    # internal operating states and Server States as defined
    # by the Rackspace API.
    RSAPI_STATE_FROM_OPER_STATE = {
        "BUILD": "BUILD",
        "ERROR": "ERROR",
        "STOPPED": "STOPPED",
        "STARTED": "ACTIVE",
        "DESTROYED": "DELETED"
    }

    name = models.CharField('Virtual Machine Name', max_length=255)
    userid = models.CharField('User ID of the owner', max_length=100)
    backend = models.ForeignKey(Backend, null=True,
                                related_name="virtual_machines",)
    backend_hash = models.CharField(max_length=128, null=True, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    imageid = models.CharField(max_length=100, null=False)
    hostid = models.CharField(max_length=100)
    flavor = models.ForeignKey(Flavor)
    deleted = models.BooleanField('Deleted', default=False)
    suspended = models.BooleanField('Administratively Suspended',
                                    default=False)

    # VM State
    # The following fields are volatile data, in the sense
    # that they need not be persistent in the DB, but rather
    # get generated at runtime by quering Ganeti and applying
    # updates received from Ganeti.

    # In the future they could be moved to a separate caching layer
    # and removed from the database.
    # [vkoukis] after discussion with [faidon].
    action = models.CharField(choices=ACTIONS, max_length=30, null=True)
    operstate = models.CharField(choices=OPER_STATES, max_length=30, null=True)
    backendjobid = models.PositiveIntegerField(null=True)
    backendopcode = models.CharField(choices=BACKEND_OPCODES, max_length=30,
                                     null=True)
    backendjobstatus = models.CharField(choices=BACKEND_STATUSES,
                                        max_length=30, null=True)
    backendlogmsg = models.TextField(null=True)
    buildpercentage = models.IntegerField(default=0)
    backendtime = models.DateTimeField(default=datetime.datetime.min)

    @property
    def client(self):
        if self.backend and not self.backend.offline:
            return get_client(self.backend_hash, self.backend_id)
        else:
            raise ServiceUnavailable

    # Error classes
    class InvalidBackendIdError(Exception):
        def __init__(self, value):
            self.value = value

        def __str__(self):
            return repr(self.value)

    class InvalidBackendMsgError(Exception):
        def __init__(self, opcode, status):
            self.opcode = opcode
            self.status = status

        def __str__(self):
            return repr('<opcode: %s, status: %s>' % (self.opcode,
                        self.status))

    class InvalidActionError(Exception):
        def __init__(self, action):
            self._action = action

        def __str__(self):
            return repr(str(self._action))

    class DeletedError(Exception):
        pass

    class BuildingError(Exception):
        pass

    def __init__(self, *args, **kw):
        """Initialize state for just created VM instances."""
        super(VirtualMachine, self).__init__(*args, **kw)
        # This gets called BEFORE an instance gets save()d for
        # the first time.
        if not self.pk:
            self.action = None
            self.backendjobid = None
            self.backendjobstatus = None
            self.backendopcode = None
            self.backendlogmsg = None
            self.operstate = 'BUILD'

    def save(self, *args, **kwargs):
        # Store hash for first time saved vm
        if (self.id is None or self.backend_hash == '') and self.backend:
            self.backend_hash = self.backend.hash
        super(VirtualMachine, self).save(*args, **kwargs)

    @property
    def backend_vm_id(self):
        """Returns the backend id for this VM by prepending backend-prefix."""
        if not self.id:
            raise VirtualMachine.InvalidBackendIdError("self.id is None")
        return "%s%s" % (settings.BACKEND_PREFIX_ID, str(self.id))

    class Meta:
        verbose_name = u'Virtual machine instance'
        get_latest_by = 'created'

    def __unicode__(self):
        return self.name


class VirtualMachineMetadata(models.Model):
    meta_key = models.CharField(max_length=50)
    meta_value = models.CharField(max_length=500)
    vm = models.ForeignKey(VirtualMachine, related_name='metadata')

    class Meta:
        unique_together = (('meta_key', 'vm'),)
        verbose_name = u'Key-value pair of metadata for a VM.'

    def __unicode__(self):
        return u'%s: %s' % (self.meta_key, self.meta_value)


class Network(models.Model):
    OPER_STATES = (
        ('PENDING', 'Pending'),
        ('ACTIVE', 'Active'),
        ('DELETED', 'Deleted'),
        ('ERROR', 'Error')
    )

    ACTIONS = (
       ('CREATE', 'Create Network'),
       ('DESTROY', 'Destroy Network'),
    )

    RSAPI_STATE_FROM_OPER_STATE = {
        'PENDING': 'PENDING',
        'ACTIVE': 'ACTIVE',
        'DELETED': 'DELETED',
        'ERROR': 'ERROR'
    }

    NETWORK_TYPES = (
        ('PUBLIC_ROUTED', 'Public routed network'),
        ('PRIVATE_PHYSICAL_VLAN', 'Private vlan network'),
        ('PRIVATE_MAC_FILTERED', 'Private network with mac-filtering'),
        ('CUSTOM_ROUTED', 'Custom routed network'),
        ('CUSTOM_BRIDGED', 'Custom bridged network')
    )

    name = models.CharField('Network Name', max_length=128)
    userid = models.CharField('User ID of the owner', max_length=128, null=True)
    subnet = models.CharField('Subnet', max_length=32, default='10.0.0.0/24')
    subnet6 = models.CharField('IPv6 Subnet', max_length=64, null=True)
    gateway = models.CharField('Gateway', max_length=32, null=True)
    gateway6 = models.CharField('IPv6 Gateway', max_length=64, null=True)
    dhcp = models.BooleanField('DHCP', default=True)
    type = models.CharField(choices=NETWORK_TYPES, max_length=50,
                            default='PRIVATE_PHYSICAL_VLAN')
    link = models.CharField('Network Link', max_length=128, null=True)
    mac_prefix = models.CharField('MAC Prefix', max_length=32, null=True)
    public = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField('Deleted', default=False)
    state = models.CharField(choices=OPER_STATES, max_length=32,
                             default='PENDING')
    machines = models.ManyToManyField(VirtualMachine,
                                      through='NetworkInterface')
    action = models.CharField(choices=ACTIONS, max_length=32, null=True,
                              default=None)

    reservations = models.TextField(default='')

    ip_pool = None


    class InvalidBackendIdError(Exception):
        def __init__(self, value):
            self.value = value

        def __str__(self):
            return repr(self.value)


    class InvalidBackendMsgError(Exception):
        def __init__(self, opcode, status):
            self.opcode = opcode
            self.status = status

        def __str__(self):
            return repr('<opcode: %s, status: %s>' % (self.opcode,
                    self.status))

    class InvalidActionError(Exception):
        def __init__(self, action):
            self._action = action

        def __str__(self):
            return repr(str(self._action))

    @property
    def backend_id(self):
        """Return the backend id by prepending backend-prefix."""
        if not self.id:
            raise Network.InvalidBackendIdError("self.id is None")
        return "%snet-%s" % (settings.BACKEND_PREFIX_ID, str(self.id))

    @property
    def backend_tag(self):
        """Return the network tag to be used in backend

        """
        return getattr(snf_settings, self.type + '_TAGS')

    def __unicode__(self):
        return self.name

    def update_state(self):
        """Update state of the Network.

        Update the state of the Network depending on the related
        backend_networks. When backend networks do not have the same operstate,
        the Network's state is PENDING. Otherwise it is the same with
        the BackendNetworks operstate.

        """
        backend_states = [s.operstate for s in self.backend_networks.all()]
        if not backend_states:
            self.state = 'PENDING'
            self.save()
            return

        all_equal = len(set(backend_states)) <= 1
        self.state = all_equal and backend_states[0] or 'PENDING'

        if self.state == 'DELETED':
            self.deleted = True

            if self.mac_prefix:
                MacPrefixPool.set_available(self.mac_prefix)

            if self.link and self.type == 'PRIVATE_VLAN':
                BridgePool.set_available(self.link)

        self.save()

    def save(self, *args, **kwargs):
        pk = self.pk
        super(Network, self).save(*args, **kwargs)
        if not pk:
            # In case of a new Network, corresponding BackendNetwork's must
            # be created!
            for back in Backend.objects.all():
                BackendNetwork.objects.create(backend=back, network=self)

    @property
    def pool(self):
        if self.ip_pool:
            return self.ip_pool
        else:
            self.ip_pool = IPPool(self)
            return self.ip_pool

    def reserve_address(self, address, pool=None):
        pool = pool or self.pool
        pool.reserve(address)
        pool._update_network()
        self.save()

    def release_address(self, address, pool=None):
        pool = pool or self.pool
        pool.release(address)
        pool._update_network()
        self.save()

    # def get_free_address(self):
    #     # Get yourself inside a transaction
    #     network = Network.objects.get(id=self.id)
    #     # Get the pool object
    #     pool = network.pool
    #     print network is self
    #     try:
    #         address = pool.get_free_address()
    #     except IPPoolExhausted:
    #         raise Network.NetworkIsFull

    #     pool._update_network()
    #     network.save()
    #     return address

    # class NetworkIsFull(Exception):
    #     pass


class BackendNetwork(models.Model):
    OPER_STATES = (
        ('PENDING', 'Pending'),
        ('ACTIVE', 'Active'),
        ('DELETED', 'Deleted'),
        ('ERROR', 'Error')
    )

    # The list of possible operations on the backend
    BACKEND_OPCODES = (
        ('OP_NETWORK_ADD', 'Create Network'),
        ('OP_NETWORK_CONNECT', 'Activate Network'),
        ('OP_NETWORK_DISCONNECT', 'Deactivate Network'),
        ('OP_NETWORK_REMOVE', 'Remove Network'),
        # These are listed here for completeness,
        # and are ignored for the time being
        ('OP_NETWORK_SET_PARAMS', 'Set Network Parameters'),
        ('OP_NETWORK_QUERY_DATA', 'Query Network Data')
    )

    # The operating state of a Netowork,
    # upon the successful completion of a backend operation.
    # IMPORTANT: Make sure all keys have a corresponding
    # entry in BACKEND_OPCODES if you update this field, see #1035, #1111.
    OPER_STATE_FROM_OPCODE = {
        'OP_NETWORK_ADD': 'PENDING',
        'OP_NETWORK_CONNECT': 'ACTIVE',
        'OP_NETWORK_DISCONNECT': 'PENDING',
        'OP_NETWORK_REMOVE': 'DELETED',
        'OP_NETWORK_SET_PARAMS': None,
        'OP_NETWORK_QUERY_DATA': None
    }

    network = models.ForeignKey(Network, related_name='backend_networks')
    backend = models.ForeignKey(Backend, related_name='networks')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    deleted = models.BooleanField('Deleted', default=False)
    operstate = models.CharField(choices=OPER_STATES, max_length=30,
                                 default='PENDING')
    backendjobid = models.PositiveIntegerField(null=True)
    backendopcode = models.CharField(choices=BACKEND_OPCODES, max_length=30,
                                     null=True)
    backendjobstatus = models.CharField(choices=BACKEND_STATUSES,
                                        max_length=30, null=True)
    backendlogmsg = models.TextField(null=True)
    backendtime = models.DateTimeField(null=False,
                                       default=datetime.datetime.min)

    def save(self, *args, **kwargs):
        super(BackendNetwork, self).save(*args, **kwargs)
        self.network.update_state()

    def delete(self, *args, **kwargs):
        super(BackendNetwork, self).delete(*args, **kwargs)
        self.network.update_state()


class NetworkInterface(models.Model):
    FIREWALL_PROFILES = (
        ('ENABLED', 'Enabled'),
        ('DISABLED', 'Disabled'),
        ('PROTECTED', 'Protected')
    )

    machine = models.ForeignKey(VirtualMachine, related_name='nics')
    network = models.ForeignKey(Network, related_name='nics')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    index = models.IntegerField(null=False)
    mac = models.CharField(max_length=32, null=True)
    ipv4 = models.CharField(max_length=15, null=True)
    ipv6 = models.CharField(max_length=100, null=True)
    firewall_profile = models.CharField(choices=FIREWALL_PROFILES,
                                        max_length=30, null=True)
    dirty = models.BooleanField(default=False)

    def __unicode__(self):
        return '%s@%s' % (self.machine.name, self.network.name)


class Pool(models.Model):
    available = models.BooleanField(default=True, null=False)
    index = models.IntegerField(null=False, unique=True)
    value = models.CharField(max_length=128, null=False, unique=True)
    max_index = 0

    class Meta:
        abstract = True
        ordering = ['index']

    @classmethod
    def get_available(cls):
        try:
            entry = cls.objects.filter(available=True)[0]
            entry.available = False
            entry.save()
            return entry
        except IndexError:
            return cls.generate_new()

    @classmethod
    def generate_new(cls):
        try:
            last = cls.objects.order_by('-index')[0]
            index = last.index + 1
        except IndexError:
            index = 1

        if index <= cls.max_index:
            return cls.objects.create(index=index,
                                      value=cls.value_from_index(index),
                                      available=False)

        raise Pool.PoolExhausted()

    @classmethod
    def set_available(cls, value):
        entry = cls.objects.get(value=value)
        entry.available = True
        entry.save()


    class PoolExhausted(Exception):
        pass


class BridgePool(Pool):
    max_index = snf_settings.PRIVATE_PHYSICAL_VLAN_MAX_NUMBER

    @staticmethod
    def value_from_index(index):
        return snf_settings.PRIVATE_PHYSICAL_VLAN_BRIDGE_PREFIX + str(index)


class MacPrefixPool(Pool):
    max_index = snf_settings.PRIVATE_MAC_FILTERED_MAX_PREFIX_NUMBER

    @staticmethod
    def value_from_index(index):
        """Convert number to mac prefix

        """
        high = snf_settings.PRIVATE_MAC_FILTERED_BASE_MAC_PREFIX
        a = hex(int(high.replace(":", ""), 16) + index).replace("0x", '')
        mac_prefix = ":".join([a[x:x + 2] for x in xrange(0, len(a), 2)])
        return mac_prefix
