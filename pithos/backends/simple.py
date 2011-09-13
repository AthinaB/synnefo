# Copyright 2011 GRNET S.A. All rights reserved.
# 
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
# 
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# 
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

import os
import time
import sqlite3
import logging
import hashlib
import binascii

from base import NotAllowedError, BaseBackend
from lib.hashfiler import Mapper, Blocker
from django.utils.encoding import smart_unicode, smart_str

logger = logging.getLogger(__name__)

def backend_method(func=None, autocommit=1):
    if func is None:
        def fn(func):
            return backend_method(func, autocommit)
        return fn

    if not autocommit:
        return func
    def fn(self, *args, **kw):
        self.con.execute('begin deferred')
        try:
            ret = func(self, *args, **kw)
            self.con.commit()
            return ret
        except:
            self.con.rollback()
            raise
    return fn


class SimpleBackend(BaseBackend):
    """A simple backend.
    
    Uses SQLite for storage.
    """
    
    # TODO: Create account if not present in all functions.
    
    def __init__(self, path, db):
        self.hash_algorithm = 'sha256'
        self.block_size = 4 * 1024 * 1024 # 4MB
        
        self.default_policy = {'quota': 0, 'versioning': 'auto'}
        
        if path and not os.path.exists(path):
            os.makedirs(path)
        if not os.path.isdir(path):
            raise RuntimeError("Cannot open path '%s'" % (path,))
        
        self.con = sqlite3.connect(db, check_same_thread=False)
        
        sql = '''pragma foreign_keys = on'''
        self.con.execute(sql)
        
        sql = '''create table if not exists versions (
                    version_id integer primary key,
                    name text,
                    user text,
                    tstamp integer not null,
                    size integer default 0,
                    hide integer default 0)'''
        self.con.execute(sql)
        sql = '''create table if not exists metadata (
                    version_id integer,
                    key text,
                    value text,
                    primary key (version_id, key)
                    foreign key (version_id) references versions(version_id)
                    on delete cascade)'''
        self.con.execute(sql)
        sql = '''create table if not exists policy (
                    name text, key text, value text, primary key (name, key))'''
        self.con.execute(sql)
        
        # Access control tables.
        sql = '''create table if not exists groups (
                    account text, gname text, user text)'''
        self.con.execute(sql)
        sql = '''create table if not exists permissions (
                    name text, op text, user text)'''
        self.con.execute(sql)
        sql = '''create table if not exists public (
                    name text, primary key (name))'''
        self.con.execute(sql)
        
        self.con.commit()
        
        params = {'blocksize': self.block_size,
                  'blockpath': os.path.join(path + '/blocks'),
                  'hashtype': self.hash_algorithm}
        self.blocker = Blocker(**params)
        
        params = {'mappath': os.path.join(path + '/maps'),
                  'namelen': self.blocker.hashlen}
        self.mapper = Mapper(**params)
    
    @backend_method
    def list_accounts(self, user, marker=None, limit=10000):
        """Return a list of accounts the user can access."""
        
        allowed = self._allowed_accounts(user)
        start, limit = self._list_limits(allowed, marker, limit)
        return allowed[start:start + limit]
    
    @backend_method
    def get_account_meta(self, user, account, until=None):
        """Return a dictionary with the account metadata."""
        
        logger.debug("get_account_meta: %s %s", account, until)
        if user != account:
            if until or account not in self._allowed_accounts(user):
                raise NotAllowedError
        else:
            self._create_account(user, account)
        try:
            version_id, mtime = self._get_accountinfo(account, until)
        except NameError:
            # Account does not exist before until.
            version_id = None
            mtime = until
        count, bytes, tstamp = self._get_pathstats(account, until)
        if mtime > tstamp:
            tstamp = mtime
        if until is None:
            modified = tstamp
        else:
            modified = self._get_pathstats(account)[2] # Overall last modification
            if mtime > modified:
                modified = mtime
        
        # Proper count.
        sql = 'select count(name) from (%s) where name glob ? and not name glob ?'
        sql = sql % self._sql_until(until)
        c = self.con.execute(sql, (account + '/*', account + '/*/*'))
        row = c.fetchone()
        count = row[0]
        
        if user != account:
            meta = {'name': account}
        else:
            meta = self._get_metadata(account, version_id)
            meta.update({'name': account, 'count': count, 'bytes': bytes})
            if until is not None:
                meta.update({'until_timestamp': tstamp})
        meta.update({'modified': modified})
        return meta
    
    @backend_method
    def update_account_meta(self, user, account, meta, replace=False):
        """Update the metadata associated with the account."""
        
        logger.debug("update_account_meta: %s %s %s", account, meta, replace)
        if user != account:
            raise NotAllowedError
        self._put_metadata(user, account, meta, replace, False)
    
    @backend_method
    def get_account_groups(self, user, account):
        """Return a dictionary with the user groups defined for this account."""
        
        logger.debug("get_account_groups: %s", account)
        if user != account:
            if account not in self._allowed_accounts(user):
                raise NotAllowedError
            return {}
        self._create_account(user, account)
        return self._get_groups(account)
    
    @backend_method
    def update_account_groups(self, user, account, groups, replace=False):
        """Update the groups associated with the account."""
        
        logger.debug("update_account_groups: %s %s %s", account, groups, replace)
        if user != account:
            raise NotAllowedError
        self._create_account(user, account)
        self._check_groups(groups)
        self._put_groups(account, groups, replace)
    
    @backend_method
    def put_account(self, user, account):
        """Create a new account with the given name."""
        
        logger.debug("put_account: %s", account)
        if user != account:
            raise NotAllowedError
        try:
            version_id, mtime = self._get_accountinfo(account)
        except NameError:
            pass
        else:
            raise NameError('Account already exists')
        self._put_version(account, user)
    
    @backend_method
    def delete_account(self, user, account):
        """Delete the account with the given name."""
        
        logger.debug("delete_account: %s", account)
        if user != account:
            raise NotAllowedError
        count = self._get_pathstats(account)[0]
        if count > 0:
            raise IndexError('Account is not empty')
        sql = 'delete from versions where name = ?'
        self.con.execute(sql, (account,))
        self._del_groups(account)
    
    @backend_method
    def list_containers(self, user, account, marker=None, limit=10000, shared=False, until=None):
        """Return a list of containers existing under an account."""
        
        logger.debug("list_containers: %s %s %s %s", account, marker, limit, until)
        if user != account:
            if until or account not in self._allowed_accounts(user):
                raise NotAllowedError
            allowed = self._allowed_containers(user, account)
            start, limit = self._list_limits(allowed, marker, limit)
            return allowed[start:start + limit]
        else:
            if shared:
                allowed = [x.split('/', 2)[1] for x in self._shared_paths(account)]
                start, limit = self._list_limits(allowed, marker, limit)
                return allowed[start:start + limit]
        return [x[0] for x in self._list_objects(account, '', '/', marker, limit, False, [], until)]
    
    @backend_method
    def get_container_meta(self, user, account, container, until=None):
        """Return a dictionary with the container metadata."""
        
        logger.debug("get_container_meta: %s %s %s", account, container, until)
        if user != account:
            if until or container not in self._allowed_containers(user, account):
                raise NotAllowedError
        path, version_id, mtime = self._get_containerinfo(account, container, until)
        count, bytes, tstamp = self._get_pathstats(path, until)
        if mtime > tstamp:
            tstamp = mtime
        if until is None:
            modified = tstamp
        else:
            modified = self._get_pathstats(path)[2] # Overall last modification
            if mtime > modified:
                modified = mtime
        
        if user != account:
            meta = {'name': container, 'modified': modified}
        else:
            meta = self._get_metadata(path, version_id)
            meta.update({'name': container, 'count': count, 'bytes': bytes, 'modified': modified})
            if until is not None:
                meta.update({'until_timestamp': tstamp})
        return meta
    
    @backend_method
    def update_container_meta(self, user, account, container, meta, replace=False):
        """Update the metadata associated with the container."""
        
        logger.debug("update_container_meta: %s %s %s %s", account, container, meta, replace)
        if user != account:
            raise NotAllowedError
        path, version_id, mtime = self._get_containerinfo(account, container)
        self._put_metadata(user, path, meta, replace, False)
    
    @backend_method
    def get_container_policy(self, user, account, container):
        """Return a dictionary with the container policy."""
        
        logger.debug("get_container_policy: %s %s", account, container)
        if user != account:
            if container not in self._allowed_containers(user, account):
                raise NotAllowedError
            return {}
        path = self._get_containerinfo(account, container)[0]
        return self._get_policy(path)
    
    @backend_method
    def update_container_policy(self, user, account, container, policy, replace=False):
        """Update the policy associated with the account."""
        
        logger.debug("update_container_policy: %s %s %s %s", account, container, policy, replace)
        if user != account:
            raise NotAllowedError
        path = self._get_containerinfo(account, container)[0]
        self._check_policy(policy)
        if replace:
            for k, v in self.default_policy.iteritems():
                if k not in policy:
                    policy[k] = v
        for k, v in policy.iteritems():
            sql = 'insert or replace into policy (name, key, value) values (?, ?, ?)'
            self.con.execute(sql, (path, k, v))
    
    @backend_method
    def put_container(self, user, account, container, policy=None):
        """Create a new container with the given name."""
        
        logger.debug("put_container: %s %s %s", account, container, policy)
        if user != account:
            raise NotAllowedError
        try:
            path, version_id, mtime = self._get_containerinfo(account, container)
        except NameError:
            pass
        else:
            raise NameError('Container already exists')
        if policy:
            self._check_policy(policy)
        path = '/'.join((account, container))
        version_id = self._put_version(path, user)[0]
        for k, v in self.default_policy.iteritems():
            if k not in policy:
                policy[k] = v
        for k, v in policy.iteritems():
            sql = 'insert or replace into policy (name, key, value) values (?, ?, ?)'
            self.con.execute(sql, (path, k, v))
    
    @backend_method
    def delete_container(self, user, account, container, until=None):
        """Delete/purge the container with the given name."""
        
        logger.debug("delete_container: %s %s %s", account, container, until)
        if user != account:
            raise NotAllowedError
        path, version_id, mtime = self._get_containerinfo(account, container)
        
        if until is not None:
            sql = '''select version_id from versions where name like ? and tstamp <= ?
                        and version_id not in (select version_id from (%s))'''
            sql = sql % self._sql_until() # Do not delete current versions.
            c = self.con.execute(sql, (path + '/%', until))
            for v in [x[0] for x in c.fetchall()]:
                self._del_version(v)
            return
        
        count = self._get_pathstats(path)[0]
        if count > 0:
            raise IndexError('Container is not empty')
        sql = 'delete from versions where name = ? or name like ?' # May contain hidden items.
        self.con.execute(sql, (path, path + '/%',))
        sql = 'delete from policy where name = ?'
        self.con.execute(sql, (path,))
        self._copy_version(user, account, account, True, False) # New account version (for timestamp update).
    
    @backend_method
    def list_objects(self, user, account, container, prefix='', delimiter=None, marker=None, limit=10000, virtual=True, keys=[], shared=False, until=None):
        """Return a list of objects existing under a container."""
        
        logger.debug("list_objects: %s %s %s %s %s %s %s %s %s %s", account, container, prefix, delimiter, marker, limit, virtual, keys, shared, until)
        allowed = []
        if user != account:
            if until:
                raise NotAllowedError
            allowed = self._allowed_paths(user, '/'.join((account, container)))
            if not allowed:
                raise NotAllowedError
        else:
            if shared:
                allowed = self._shared_paths('/'.join((account, container)))
        path, version_id, mtime = self._get_containerinfo(account, container, until)
        return self._list_objects(path, prefix, delimiter, marker, limit, virtual, keys, until, allowed)
    
    @backend_method
    def list_object_meta(self, user, account, container, until=None):
        """Return a list with all the container's object meta keys."""
        
        logger.debug("list_object_meta: %s %s %s", account, container, until)
        allowed = []
        if user != account:
            if until:
                raise NotAllowedError
            allowed = self._allowed_paths(user, '/'.join((account, container)))
            if not allowed:
                raise NotAllowedError
        path, version_id, mtime = self._get_containerinfo(account, container, until)
        sql = '''select distinct m.key from (%s) o, metadata m
                    where m.version_id = o.version_id and o.name like ?'''
        sql = sql % self._sql_until(until)
        param = (path + '/%',)
        if allowed:
            for x in allowed:
                sql += ' and o.name like ?'
                param += (x,)
        c = self.con.execute(sql, param)
        return [x[0] for x in c.fetchall()]
    
    @backend_method
    def get_object_meta(self, user, account, container, name, version=None):
        """Return a dictionary with the object metadata."""
        
        logger.debug("get_object_meta: %s %s %s %s", account, container, name, version)
        self._can_read(user, account, container, name)
        path, version_id, muser, mtime, size = self._get_objectinfo(account, container, name, version)
        if version is None:
            modified = mtime
        else:
            modified = self._get_version(path, version)[2] # Overall last modification
        
        meta = self._get_metadata(path, version_id)
        meta.update({'name': name, 'bytes': size})
        meta.update({'version': version_id, 'version_timestamp': mtime})
        meta.update({'modified': modified, 'modified_by': muser})
        return meta
    
    @backend_method
    def update_object_meta(self, user, account, container, name, meta, replace=False):
        """Update the metadata associated with the object."""
        
        logger.debug("update_object_meta: %s %s %s %s %s", account, container, name, meta, replace)
        self._can_write(user, account, container, name)
        path, version_id, muser, mtime, size = self._get_objectinfo(account, container, name)
        return self._put_metadata(user, path, meta, replace)
    
    @backend_method
    def get_object_permissions(self, user, account, container, name):
        """Return the action allowed on the object, the path
        from which the object gets its permissions from,
        along with a dictionary containing the permissions."""
        
        logger.debug("get_object_permissions: %s %s %s", account, container, name)
        allowed = 'write'
        if user != account:
            if self._is_allowed(user, account, container, name, 'write'):
                allowed = 'write'
            elif self._is_allowed(user, account, container, name, 'read'):
                allowed = 'read'
            else:
                raise NotAllowedError
        path = self._get_objectinfo(account, container, name)[0]
        return (allowed,) + self._get_permissions(path)
    
    @backend_method
    def update_object_permissions(self, user, account, container, name, permissions):
        """Update the permissions associated with the object."""
        
        logger.debug("update_object_permissions: %s %s %s %s", account, container, name, permissions)
        if user != account:
            raise NotAllowedError
        path = self._get_objectinfo(account, container, name)[0]
        r, w = self._check_permissions(path, permissions)
        self._put_permissions(path, r, w)
    
    @backend_method
    def get_object_public(self, user, account, container, name):
        """Return the public URL of the object if applicable."""
        
        logger.debug("get_object_public: %s %s %s", account, container, name)
        self._can_read(user, account, container, name)
        path = self._get_objectinfo(account, container, name)[0]
        if self._get_public(path):
            return '/public/' + path
        return None
    
    @backend_method
    def update_object_public(self, user, account, container, name, public):
        """Update the public status of the object."""
        
        logger.debug("update_object_public: %s %s %s %s", account, container, name, public)
        self._can_write(user, account, container, name)
        path = self._get_objectinfo(account, container, name)[0]
        self._put_public(path, public)
    
    @backend_method
    def get_object_hashmap(self, user, account, container, name, version=None):
        """Return the object's size and a list with partial hashes."""
        
        logger.debug("get_object_hashmap: %s %s %s %s", account, container, name, version)
        self._can_read(user, account, container, name)
        path, version_id, muser, mtime, size = self._get_objectinfo(account, container, name, version)
        hashmap = self.mapper.map_retr(version_id)
        return size, [binascii.hexlify(x) for x in hashmap]
    
    @backend_method
    def update_object_hashmap(self, user, account, container, name, size, hashmap, meta={}, replace_meta=False, permissions=None):
        """Create/update an object with the specified size and partial hashes."""
        
        logger.debug("update_object_hashmap: %s %s %s %s %s", account, container, name, size, hashmap)
        if permissions is not None and user != account:
            raise NotAllowedError
        self._can_write(user, account, container, name)
        missing = self.blocker.block_ping([binascii.unhexlify(x) for x in hashmap])
        if missing:
            ie = IndexError()
            ie.data = [binascii.hexlify(x) for x in missing]
            raise ie
        path = self._get_containerinfo(account, container)[0]
        path = '/'.join((path, name))
        if permissions is not None:
            r, w = self._check_permissions(path, permissions)
        src_version_id, dest_version_id = self._copy_version(user, path, path, not replace_meta, False)
        sql = 'update versions set size = ? where version_id = ?'
        self.con.execute(sql, (size, dest_version_id))
        self.mapper.map_stor(dest_version_id, [binascii.unhexlify(x) for x in hashmap])
        for k, v in meta.iteritems():
            sql = 'insert or replace into metadata (version_id, key, value) values (?, ?, ?)'
            self.con.execute(sql, (dest_version_id, k, v))
        if permissions is not None:
            self._put_permissions(path, r, w)
        return dest_version_id
    
    @backend_method
    def copy_object(self, user, account, src_container, src_name, dest_container, dest_name, dest_meta={}, replace_meta=False, permissions=None, src_version=None):
        """Copy an object's data and metadata."""
        
        logger.debug("copy_object: %s %s %s %s %s %s %s %s %s", account, src_container, src_name, dest_container, dest_name, dest_meta, replace_meta, permissions, src_version)
        if permissions is not None and user != account:
            raise NotAllowedError
        self._can_read(user, account, src_container, src_name)
        self._can_write(user, account, dest_container, dest_name)
        self._get_containerinfo(account, src_container)
        if src_version is None:
            src_path = self._get_objectinfo(account, src_container, src_name)[0]
        else:
            src_path = '/'.join((account, src_container, src_name))
        dest_path = self._get_containerinfo(account, dest_container)[0]
        dest_path = '/'.join((dest_path, dest_name))
        if permissions is not None:
            r, w = self._check_permissions(dest_path, permissions)
        src_version_id, dest_version_id = self._copy_version(user, src_path, dest_path, not replace_meta, True, src_version)
        for k, v in dest_meta.iteritems():
            sql = 'insert or replace into metadata (version_id, key, value) values (?, ?, ?)'
            self.con.execute(sql, (dest_version_id, k, v))
        if permissions is not None:
            self._put_permissions(dest_path, r, w)
        return dest_version_id
    
    @backend_method
    def move_object(self, user, account, src_container, src_name, dest_container, dest_name, dest_meta={}, replace_meta=False, permissions=None):
        """Move an object's data and metadata."""
        
        logger.debug("move_object: %s %s %s %s %s %s %s %s", account, src_container, src_name, dest_container, dest_name, dest_meta, replace_meta, permissions)
        dest_version_id = self.copy_object(user, account, src_container, src_name, dest_container, dest_name, dest_meta, replace_meta, permissions, None)
        self.delete_object(user, account, src_container, src_name)
        return dest_version_id
    
    @backend_method
    def delete_object(self, user, account, container, name, until=None):
        """Delete/purge an object."""
        
        logger.debug("delete_object: %s %s %s %s", account, container, name, until)
        if user != account:
            raise NotAllowedError
        
        if until is not None:
            path = '/'.join((account, container, name))
            sql = '''select version_id from versions where name = ? and tstamp <= ?'''
            c = self.con.execute(sql, (path, until))
            for v in [x[0] in c.fetchall()]:
                self._del_version(v)
            try:
                version_id = self._get_version(path)[0]
            except NameError:
                pass
            else:
                self._del_sharing(path)
            return
        
        path = self._get_objectinfo(account, container, name)[0]
        self._put_version(path, user, 0, 1)
        self._del_sharing(path)
    
    @backend_method
    def list_versions(self, user, account, container, name):
        """Return a list of all (version, version_timestamp) tuples for an object."""
        
        logger.debug("list_versions: %s %s %s", account, container, name)
        self._can_read(user, account, container, name)
        # This will even show deleted versions.
        path = '/'.join((account, container, name))
        sql = '''select distinct version_id, tstamp from versions where name = ? and hide = 0'''
        c = self.con.execute(sql, (path,))
        return [(int(x[0]), int(x[1])) for x in c.fetchall()]
    
    @backend_method(autocommit=0)
    def get_block(self, hash):
        """Return a block's data."""
        
        logger.debug("get_block: %s", hash)
        blocks = self.blocker.block_retr((binascii.unhexlify(hash),))
        if not blocks:
            raise NameError('Block does not exist')
        return blocks[0]
    
    @backend_method(autocommit=0)
    def put_block(self, data):
        """Store a block and return the hash."""
        
        logger.debug("put_block: %s", len(data))
        hashes, absent = self.blocker.block_stor((data,))
        return binascii.hexlify(hashes[0])
    
    @backend_method(autocommit=0)
    def update_block(self, hash, data, offset=0):
        """Update a known block and return the hash."""
        
        logger.debug("update_block: %s %s %s", hash, len(data), offset)
        if offset == 0 and len(data) == self.block_size:
            return self.put_block(data)
        h, e = self.blocker.block_delta(binascii.unhexlify(hash), ((offset, data),))
        return binascii.hexlify(h)
    
    def _sql_until(self, until=None):
        """Return the sql to get the latest versions until the timestamp given."""
        if until is None:
            until = int(time.time())
        sql = '''select version_id, name, tstamp, size from versions v
                    where version_id = (select max(version_id) from versions
                                        where v.name = name and tstamp <= %s)
                    and hide = 0'''
        return sql % (until,)
    
    def _get_pathstats(self, path, until=None):
        """Return count and sum of size of everything under path and latest timestamp."""
        
        sql = 'select count(version_id), total(size), max(tstamp) from (%s) where name like ?'
        sql = sql % self._sql_until(until)
        c = self.con.execute(sql, (path + '/%',))
        row = c.fetchone()
        tstamp = row[2] if row[2] is not None else 0
        return int(row[0]), int(row[1]), int(tstamp)
    
    def _get_version(self, path, version=None):
        if version is None:
            sql = '''select version_id, user, tstamp, size, hide from versions where name = ?
                        order by version_id desc limit 1'''
            c = self.con.execute(sql, (path,))
            row = c.fetchone()
            if not row or int(row[4]):
                raise NameError('Object does not exist')
        else:
            # The database (sqlite) will not complain if the version is not an integer.
            sql = '''select version_id, user, tstamp, size from versions where name = ?
                        and version_id = ?'''
            c = self.con.execute(sql, (path, version))
            row = c.fetchone()
            if not row:
                raise IndexError('Version does not exist')
        return smart_str(row[0]), smart_str(row[1]), int(row[2]), int(row[3])
    
    def _put_version(self, path, user, size=0, hide=0):
        tstamp = int(time.time())
        sql = 'insert into versions (name, user, tstamp, size, hide) values (?, ?, ?, ?, ?)'
        id = self.con.execute(sql, (path, user, tstamp, size, hide)).lastrowid
        return str(id), tstamp
    
    def _copy_version(self, user, src_path, dest_path, copy_meta=True, copy_data=True, src_version=None):
        if src_version is not None:
            src_version_id, muser, mtime, size = self._get_version(src_path, src_version)
        else:
            # Latest or create from scratch.
            try:
                src_version_id, muser, mtime, size = self._get_version(src_path)
            except NameError:
                src_version_id = None
                size = 0
        if not copy_data:
            size = 0
        dest_version_id = self._put_version(dest_path, user, size)[0]
        if copy_meta and src_version_id is not None:
            sql = 'insert into metadata select %s, key, value from metadata where version_id = ?'
            sql = sql % dest_version_id
            self.con.execute(sql, (src_version_id,))
        if copy_data and src_version_id is not None:
            # TODO: Copy properly.
            hashmap = self.mapper.map_retr(src_version_id)
            self.mapper.map_stor(dest_version_id, hashmap)
        return src_version_id, dest_version_id
    
    def _get_versioninfo(self, account, container, name, until=None):
        """Return path, latest version, associated timestamp and size until the timestamp given."""
        
        p = (account, container, name)
        try:
            p = p[:p.index(None)]
        except ValueError:
            pass
        path = '/'.join(p)
        sql = '''select version_id, tstamp, size from (%s) where name = ?'''
        sql = sql % self._sql_until(until)
        c = self.con.execute(sql, (path,))
        row = c.fetchone()
        if row is None:
            raise NameError('Path does not exist')
        return path, str(row[0]), int(row[1]), int(row[2])
    
    def _get_accountinfo(self, account, until=None):
        try:
            path, version_id, mtime, size = self._get_versioninfo(account, None, None, until)
            return version_id, mtime
        except:
            raise NameError('Account does not exist')
    
    def _get_containerinfo(self, account, container, until=None):
        try:
            path, version_id, mtime, size = self._get_versioninfo(account, container, None, until)
            return path, version_id, mtime
        except:
            raise NameError('Container does not exist')
    
    def _get_objectinfo(self, account, container, name, version=None):
        path = '/'.join((account, container, name))
        version_id, muser, mtime, size = self._get_version(path, version)
        return path, version_id, muser, mtime, size
    
    def _create_account(self, user, account):
        try:
            self._get_accountinfo(account)
        except NameError:
            self._put_version(account, user)
    
    def _get_metadata(self, path, version):
        sql = 'select key, value from metadata where version_id = ?'
        c = self.con.execute(sql, (version,))
        return dict(c.fetchall())
    
    def _put_metadata(self, user, path, meta, replace=False, copy_data=True):
        """Create a new version and store metadata."""
        
        src_version_id, dest_version_id = self._copy_version(user, path, path, not replace, copy_data)
        for k, v in meta.iteritems():
            if not replace and v == '':
                sql = 'delete from metadata where version_id = ? and key = ?'
                self.con.execute(sql, (dest_version_id, k))
            else:
                sql = 'insert or replace into metadata (version_id, key, value) values (?, ?, ?)'
                self.con.execute(sql, (dest_version_id, k, v))
        return dest_version_id
    
    def _check_policy(self, policy):
        for k in policy.keys():
            if policy[k] == '':
                policy[k] = self.default_policy.get(k)
        for k, v in policy.iteritems():
            if k == 'quota':
                q = int(v) # May raise ValueError.
                if q < 0:
                    raise ValueError
            elif k == 'versioning':
                if v not in ['auto', 'manual', 'none']:
                    raise ValueError
            else:
                raise ValueError
    
    def _get_policy(self, path):
        sql = 'select key, value from policy where name = ?'
        c = self.con.execute(sql, (path,))
        return dict(c.fetchall())
    
    def _list_limits(self, listing, marker, limit):
        start = 0
        if marker:
            try:
                start = listing.index(marker) + 1
            except ValueError:
                pass
        if not limit or limit > 10000:
            limit = 10000
        return start, limit
    
    def _list_objects(self, path, prefix='', delimiter=None, marker=None, limit=10000, virtual=True, keys=[], until=None, allowed=[]):
        cont_prefix = path + '/'
        if keys and len(keys) > 0:
            sql = '''select distinct o.name, o.version_id from (%s) o, metadata m where o.name like ? and
                        m.version_id = o.version_id and m.key in (%s)'''
            sql = sql % (self._sql_until(until), ', '.join('?' * len(keys)))
            param = (cont_prefix + prefix + '%',) + tuple(keys)
            if allowed:
                sql += ' and (' + ' or '.join(('o.name like ?',) * len(allowed)) + ')'
                param += tuple([x + '%' for x in allowed])
            sql += ' order by o.name'
        else:
            sql = 'select name, version_id from (%s) where name like ?'
            sql = sql % self._sql_until(until)
            param = (cont_prefix + prefix + '%',)
            if allowed:
                sql += ' and (' + ' or '.join(('name like ?',) * len(allowed)) + ')'
                param += tuple([x + '%' for x in allowed])
            sql += ' order by name'
        c = self.con.execute(sql, param)
        objects = [(x[0][len(cont_prefix):], x[1]) for x in c.fetchall()]
        if delimiter:
            pseudo_objects = []
            for x in objects:
                pseudo_name = x[0]
                i = pseudo_name.find(delimiter, len(prefix))
                if not virtual:
                    # If the delimiter is not found, or the name ends
                    # with the delimiter's first occurence.
                    if i == -1 or len(pseudo_name) == i + len(delimiter):
                        pseudo_objects.append(x)
                else:
                    # If the delimiter is found, keep up to (and including) the delimiter.
                    if i != -1:
                        pseudo_name = pseudo_name[:i + len(delimiter)]
                    if pseudo_name not in [y[0] for y in pseudo_objects]:
                        if pseudo_name == x[0]:
                            pseudo_objects.append(x)
                        else:
                            pseudo_objects.append((pseudo_name, None))
            objects = pseudo_objects
        
        start, limit = self._list_limits([x[0] for x in objects], marker, limit)
        return objects[start:start + limit]
    
    def _del_version(self, version):
        self.mapper.map_remv(version)
        sql = 'delete from versions where version_id = ?'
        self.con.execute(sql, (version,))
    
    # Access control functions.
    
    def _check_groups(self, groups):
        # Example follows.
        # for k, v in groups.iteritems():
        #     if True in [False or ',' in x for x in v]:
        #         raise ValueError('Bad characters in groups')
        pass
    
    def _get_groups(self, account):
        sql = 'select gname, user from groups where account = ?'
        c = self.con.execute(sql, (account,))
        groups = {}
        for gname, user in c.fetchall():
            if gname not in groups:
                groups[gname] = []
            groups[gname].append(user)
        return groups
    
    def _put_groups(self, account, groups, replace=False):
        if replace:
            self._del_groups(account)
        for k, v in groups.iteritems():
            sql = 'delete from groups where account = ? and gname = ?'
            self.con.execute(sql, (account, k))
            if v:
                sql = 'insert into groups (account, gname, user) values (?, ?, ?)'
                self.con.executemany(sql, [(account, k, x) for x in v])
    
    def _del_groups(self, account):
        sql = 'delete from groups where account = ?'
        self.con.execute(sql, (account,))
    
    def _check_permissions(self, path, permissions):
        # Check for existing permissions.
        sql = '''select name from permissions
                    where name != ? and (name like ? or ? like name || ?)'''
        c = self.con.execute(sql, (path, path + '%', path, '%'))
        rows = c.fetchall()
        if rows:
            ae = AttributeError()
            ae.data = rows
            raise ae
        
        # Format given permissions.
        if len(permissions) == 0:
            return [], []
        r = permissions.get('read', [])
        w = permissions.get('write', [])
        # Examples follow.
        # if True in [False or ',' in x for x in r]:
        #     raise ValueError('Bad characters in read permissions')
        # if True in [False or ',' in x for x in w]:
        #     raise ValueError('Bad characters in write permissions')
        return r, w
    
    def _get_permissions(self, path):
        # Check for permissions at path or above.
        sql = 'select name, op, user from permissions where ? like name || ?'
        c = self.con.execute(sql, (path, '%'))
        name = path
        perms = {} # Return nothing, if nothing is set.
        for row in c.fetchall():
            name = row[0]
            op = row[1]
            user = row[2]
            if op not in perms:
                perms[op] = []
            perms[op].append(user)
        return name, perms
    
    def _put_permissions(self, path, r, w):
        sql = 'delete from permissions where name = ?'
        self.con.execute(sql, (path,))
        sql = 'insert into permissions (name, op, user) values (?, ?, ?)'
        if r:
            self.con.executemany(sql, [(path, 'read', x) for x in r])
        if w:
            self.con.executemany(sql, [(path, 'write', x) for x in w])
    
    def _get_public(self, path):
        sql = 'select name from public where name = ?'
        c = self.con.execute(sql, (path,))
        row = c.fetchone()
        if not row:
            return False
        return True
    
    def _put_public(self, path, public):
        if not public:
            sql = 'delete from public where name = ?'
        else:
            sql = 'insert or replace into public (name) values (?)'
        self.con.execute(sql, (path,))
    
    def _del_sharing(self, path):
        sql = 'delete from permissions where name = ?'
        self.con.execute(sql, (path,))
        sql = 'delete from public where name = ?'
        self.con.execute(sql, (path,))
    
    def _is_allowed(self, user, account, container, name, op='read'):
        if smart_unicode(user) == smart_unicode(account):
            return True
        path = '/'.join((account, container, name))
        if op == 'read' and self._get_public(path):
            return True
        perm_path, perms = self._get_permissions(path)
        
        # Expand groups.
        for x in ('read', 'write'):
            g_perms = set()
            for y in perms.get(x, []):
                if ':' in y:
                    g_account, g_name = y.split(':', 1)
                    groups = self._get_groups(g_account)
                    if g_name in groups.keys():
                        g_perms.update(groups[g_name])
                else:
                    g_perms.add(y)
            perms[x] = g_perms
        
        user = smart_unicode(user, strings_only=True)
        if op == 'read' and ('*' in perms['read'] or user in perms['read']):
            return True
        if '*' in perms['write'] or user in perms['write']:
            return True
        return False
    
    def _can_read(self, user, account, container, name):
        if not self._is_allowed(user, account, container, name, 'read'):
            raise NotAllowedError
    
    def _can_write(self, user, account, container, name):
        if not self._is_allowed(user, account, container, name, 'write'):
            raise NotAllowedError
    
    def _allowed_paths(self, user, prefix=None):
        sql = '''select distinct name from permissions 
                 where (user = '*' or
                        user = ? or
                        user in (select account || ':' || gname from groups where user = ?))'''
        param = (user, user)
        if prefix:
            sql += ' and name like ?'
            param += (prefix + '/%',)
        c = self.con.execute(sql, param)
        return [x[0] for x in c.fetchall()]
    
    def _allowed_accounts(self, user):
        allow = set()
        for path in self._allowed_paths(user):
            allow.add(path.split('/', 1)[0])
        return sorted(allow)
    
    def _allowed_containers(self, user, account):
        allow = set()
        for path in self._allowed_paths(user, account):
            allow.add(path.split('/', 2)[1])
        return sorted(allow)
    
    def _shared_paths(self, prefix):
        sql = 'select distinct name from permissions where name like ?'
        c = self.con.execute(sql, (prefix + '/%',))
        return [x[0] for x in c.fetchall()]
