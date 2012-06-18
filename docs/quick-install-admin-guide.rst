.. _quick-install-admin-guide:

Administrator's Quick Installation Guide
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is the Administrator's quick installation guide.

It describes how to install the whole synnefo stack on two (2) physical nodes,
with minimum configuration. It installs synnefo from Debian packages, and
assumes the nodes run Debian Squeeze. After successful installation, you will
have the following services running:

 * Identity Management (Astakos)
 * Object Storage Service (Pithos+)
 * Compute Service (Cyclades)
 * Image Registry Service (Plankton)

and a single unified Web UI to manage them all.

The Volume Storage Service (Archipelago) and the Billing Service (Aquarium) are
not released yet.

If you just want to install the Object Storage Service (Pithos+), follow the guide
and just stop after the "Testing of Pithos+" section.


Installation of Synnefo / Introduction
======================================

We will install the services with the above list's order. Cyclades and Plankton
will be installed in a single step (at the end), because at the moment they are
contained in the same software component. Furthermore, we will install all
services in the first physical node, except Pithos+ which will be installed in
the second, due to a conflict between the snf-pithos-app and snf-cyclades-app
component (scheduled to be fixed in the next version).

For the rest of the documentation we will refer to the first physical node as
"node1" and the second as "node2". We will also assume that their domain names
are "node1.example.com" and "node2.example.com" and their IPs are "4.3.2.1" and
"4.3.2.2" respectively.


General Prerequisites
=====================

These are the general synnefo prerequisites, that you need on node1 and node2
and are related to all the services (Astakos, Pithos+, Cyclades, Plankton).

To be able to download all synnefo components you need to add the following
lines in your ``/etc/apt/sources.list`` file:

| ``deb http://apt.dev.grnet.gr squeeze main``
| ``deb-src http://apt.dev.grnet.gr squeeze main``

You also need a shared directory visible by both nodes. Pithos+ will save all
data inside this directory. By 'all data', we mean files, images, and pithos
specific mapping data. If you plan to upload more than one basic image, this
directory should have at least 50GB of free space. During this guide, we will
assume that node1 acts as an NFS server and serves the directory ``/srv/pithos``
to node2. Node2 has this directory mounted under ``/srv/pithos``, too.

Before starting the synnefo installation, you will need basic third party
software to be installed and configured on the physical nodes. We will describe
each node's general prerequisites separately. Any additional configuration,
specific to a synnefo service for each node, will be described at the service's
section.

Node1
-----

General Synnefo dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

 * apache (http server)
 * gunicorn (WSGI http server)
 * postgresql (database)
 * rabbitmq (message queue)

You can install the above by running:

.. code-block:: console

   # apt-get install apache2 postgresql rabbitmq-server

Make sure to install gunicorn >= v0.12.2. You can do this by installing from
the official debian backports:

.. code-block:: console

   # apt-get -t squeeze-backports install gunicorn

On node1, we will create our databases, so you will also need the
python-psycopg2 package:

.. code-block:: console

   # apt-get install python-psycopg2

Database setup
~~~~~~~~~~~~~~

On node1, we create a database called ``snf_apps``, that will host all django
apps related tables. We also create the user ``synnefo`` and grant him all
privileges on the database. We do this by running:

.. code-block:: console

   root@node1:~ # su - postgres
   postgres@node1:~ $ psql
   postgres=# CREATE DATABASE snf_apps WITH ENCODING 'UTF8' LC_COLLATE='C' LC_CTYPE='C' TEMPLATE=template0;
   postgres=# CREATE USER synnefo WITH PASSWORD 'example_passw0rd';
   postgres=# GRANT ALL PRIVILEGES ON DATABASE snf_apps TO synnefo;

We also create the database ``snf_pithos`` needed by the pithos+ backend and
grant the ``synnefo`` user all privileges on the database. This database could
be created on node2 instead, but we do it on node1 for simplicity. We will
create all needed databases on node1 and then node2 will connect to them.

.. code-block:: console

   postgres=# CREATE DATABASE snf_pithos WITH ENCODING 'UTF8' LC_COLLATE='C' LC_CTYPE='C' TEMPLATE=template0;
   postgres=# GRANT ALL PRIVILEGES ON DATABASE snf_pithos TO synnefo;

Configure the database to listen to all network interfaces. You can do this by
editting the file ``/etc/postgresql/8.4/main/postgresql.conf`` and change
``listen_addresses`` to ``'*'`` :

.. code-block:: console

   listen_addresses = '*'

Furthermore, edit ``/etc/postgresql/8.4/main/pg_hba.conf`` to allow node1 and
node2 to connect to the database. Add the following lines under ``#IPv4 local
connections:`` :

.. code-block:: console

   host		all	all	4.3.2.1/32	md5
   host		all	all	4.3.2.2/32	md5

Make sure to substitute "4.3.2.1" and "4.3.2.2" with node1's and node2's
actual IPs. Now, restart the server to apply the changes:

.. code-block:: console

   # /etc/init.d/postgresql restart

Gunicorn setup
~~~~~~~~~~~~~~

Create the file ``synnefo`` under ``/etc/gunicorn.d/`` containing the following:

.. code-block:: console

   CONFIG = {
    'mode': 'django',
    'environment': {
      'DJANGO_SETTINGS_MODULE': 'synnefo.settings',
    },
    'working_dir': '/etc/synnefo',
    'user': 'www-data',
    'group': 'www-data',
    'args': (
      '--bind=127.0.0.1:8080',
      '--workers=4',
      '--log-level=debug',
    ),
   }

.. warning:: Do NOT start the server yet, because it won't find the
    ``synnefo.settings`` module. We will start the server after successful
    installation of astakos. If the server is running::

       # /etc/init.d/gunicorn stop

Apache2 setup
~~~~~~~~~~~~~

Create the file ``synnefo`` under ``/etc/apache2/sites-available/`` containing
the following:

.. code-block:: console

   <VirtualHost *:80>
     ServerName node1.example.com

     RewriteEngine On
     RewriteCond %{THE_REQUEST} ^.*(\\r|\\n|%0A|%0D).* [NC]
     RewriteRule ^(.*)$ - [F,L]
     RewriteRule (.*) https://%{HTTP_HOST}%{REQUEST_URI}
   </VirtualHost>

Create the file ``synnefo-ssl`` under ``/etc/apache2/sites-available/``
containing the following:

.. code-block:: console

   <IfModule mod_ssl.c>
   <VirtualHost _default_:443>
     ServerName node1.example.com

     Alias /static "/usr/share/synnefo/static"

   #  SetEnv no-gzip
   #  SetEnv dont-vary

     AllowEncodedSlashes On

     RequestHeader set X-Forwarded-Protocol "https"

     <Proxy * >
       Order allow,deny
       Allow from all
     </Proxy>

     SetEnv                proxy-sendchunked
     SSLProxyEngine        off
     ProxyErrorOverride    off

     ProxyPass        /static !
     ProxyPass        / http://localhost:8080/ retry=0
     ProxyPassReverse / http://localhost:8080/

     RewriteEngine On
     RewriteCond %{THE_REQUEST} ^.*(\\r|\\n|%0A|%0D).* [NC]
     RewriteRule ^(.*)$ - [F,L]
     RewriteRule ^/login(.*) /im/login/redirect$1 [PT,NE]

     SSLEngine on
     SSLCertificateFile    /etc/ssl/certs/ssl-cert-snakeoil.pem
     SSLCertificateKeyFile /etc/ssl/private/ssl-cert-snakeoil.key
   </VirtualHost>
   </IfModule>

Now enable sites and modules by running:

.. code-block:: console

   # a2enmod ssl
   # a2enmod rewrite
   # a2dissite default
   # a2ensite synnefo
   # a2ensite synnefo-ssl
   # a2enmod headers
   # a2enmod proxy_http

.. warning:: Do NOT start/restart the server yet. If the server is running::

       # /etc/init.d/apache2 stop

.. _rabbitmq-setup:

Message Queue setup
~~~~~~~~~~~~~~~~~~~

The message queue will run on node1, so we need to create the appropriate
rabbitmq user. The user is named ``synnefo`` and gets full privileges on all
exchanges:

.. code-block:: console

   # rabbitmqctl add_user synnefo "examle_rabbitmq_passw0rd"
   # rabbitmqctl set_permissions synnefo ".*" ".*" ".*"

We do not need to initialize the exchanges. This will be done automatically,
during the Cyclades setup.

Pithos+ data directory setup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As mentioned in the General Prerequisites section, there is a directory called
``/srv/pithos`` visible by both nodes. We create and setup the ``data``
directory inside it:

.. code-block:: console

   # cd /srv/pithos
   # mkdir data
   # chown www-data:www-data data
   # chmod g+ws data

You are now ready with all general prerequisites concerning node1. Let's go to
node2.

Node2
-----

General Synnefo dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

 * apache (http server)
 * gunicorn (WSGI http server)
 * postgresql (database)

You can install the above by running:

.. code-block:: console

   # apt-get install apache2 postgresql

Make sure to install gunicorn >= v0.12.2. You can do this by installing from
the official debian backports:

.. code-block:: console

   # apt-get -t squeeze-backports install gunicorn

Node2 will connect to the databases on node1, so you will also need the
python-psycopg2 package:

.. code-block:: console

   # apt-get install python-psycopg2

Database setup
~~~~~~~~~~~~~~

All databases have been created and setup on node1, so we do not need to take
any action here. From node2, we will just connect to them. When you get familiar
with the software you may choose to run different databases on different nodes,
for performance/scalability/redundancy reasons, but those kind of setups are out
of the purpose of this guide.

Gunicorn setup
~~~~~~~~~~~~~~

Create the file ``synnefo`` under ``/etc/gunicorn.d/`` containing the following
(same contents as in node1; you can just copy/paste the file):

.. code-block:: console

   CONFIG = {
    'mode': 'django',
    'environment': {
      'DJANGO_SETTINGS_MODULE': 'synnefo.settings',
    },
    'working_dir': '/etc/synnefo',
    'user': 'www-data',
    'group': 'www-data',
    'args': (
      '--bind=127.0.0.1:8080',
      '--workers=4',
      '--log-level=debug',
      '--timeout=43200'
    ),
   }

.. warning:: Do NOT start the server yet, because it won't find the
    ``synnefo.settings`` module. We will start the server after successful
    installation of astakos. If the server is running::

       # /etc/init.d/gunicorn stop

Apache2 setup
~~~~~~~~~~~~~

Create the file ``synnefo`` under ``/etc/apache2/sites-available/`` containing
the following:

.. code-block:: console

   <VirtualHost *:80>
     ServerName node2.example.com

     RewriteEngine On
     RewriteCond %{THE_REQUEST} ^.*(\\r|\\n|%0A|%0D).* [NC]
     RewriteRule ^(.*)$ - [F,L]
     RewriteRule (.*) https://%{HTTP_HOST}%{REQUEST_URI}
   </VirtualHost>

Create the file ``synnefo-ssl`` under ``/etc/apache2/sites-available/``
containing the following:

.. code-block:: console

   <IfModule mod_ssl.c>
   <VirtualHost _default_:443>
     ServerName node2.example.com

     Alias /static "/usr/share/synnefo/static"

     SetEnv no-gzip
     SetEnv dont-vary
     AllowEncodedSlashes On

     RequestHeader set X-Forwarded-Protocol "https"

     <Proxy * >
       Order allow,deny
       Allow from all
     </Proxy>

     SetEnv                proxy-sendchunked
     SSLProxyEngine        off
     ProxyErrorOverride    off

     ProxyPass        /static !
     ProxyPass        / http://localhost:8080/ retry=0
     ProxyPassReverse / http://localhost:8080/

     SSLEngine on
     SSLCertificateFile    /etc/ssl/certs/ssl-cert-snakeoil.pem
     SSLCertificateKeyFile /etc/ssl/private/ssl-cert-snakeoil.key
   </VirtualHost>
   </IfModule>

As in node1, enable sites and modules by running:

.. code-block:: console

   # a2enmod ssl
   # a2enmod rewrite
   # a2dissite default
   # a2ensite synnefo
   # a2ensite synnefo-ssl
   # a2enmod headers
   # a2enmod proxy_http

.. warning:: Do NOT start/restart the server yet. If the server is running::

       # /etc/init.d/apache2 stop

We are now ready with all general prerequisites for node2. Now that we have
finished with all general prerequisites for both nodes, we can start installing
the services. First, let's install Astakos on node1.


Installation of Astakos on node1
================================

To install astakos, grab the package from our repository (make sure  you made
the additions needed in your ``/etc/apt/sources.list`` file, as described
previously), by running:

.. code-block:: console

   # apt-get install snf-astakos-app

After successful installation of snf-astakos-app, make sure that also
snf-webproject has been installed (marked as "Recommended" package). By default
Debian installs "Recommended" packages, but if you have changed your
configuration and the package didn't install automatically, you should
explicitly install it manually running:

.. code-block:: console

   # apt-get install snf-webproject

The reason snf-webproject is "Recommended" and not a hard dependency, is to give
the experienced administrator the ability to install synnefo in a custom made
django project. This corner case concerns only very advanced users that know
what they are doing and want to experiment with synnefo.


.. _conf-astakos:

Configuration of Astakos
========================

Conf Files
----------

After astakos is successfully installed, you will find the directory
``/etc/synnefo`` and some configuration files inside it. The files contain
commented configuration options, which are the default options. While installing
new snf-* components, new configuration files will appear inside the directory.
In this guide (and for all services), we will edit only the minimum necessary
configuration options, to reflect our setup. Everything else will remain as is.

After getting familiar with synnefo, you will be able to customize the software
as you wish and fits your needs. Many options are available, to empower the
administrator with extensively customizable setups.

For the snf-webproject component (installed as an astakos dependency), we
need the following:

Edit ``/etc/synnefo/10-snf-webproject-database.conf``. You will need to
uncomment and edit the ``DATABASES`` block to reflect our database:

.. code-block:: console

   DATABASES = {
    'default': {
        # 'postgresql_psycopg2', 'postgresql','mysql', 'sqlite3' or 'oracle'
        'ENGINE': 'postgresql_psycopg2',
         # ATTENTION: This *must* be the absolute path if using sqlite3.
         # See: http://docs.djangoproject.com/en/dev/ref/settings/#name
        'NAME': 'snf_apps',
        'USER': 'synnefo',                      # Not used with sqlite3.
        'PASSWORD': 'examle_passw0rd',          # Not used with sqlite3.
        # Set to empty string for localhost. Not used with sqlite3.
        'HOST': '4.3.2.1',
        # Set to empty string for default. Not used with sqlite3.
        'PORT': '5432',
    }
   }

Edit ``/etc/synnefo/10-snf-webproject-deploy.conf``. Uncomment and edit
``SECRET_KEY``. This is a django specific setting which is used to provide a
seed in secret-key hashing algorithms. Set this to a random string of your
choise and keep it private:

.. code-block:: console

   SECRET_KEY = 'sy6)mw6a7x%n)-example_secret_key#zzk4jo6f2=uqu!1o%)'

For astakos specific configuration, edit the following options in
``/etc/synnefo/20-snf-astakos-app-settings.conf`` :

.. code-block:: console

   ASTAKOS_IM_MODULES = ['local']

   ASTAKOS_COOKIE_DOMAIN = '.example.com'

   ASTAKOS_BASEURL = 'https://node1.example.com'

   ASTAKOS_SITENAME = '~okeanos demo example'

   ASTAKOS_RECAPTCHA_PUBLIC_KEY = 'example_recaptcha_public_key!@#$%^&*('
   ASTAKOS_RECAPTCHA_PRIVATE_KEY = 'example_recaptcha_private_key!@#$%^&*('

   ASTAKOS_RECAPTCHA_USE_SSL = True

``ASTAKOS_IM_MODULES`` refers to the astakos login methods. For now only local
is supported. The ``ASTAKOS_COOKIE_DOMAIN`` should be the base url of our
domain (for all services). ``ASTAKOS_BASEURL`` is the astakos home page.

For the ``ASTAKOS_RECAPTCHA_PUBLIC_KEY`` and ``ASTAKOS_RECAPTCHA_PRIVATE_KEY``
go to https://www.google.com/recaptcha/admin/create and create your own pair.

If you are an advanced user and want to use the Shibboleth Authentication method,
read the relative :ref:`section <shibboleth-auth>`.

Database Initialization
-----------------------

After configuration is done, we initialize the database by running:

.. code-block:: console

   # snf-manage syncdb

At this example we don't need to create a django superuser, so we select
``[no]`` to the question. After a successful sync, we run the migration needed
for astakos:

.. code-block:: console

   # snf-manage migrate im

Then, we load the pre-defined user groups

.. code-block:: console

   # snf-manage loaddata groups

.. _services-reg:

Services Registration
---------------------

When the database is ready, we configure the elements of the Astakos cloudbar,
to point to our future services:

.. code-block:: console

   # snf-manage registerservice "~okeanos home" https://node1.example.com/im/ home-icon.png
   # snf-manage registerservice "cyclades" https://node1.example.com/ui/
   # snf-manage registerservice "pithos+" https://node2.example.com/ui/

Servers Initialization
----------------------

Finally, we initialize the servers on node1:

.. code-block:: console

   root@node1:~ # /etc/init.d/gunicorn restart
   root@node1:~ # /etc/init.d/apache2 restart

We have now finished the Astakos setup. Let's test it now.


Testing of Astakos
==================

Open your favorite browser and go to:

``http://node1.example.com/im``

If this redirects you to ``https://node1.example.com/im`` and you can see
the "welcome" door of Astakos, then you have successfully setup Astakos.

Let's create our first user. At the homepage click the "CREATE ACCOUNT" button
and fill all your data at the sign up form. Then click "SUBMIT". You should now
see a green box on the top, which informs you that you made a successful request
and the request has been sent to the administrators. So far so good, let's assume
that you created the user with username ``user@example.com``.

Now we need to activate that user. Return to a command prompt at node1 and run:

.. code-block:: console

   root@node1:~ # snf-manage listusers

This command should show you a list with only one user; the one we just created.
This user should have an id with a value of ``1``. It should also have an
"active" status with the value of ``0`` (inactive). Now run:

.. code-block:: console

   root@node1:~ # snf-manage modifyuser --set-active 1

This modifies the active value to ``1``, and actually activates the user.
When running in production, the activation is done automatically with different
types of moderation, that Astakos supports. You can see the moderation methods
(by invitation, whitelists, matching regexp, etc.) at the Astakos specific
documentation. In production, you can also manually activate a user, by sending
him/her an activation email. See how to do this at the :ref:`User
activation <user_activation>` section.

Now let's go back to the homepage. Open ``http://node1.example.com/im`` with
your browser again. Try to sign in using your new credentials. If the astakos
menu appears and you can see your profile, then you have successfully setup
Astakos.

Let's continue to install Pithos+ now.


Installation of Pithos+ on node2
================================

To install pithos+, grab the packages from our repository (make sure  you made
the additions needed in your ``/etc/apt/sources.list`` file, as described
previously), by running:

.. code-block:: console

   # apt-get install snf-pithos-app

After successful installation of snf-pithos-app, make sure that also
snf-webproject has been installed (marked as "Recommended" package). Refer to
the "Installation of Astakos on node1" section, if you don't remember why this
should happen. Now, install the pithos web interface:

.. code-block:: console

   # apt-get install snf-pithos-webclient

This package provides the standalone pithos web client. The web client is the
web UI for pithos+ and will be accessible by clicking "pithos+" on the Astakos
interface's cloudbar, at the top of the Astakos homepage.


.. _conf-pithos:

Configuration of Pithos+
========================

Conf Files
----------

After pithos+ is successfully installed, you will find the directory
``/etc/synnefo`` and some configuration files inside it, as you did in node1
after installation of astakos. Here, you will not have to change anything that
has to do with snf-common or snf-webproject. Everything is set at node1. You
only need to change settings that have to do with pithos+. Specifically:

Edit ``/etc/synnefo/20-snf-pithos-app-settings.conf``. There you need to set
only the two options:

.. code-block:: console

   PITHOS_BACKEND_DB_CONNECTION = 'postgresql://synnefo:example_passw0rd@node1.example.com:5432/snf_pithos'

   PITHOS_BACKEND_BLOCK_PATH = '/srv/pithos/data'

   PITHOS_AUTHENTICATION_URL = 'https://node1.example.com/im/authenticate'
   PITHOS_AUTHENTICATION_USERS = None

   PITHOS_SERVICE_TOKEN = 'pithos_service_token22w=='

The ``PITHOS_BACKEND_DB_CONNECTION`` option tells to the pithos+ app where to
find the pithos+ backend database. Above we tell pithos+ that its database is
``snf_pithos`` at node1 and to connect as user ``synnefo`` with password
``example_passw0rd``.  All those settings where setup during node1's "Database
setup" section.

The ``PITHOS_BACKEND_BLOCK_PATH`` option tells to the pithos+ app where to find
the pithos+ backend data. Above we tell pithos+ to store its data under
``/srv/pithos/data``, which is visible by both nodes. We have already setup this
directory at node1's "Pithos+ data directory setup" section.

The ``PITHOS_AUTHENTICATION_URL`` option tells to the pithos+ app in which URI
is available the astakos authentication api. If not set, pithos+ tries to
authenticate using the ``PITHOS_AUTHENTICATION_USERS`` user pool.

The ``PITHOS_SERVICE_TOKEN`` should be the Pithos+ token returned by running on
the Astakos node (node1 in our case):

.. code-block:: console

   # snf-manage listservices

The token has been generated automatically during the :ref:`Pithos+ service
registration <services-reg>`.

Then we need to setup the web UI and connect it to astakos. To do so, edit
``/etc/synnefo/20-snf-pithos-webclient-settings.conf``:

.. code-block:: console

   PITHOS_UI_LOGIN_URL = "https://node1.example.com/im/login?next="
   PITHOS_UI_FEEDBACK_URL = "https://node1.example.com/im/feedback"

The ``PITHOS_UI_LOGIN_URL`` option tells the client where to redirect you, if
you are not logged in. The ``PITHOS_UI_FEEDBACK_URL`` option points at the
pithos+ feedback form. Astakos already provides a generic feedback form for all
services, so we use this one.

Then edit ``/etc/synnefo/20-snf-pithos-webclient-cloudbar.conf``, to connect the
pithos+ web UI with the astakos web UI (through the top cloudbar):

.. code-block:: console

   CLOUDBAR_LOCATION = 'https://node1.example.com/static/im/cloudbar/'
   PITHOS_UI_CLOUDBAR_ACTIVE_SERVICE = '3'
   CLOUDBAR_SERVICES_URL = 'https://node1.example.com/im/get_services'
   CLOUDBAR_MENU_URL = 'https://node1.example.com/im/get_menu'

The ``CLOUDBAR_LOCATION`` tells the client where to find the astakos common
cloudbar.

The ``PITHOS_UI_CLOUDBAR_ACTIVE_SERVICE`` points to an already registered
Astakos service. You can see all :ref:`registered services <services-reg>` by
running on the Astakos node (node1):

.. code-block:: console

   # snf-manage listservices

The value of ``PITHOS_UI_CLOUDBAR_ACTIVE_SERVICE`` should be the pithos service's
``id`` as shown by the above command, in our case ``3``.

The ``CLOUDBAR_SERVICES_URL`` and ``CLOUDBAR_MENU_URL`` options are used by the
pithos+ web client to get from astakos all the information needed to fill its
own cloudbar. So we put our astakos deployment urls there.

Servers Initialization
----------------------

After configuration is done, we initialize the servers on node2:

.. code-block:: console

   root@node2:~ # /etc/init.d/gunicorn restart
   root@node2:~ # /etc/init.d/apache2 restart

You have now finished the Pithos+ setup. Let's test it now.


Testing of Pithos+
==================

Open your browser and go to the Astakos homepage:

``http://node1.example.com/im``

Login, and you will see your profile page. Now, click the "pithos+" link on the
top black cloudbar. If everything was setup correctly, this will redirect you
to:

``https://node2.example.com/ui``

and you will see the blue interface of the Pithos+ application.  Click the
orange "Upload" button and upload your first file. If the file gets uploaded
successfully, then this is your first sign of a successful Pithos+ installation.
Go ahead and experiment with the interface to make sure everything works
correctly.

You can also use the Pithos+ clients to sync data from your Windows PC or MAC.

If you don't stumble on any problems, then you have successfully installed
Pithos+, which you can use as a standalone File Storage Service.

If you would like to do more, such as:

 * Spawning VMs
 * Spawning VMs from Images stored on Pithos+
 * Uploading your custom Images to Pithos+
 * Spawning VMs from those custom Images
 * Registering existing Pithos+ files as Images
 * Connect VMs to the Internet
 * Create Private Networks
 * Add VMs to Private Networks

please continue with the rest of the guide.


Cyclades (and Plankton) Prerequisites
=====================================

Before proceeding with the Cyclades (and Plankton) installation, make sure you
have successfully set up Astakos and Pithos+ first, because Cyclades depends
on them. If you don't have a working Astakos and Pithos+ installation yet,
please return to the :ref:`top <quick-install-admin-guide>` of this guide.

Besides Astakos and Pithos+, you will also need a number of additional working
prerequisites, before you start the Cyclades installation.

Ganeti
------

`Ganeti <http://code.google.com/p/ganeti/>`_ handles the low level VM management
for Cyclades, so Cyclades requires a working Ganeti installation at the backend.
Please refer to the
`ganeti documentation <http://docs.ganeti.org/ganeti/2.5/html>`_ for all the
gory details. A successful Ganeti installation concludes with a working
:ref:`GANETI-MASTER <GANETI_NODES>` and a number of :ref:`GANETI-NODEs
<GANETI_NODES>`.

The above Ganeti cluster can run on different physical machines than node1 and
node2 and can scale independently, according to your needs.

For the purpose of this guide, we will assume that the :ref:`GANETI-MASTER
<GANETI_NODES>` runs on node1 and is VM-capable. Also, node2 is a
:ref:`GANETI-NODE <GANETI_NODES>` and is Master-capable and VM-capable too.

We highly recommend that you read the official Ganeti documentation, if you are
not familiar with Ganeti. If you are extremely impatient, you can result with
the above assumed setup by running:

.. code-block:: console

   root@node1:~ # apt-get install ganeti2
   root@node1:~ # apt-get install ganeti-htools
   root@node2:~ # apt-get install ganeti2
   root@node2:~ # apt-get install ganeti-htools

We assume that Ganeti will use the KVM hypervisor. After installing Ganeti on
both nodes, choose a domain name that resolves to a valid floating IP (let's say
it's ``ganeti.node1.example.com``). Make sure node1 and node2 have root access
between each other using ssh keys and not passwords. Also, make sure there is an
lvm volume group named ``ganeti`` that will host your VMs' disks. Finally, setup
a bridge interface on the host machines (e.g:: br0). Then run on node1:

.. code-block:: console

   root@node1:~ # gnt-cluster init --enabled-hypervisors=kvm --no-ssh-init
                                   --no-etc-hosts --vg-name=ganeti
                                   --nic-parameters link=br0 --master-netdev eth0
                                   ganeti.node1.example.com
   root@node1:~ # gnt-cluster modify --default-iallocator hail
   root@node1:~ # gnt-cluster modify --hypervisor-parameters kvm:kernel_path=
   root@node1:~ # gnt-cluster modify --hypervisor-parameters kvm:vnc_bind_address=0.0.0.0

   root@node1:~ # gnt-node add --no-node-setup --master-capable=yes
                               --vm-capable=yes node2.example.com

For any problems you may stumble upon installing Ganeti, please refer to the
`official documentation <http://docs.ganeti.org/ganeti/2.5/html>`_. Installation
of Ganeti is out of the scope of this guide.

.. _cyclades-install-snfimage:

snf-image
---------

Installation
~~~~~~~~~~~~
For :ref:`Cyclades <cyclades>` to be able to launch VMs from specified Images,
you need the :ref:`snf-image <snf-image>` OS Definition installed on *all*
VM-capable Ganeti nodes. This means we need :ref:`snf-image <snf-image>` on
node1 and node2. You can do this by running on *both* nodes:

.. code-block:: console

   # apt-get install snf-image-host

Now, you need to download and save the corresponding helper package. Please see
`here <https://code.grnet.gr/projects/snf-image/files>`_ for the latest package. Let's
assume that you installed snf-image-host version 0.3.5-1. Then, you need
snf-image-helper v0.3.5-1 on *both* nodes:

.. code-block:: console

   # cd /var/lib/snf-image/helper/
   # wget https://code.grnet.gr/attachments/download/1058/snf-image-helper_0.3.5-1_all.deb

.. warning:: Be careful: Do NOT install the snf-image-helper debian package.
             Just put it under /var/lib/snf-image/helper/

Once, you have downloaded the snf-image-helper package, create the helper VM by
running on *both* nodes:

.. code-block:: console

   # ln -s snf-image-helper_0.3.5-1_all.deb snf-image-helper.deb
   # snf-image-update-helper

This will create all the needed files under ``/var/lib/snf-image/helper/`` for
snf-image-host to run successfully.

Configuration
~~~~~~~~~~~~~
snf-image supports native access to Images stored on Pithos+. This means that
snf-image can talk directly to the Pithos+ backend, without the need of providing
a public URL. More details, are described in the next section. For now, the only
thing we need to do, is configure snf-image to access our Pithos+ backend.

To do this, we need to set the corresponding variables in
``/etc/default/snf-image``, to reflect our Pithos+ setup:

.. code-block:: console

   PITHOS_DB="postgresql://synnefo:example_passw0rd@node1.example.com:5432/snf_pithos"

   PITHOS_DATA="/srv/pithos/data"

If you have installed your Ganeti cluster on different nodes than node1 and node2 make
sure that ``/srv/pithos/data`` is visible by all of them.

If you would like to use Images that are also/only stored locally, you need to
save them under ``IMAGE_DIR``, however this guide targets Images stored only on
Pithos+.

Testing
~~~~~~~
You can test that snf-image is successfully installed by running on the
:ref:`GANETI-MASTER <GANETI_NODES>` (in our case node1):

.. code-block:: console

   # gnt-os diagnose

This should return ``valid`` for snf-image.

If you are interested to learn more about snf-image's internals (and even use
it alongside Ganeti without Synnefo), please see
`here <https://code.grnet.gr/projects/snf-image/wiki>`_ for information concerning
installation instructions, documentation on the design and implementation, and
supported Image formats.

snf-image's actual Images
-------------------------

Now that snf-image is installed successfully we need to provide it with some
Images. :ref:`snf-image <snf-image>` supports Images stored in ``extdump``,
``ntfsdump`` or ``diskdump`` format. We recommend the use of the ``diskdump``
format. For more information about snf-image's Image formats see `here
<https://code.grnet.gr/projects/snf-image/wiki/Image_Format>`_.

:ref:`snf-image <snf-image>` also supports three (3) different locations for the
above Images to be stored:

 * Under a local folder (usually an NFS mount, configurable as ``IMAGE_DIR`` in
   :file:`/etc/default/snf-image`)
 * On a remote host (accessible via a public URL e.g: http://... or ftp://...)
 * On Pithos+ (accessible natively, not only by its public URL)

For the purpose of this guide, we will use the `Debian Squeeze Base Image
<https://pithos.okeanos.grnet.gr/public/9epgb>`_ found on the official
`snf-image page
<https://code.grnet.gr/projects/snf-image/wiki#Sample-Images>`_. The image is
of type ``diskdump``. We will store it in our new Pithos+ installation.

To do so, do the following:

a) Download the Image from the official snf-image page (`image link
   <https://pithos.okeanos.grnet.gr/public/9epgb>`_).

b) Upload the Image to your Pithos+ installation, either using the Pithos+ Web UI
   or the command line client `kamaki
   <http://docs.dev.grnet.gr/kamaki/latest/index.html>`_.

Once the Image is uploaded successfully, download the Image's metadata file
from the official snf-image page (`image_metadata link
<https://pithos.okeanos.grnet.gr/public/gwqcv>`_). You will need it, for
spawning a VM from Ganeti, in the next section.

Of course, you can repeat the procedure to upload more Images, available from the
`official snf-image page
<https://code.grnet.gr/projects/snf-image/wiki#Sample-Images>`_.

Spawning a VM from a Pithos+ Image, using Ganeti
------------------------------------------------

Now, it is time to test our installation so far. So, we have Astakos and
Pithos+ installed, we have a working Ganeti installation, the snf-image
definition installed on all VM-capable nodes and a Debian Squeeze Image on
Pithos+. Make sure you also have the `metadata file
<https://pithos.okeanos.grnet.gr/public/gwqcv>`_ for this image.

Run on the :ref:`GANETI-MASTER's <GANETI_NODES>` (node1) command line:

.. code-block:: console

   # gnt-instance add -o snf-image+default --os-parameters
                      img_passwd=my_vm_example_passw0rd,
                      img_format=diskdump,
                      img_id="pithos://user@example.com/pithos/debian_base-6.0-7-x86_64.diskdump",
                      img_properties='{"OSFAMILY":"linux"\,"ROOT_PARTITION":"1"}'
                      -t plain --disk 0:size=2G --no-name-check --no-ip-check
                      testvm1

In the above command:

 * ``img_passwd``: the arbitrary root password of your new instance
 * ``img_format``: set to ``diskdump`` to reflect the type of the uploaded Image
 * ``img_id``: If you want to deploy an Image stored on Pithos+ (our case), this
               should have the format
               ``pithos://<username>/<container>/<filename>``:
                * ``username``: ``user@example.com`` (defined during Astakos sign up)
                * ``container``: ``pithos`` (default, if the Web UI was used)
                * ``filename``: the name of file (visible also from the Web UI)
 * ``img_properties``: taken from the metadata file. Used only the two mandatory
                       properties ``OSFAMILY`` and ``ROOT_PARTITION``. `Learn more
                       <https://code.grnet.gr/projects/snf-image/wiki/Image_Format#Image-Properties>`_

If the ``gnt-instance add`` command returns successfully, then run:

.. code-block:: console

   # gnt-instance info testvm1 | grep "console connection"

to find out where to connect using VNC. If you can connect successfully and can
login to your new instance using the root password ``my_vm_example_passw0rd``,
then everything works as expected and you have your new Debian Base VM up and
running.

If ``gnt-instance add`` fails, make sure that snf-image is correctly configured
to access the Pithos+ database and the Pithos+ backend data. Also, make sure
you gave the correct ``img_id`` and ``img_properties``. If ``gnt-instance add``
succeeds but you cannot connect, again find out what went wrong. Do *NOT*
proceed to the next steps unless you are sure everything works till this point.

If everything works, you have successfully connected Ganeti with Pithos+. Let's
move on to networking now.

.. warning::
    You can bypass the networking sections and go straight to
    :ref:`Cyclades Ganeti tools <cyclades-gtools>`, if you do not want to setup
    the Cyclades Network Service, but only the Cyclades Compute Service
    (recommended for now).

Network setup overview
----------------------

This part is deployment-specific and must be customized based on the specific
needs of the system administrator. However, to do so, the administrator needs
to understand how each level handles Virtual Networks, to be able to setup the
backend appropriately, before installing Cyclades.

Network @ Cyclades level
~~~~~~~~~~~~~~~~~~~~~~~~

Cyclades understands two types of Virtual Networks:

a) One common Public Network (Internet)
b) One or more distinct Private Networks (L2)

a) When a new VM is created, it instantly gets connected to the Public Network
   (Internet). This means it gets a public IPv4 and IPv6 and has access to the
   public Internet.

b) Then each user, is able to create one or more Private Networks manually and
   add VMs inside those Private Networks. Private Networks provide Layer 2
   connectivity. All VMs inside a Private Network are completely isolated.

From the VM perspective, every Network corresponds to a distinct NIC. So, the
above are translated as follows:

a) Every newly created VM, needs at least one NIC. This NIC, connects the VM
   to the Public Network and thus should get a public IPv4 and IPv6.

b) For every Private Network, the VM gets a new NIC, which is added during the
   connection of the VM to the Private Network (without an IP). This NIC should
   have L2 connectivity with all other NICs connected to this Private Network.

To achieve the above, first of all, we need Network and IP Pool management support
at Ganeti level, for Cyclades to be able to issue the corresponding commands.

Network @ Ganeti level
~~~~~~~~~~~~~~~~~~~~~~

Currently, Ganeti does not support IP Pool management. However, we've been
actively in touch with the official Ganeti team, who are reviewing a relatively
big patchset that implements this functionality (you can find it at the
ganeti-devel mailing list). We hope that the functionality will be merged to
the Ganeti master branch soon and appear on Ganeti 2.7.

Furthermore, currently the `~okeanos service <http://okeanos.grnet.gr>`_ uses
the same patchset with slight differencies on top of Ganeti 2.4.5. Cyclades
0.9 are compatible with this old patchset and we do not guarantee that will
work with the updated patchset sent to ganeti-devel.

We do *NOT* recommend you to apply the patchset yourself on the current Ganeti
master, unless you are an experienced Cyclades and Ganeti integrator and you
really know what you are doing.

Instead, be a little patient and we hope that everything will work out of the
box, once the patchset makes it into the Ganeti master. When so, Cyclades will
get updated to become compatible with that Ganeti version.

Network @ Physical host level
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We talked about the two types of Network from the Cyclades perspective, from the
VMs perspective and from Ganeti's perspective. Finally, we need to talk about
the Networks from the physical (VM container) host's perspective.

If your version of Ganeti supports IP pool management, then you need to setup
your physical hosts for the two types of Networks. For the second type
(Private Networks), our reference installation uses a number of pre-provisioned
bridges (one for each Network), which are connected to the corresponding number
of pre-provisioned vlans on each physical host (node1 and node2). For the first
type (Public Network), our reference installation uses routing over one
preprovisioned vlan on each host (node1 and node2). It also uses the `NFDHCPD`
package for dynamically serving specific public IPs managed by Ganeti.

Public Network setup
--------------------

Physical hosts' public network setup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The physical hosts' setup is out of the scope of this guide.

However, two common cases that you may want to consider (and choose from) are:

a) One public bridge, where all VMs' public tap interfaces will connect.
b) IP-less routing over the same vlan on every host.

When you setup your physical hosts (node1 and node2) for the Public Network,
then you need to inform Ganeti about the Network's IP range.

Add the public network to Ganeti
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once you have Ganeti with IP pool management up and running, you need to choose
the public network for your VMs and add it to Ganeti. Let's assume, that you
want to assign IPs from the ``5.6.7.0/27`` range to your new VMs, with
``5.6.7.1`` as their gateway. You can add the network by running:

.. code-block:: console

   # gnt-network add --network=5.6.7.0/27 --gateway=5.6.7.1 public_network

Then, connect the network to all your nodegroups. We assume that we only have
one nodegroup (``default``) in our Ganeti cluster:

.. code-block:: console

   # gnt-network connect public_network default public_link

Your new network is now ready from the Ganeti perspective. Now, we need to setup
`NFDHCPD` to actually reply with the correct IPs (that Ganeti will choose for
each NIC).

NFDHCPD
~~~~~~~

At this point, Ganeti knows about your preferred network, it can manage the IP
pool and choose a specific IP for each new VM's NIC. However, the actual
assignment of the IP to the NIC is not done by Ganeti. It is done after the VM
boots and its dhcp client makes a request. When this is done, `NFDHCPD` will
reply to the request with Ganeti's chosen IP. So, we need to install `NFDHCPD`
on all VM-capable nodes of the Ganeti cluster (node1 and node2 in our case) and
connect it to Ganeti:

.. code-block:: console

   # apt-get install nfdhcpd

Edit ``/etc/nfdhcpd/nfdhcpd.conf`` to reflect your network configuration. At
least, set the ``dhcp_queue`` variable to ``42`` and the ``nameservers``
variable to your DNS IP/s. Those IPs will be passed as the DNS IP/s of your new
VMs. Once you are finished, restart the server on all nodes:

.. code-block:: console

   # /etc/init.d/nfdhcpd restart

If you are using ``ferm``, then you need to run the following:

.. code-block:: console

   # echo "@include 'nfdhcpd.ferm';" >> /etc/ferm/ferm.conf
   # /etc/init.d/ferm restart

Now, you need to connect `NFDHCPD` with Ganeti. To do that, you need to install
a custom KVM ifup script for use by Ganeti, as ``/etc/ganeti/kvm-vif-bridge``,
on all VM-capable GANETI-NODEs (node1 and node2). A sample implementation is
provided along with `snf-cyclades-gtools <snf-cyclades-gtools>`, that will
be installed in the next sections, however you will probably need to write your
own, according to your underlying network configuration.

Testing the Public Network
~~~~~~~~~~~~~~~~~~~~~~~~~~

So, we have setup the bridges/vlans on the physical hosts appropriately, we have
added the desired network to Ganeti, we have installed nfdhcpd and installed the
appropriate ``kvm-vif-bridge`` script under ``/etc/ganeti``.

Now, it is time to test that the backend infrastracture is correctly setup for
the Public Network. We assume to have used the (b) method on setting up the
physical hosts. We will add a new VM, the same way we did it on the previous
testing section. However, now will also add one NIC, configured to be managed
from our previously defined network. Run on the GANETI-MASTER (node1):

.. code-block:: console

   # gnt-instance add -o snf-image+default --os-parameters
                      img_passwd=my_vm_example_passw0rd,
                      img_format=diskdump,
                      img_id="pithos://user@example.com/pithos/debian_base-6.0-7-x86_64.diskdump",
                      img_properties='{"OSFAMILY":"linux"\,"ROOT_PARTITION":"1"}'
                      -t plain --disk 0:size=2G --no-name-check --no-ip-check
                      --net 0:ip=pool,mode=routed,link=public_link
                      testvm2

If the above returns successfully, connect to the new VM and run:

.. code-block:: console

   root@testvm2:~ # ifconfig -a

If a network interface appears with an IP from you Public Network's range
(``5.6.7.0/27``) and the corresponding gateway, then you have successfully
connected Ganeti with `NFDHCPD` (and ``kvm-vif-bridge`` works correctly).

Now ping the outside world. If this works too, then you have also configured
correctly your physical hosts' networking.

Later, Cyclades will create the first NIC of every new VM by issuing an
analogous command. The first NIC of the instance will be the NIC connected to
the Public Network. The ``link`` variable will be set accordingly in the
Cyclades conf files later on the guide.

Make sure everything works as expected, before proceeding with the Private
Networks setup.

.. _private-networks-setup:

Private Networks setup
----------------------

Physical hosts' private networks setup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

At the physical host's level, it is the administrator's responsibility to
configure the network appropriately, according to his/her needs (as for the
Public Network).

However we propose the following setup:

For every possible Private Network we assume a pre-provisioned bridge interface
exists on every host with the same name. Every Private Network will be
associated with one of the pre-provisioned bridges. Then the instance's new NIC
(while connecting to the Private Network) will be connected to that bridge. All
instances' tap interfaces that reside in the same Private Network will be
connected in the corresponding bridge of that network. Furthermore, every
bridge will be connected to a corresponding vlan. So, lets assume that our
Cyclades installation allows for 20 Private Networks to be setup. We should
pre-provision the corresponding bridges and vlans to all the hosts. We can do
this by running on all VM-capable Ganeti nodes (in our case node1 and node2):

.. code-block:: console

   # $iface=eth0
   # for prv in $(seq 1 20); do
	vlan=$prv
	bridge=prv$prv
	vconfig add $iface $vlan
	ifconfig $iface.$vlan up
	brctl addbr $bridge
	brctl setfd $bridge 0
	brctl addif $bridge $iface.$vlan
	ifconfig $bridge up
      done

The above will do the following (assuming ``eth0`` exists on both hosts):

 * provision 20 new bridges: ``prv1`` - ``prv20``
 * provision 20 new vlans: ``eth0.1`` - ``eth0.20``
 * add the corresponding vlan to the equivelant bridge

You can run ``brctl show`` on both nodes to see if everything was setup
correctly.

Everything is now setup to support the 20 Cyclades Private Networks. Later,
we will configure Cyclades to talk to those 20 pre-provisioned bridges.

Testing the Private Networks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To test the Private Networks, we will create two instances and put them in the
same Private Network (``prv1``). This means that the instances will have a
second NIC connected to the ``prv1`` pre-provisioned bridge.

We run the same command as in the Public Network testing section, but with one
more argument for the second NIC:

.. code-block:: console

   # gnt-instance add -o snf-image+default --os-parameters
                      img_passwd=my_vm_example_passw0rd,
                      img_format=diskdump,
                      img_id="pithos://user@example.com/pithos/debian_base-6.0-7-x86_64.diskdump",
                      img_properties='{"OSFAMILY":"linux"\,"ROOT_PARTITION":"1"}'
                      -t plain --disk 0:size=2G --no-name-check --no-ip-check
                      --net 0:ip=pool,mode=routed,link=public_link
                      --net 1:ip=none,mode=bridged,link=prv1
                      testvm3

   # gnt-instance add -o snf-image+default --os-parameters
                      img_passwd=my_vm_example_passw0rd,
                      img_format=diskdump,
                      img_id="pithos://user@example.com/pithos/debian_base-6.0-7-x86_64.diskdump",
                      img_properties='{"OSFAMILY":"linux"\,"ROOT_PARTITION":"1"}'
                      -t plain --disk 0:size=2G --no-name-check --no-ip-check
                      --net 0:ip=pool,mode=routed,link=public_link
                      --net 1:ip=none,mode=bridged,link=prv1
                      testvm4

Above, we create two instances with their first NIC connected to the Public
Network and their second NIC connected to the first Private Network (``prv1``).
Now, connect to the instances using VNC and make sure everything works as
expected:

a) The instances have access to the public internet through their first eth
   interface (``eth0``), which has been automatically assigned a public IP.

b) Setup the second eth interface of the instances (``eth1``), by assigning two
   different private IPs (e.g.: ``10.0.0.1`` and ``10.0.0.2``) and the
   corresponding netmask. If they ``ping`` each other successfully, then
   the Private Network works.

Repeat the procedure with more instances connected in different Private Networks
(``prv{1-20}``), by adding more NICs on each instance. e.g.: We add an instance
connected to the Public Network and Private Networks 1, 3 and 19:

.. code-block:: console

   # gnt-instance add -o snf-image+default --os-parameters
                      img_passwd=my_vm_example_passw0rd,
                      img_format=diskdump,
                      img_id="pithos://user@example.com/pithos/debian_base-6.0-7-x86_64.diskdump",
                      img_properties='{"OSFAMILY":"linux"\,"ROOT_PARTITION":"1"}'
                      -t plain --disk 0:size=2G --no-name-check --no-ip-check
                      --net 0:ip=pool,mode=routed,link=public_link
                      --net 1:ip=none,mode=bridged,link=prv1
                      --net 2:ip=none,mode=bridged,link=prv3
                      --net 3:ip=none,mode=bridged,link=prv19
                      testvm5

If everything works as expected, then you have finished the Network Setup at the
backend for both types of Networks (Public & Private).

.. _cyclades-gtools:

Cyclades Ganeti tools
---------------------

In order for Ganeti to be connected with Cyclades later on, we need the
`Cyclades Ganeti tools` available on all Ganeti nodes (node1 & node2 in our
case). You can install them by running in both nodes:

.. code-block:: console

   # apt-get install snf-cyclades-gtools

This will install the following:

 * ``snf-ganeti-eventd`` (daemon to publish Ganeti related messages on RabbitMQ)
 * ``snf-ganeti-hook`` (all necessary hooks under ``/etc/ganeti/hooks``)
 * ``snf-progress-monitor`` (used by ``snf-image`` to publish progress messages)
 * ``kvm-vif-bridge`` (installed under ``/etc/ganeti`` to connect Ganeti with
   NFDHCPD)

Configure ``snf-cyclades-gtools``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The package will install the ``/etc/synnefo/10-snf-cyclades-gtools-backend.conf``
configuration file. At least we need to set the RabbitMQ endpoint for all tools
that need it:

.. code-block:: console

   RABBIT_HOST = "node1.example.com:5672"
   RABBIT_USERNAME = "synnefo"
   RABBIT_PASSWORD = "example_rabbitmq_passw0rd"

The above variables should reflect your :ref:`Message Queue setup
<rabbitmq-setup>`. This file should be editted in all Ganeti nodes.

Connect ``snf-image`` with ``snf-progress-monitor``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Finally, we need to configure ``snf-image`` to publish progress messages during
the deployment of each Image. To do this, we edit ``/etc/default/snf-image`` and
set the corresponding variable to ``snf-progress-monitor``:

.. code-block:: console

   PROGRESS_MONITOR="snf-progress-monitor"

This file should be editted in all Ganeti nodes.

.. _rapi-user:

Synnefo RAPI user
-----------------

As a last step before installing Cyclades, create a new RAPI user that will
have ``write`` access. Cyclades will use this user to issue commands to Ganeti,
so we will call the user ``cyclades`` with password ``example_rapi_passw0rd``.
You can do this, by first running:

.. code-block:: console

   # echo -n 'cyclades:Ganeti Remote API:example_rapi_passw0rd' | openssl md5

and then putting the output in ``/var/lib/ganeti/rapi/users`` as follows:

.. code-block:: console

   cyclades {HA1}55aec7050aa4e4b111ca43cb505a61a0 write

More about Ganeti's RAPI users `here.
<http://docs.ganeti.org/ganeti/2.5/html/rapi.html#introduction>`_

You have now finished with all needed Prerequisites for Cyclades (and
Plankton). Let's move on to the actual Cyclades installation.


Installation of Cyclades (and Plankton) on node1
================================================

This section describes the installation of Cyclades. Cyclades is Synnefo's
Compute service. Plankton (the Image Registry service) will get installed
automatically along with Cyclades, because it is contained in the same Synnefo
component right now.

We will install Cyclades (and Plankton) on node1. To do so, we install the
corresponding package by running on node1:

.. code-block:: console

   # apt-get install snf-cyclades-app

If the package installs successfully, then Cyclades and Plankton are installed
and we proceed with their configuration.


Configuration of Cyclades (and Plankton)
========================================

Conf files
----------

After installing Cyclades, a number of new configuration files will appear under
``/etc/synnefo/`` prefixed with ``20-snf-cyclades-app-``. We will descibe here
only the minimal needed changes to result with a working system. In general, sane
defaults have been chosen for the most of the options, to cover most of the
common scenarios. However, if you want to tweak Cyclades feel free to do so,
once you get familiar with the different options.

Edit ``/etc/synnefo/20-snf-cyclades-app-api.conf``:

.. code-block:: console

   GANETI_MAX_LINK_NUMBER = 20
   ASTAKOS_URL = 'https://node1.example.com/im/authenticate'

The ``GANETI_MAX_LINK_NUMBER`` is used to construct the names of the bridges
already pre-provisioned for the Private Networks. Thus we set it to ``20``, to
reflect our :ref:`Private Networks setup in the host machines
<private-networks-setup>`. These numbers will suffix the
``GANETI_LINK_PREFIX``, which is already set to ``prv`` and doesn't need to be
changed. With those two variables Cyclades will construct the names of the
available bridges ``prv1`` to ``prv20``, which are the real pre-provisioned
bridges in the backend.

The ``ASTAKOS_URL`` denotes the authentication endpoint for Cyclades and is set
to point to Astakos (this should have the same value with Pithos+'s
``PITHOS_AUTHENTICATION_URL``, setup :ref:`previously <conf-pithos>`).

Edit ``/etc/synnefo/20-snf-cyclades-app-backend.conf``:

.. code-block:: console

   GANETI_MASTER_IP = "ganeti.node1.example.com"
   GANETI_CLUSTER_INFO = (GANETI_MASTER_IP, 5080, "cyclades", "example_rapi_passw0rd")

``GANETI_MASTER_IP`` denotes the Ganeti-master's floating IP. We provide the
corresponding domain that resolves to that IP, than the IP itself, to ensure
Cyclades can talk to Ganeti even after a Ganeti master-failover.

``GANETI_CLUSTER_INFO`` is a tuple containing the ``GANETI_MASTER_IP``, the RAPI
port, the RAPI user's username and the RAPI user's password. We set the above to
reflect our :ref:`RAPI User setup <rapi-user>`.

Edit ``/etc/synnefo/20-snf-cyclades-app-cloudbar.conf``:

.. code-block:: console

   CLOUDBAR_LOCATION = 'https://node1.example.com/static/im/cloudbar/'
   CLOUDBAR_ACTIVE_SERVICE = '2'
   CLOUDBAR_SERVICES_URL = 'https://node1.example.com/im/get_services'
   CLOUDBAR_MENU_URL = 'https://account.node1.example.com/im/get_menu'

``CLOUDBAR_LOCATION`` tells the client where to find the Astakos common
cloudbar. The ``CLOUDBAR_SERVICES_URL`` and ``CLOUDBAR_MENU_URL`` options are
used by the Cyclades Web UI to get from Astakos all the information needed to
fill its own cloudbar. So, we put our Astakos deployment urls there. All the
above should have the same values we put in the corresponding variables in
``/etc/synnefo/20-snf-pithos-webclient-cloudbar.conf`` on the previous
:ref:`Pithos configuration <conf-pithos>` section.

The ``CLOUDBAR_ACTIVE_SERVICE`` points to an already registered Astakos
service. You can see all :ref:`registered services <services-reg>` by running
on the Astakos node (node1):

.. code-block:: console

   # snf-manage listservices

The value of ``CLOUDBAR_ACTIVE_SERVICE`` should be the cyclades service's
``id`` as shown by the above command, in our case ``2``.

Edit ``/etc/synnefo/20-snf-cyclades-app-plankton.conf``:

.. code-block:: console

   BACKEND_DB_CONNECTION = 'postgresql://synnefo:example_passw0rd@node1.example.com:5432/snf_pithos'
   BACKEND_BLOCK_PATH = '/srv/pithos/data/'

In this file we configure the Plankton Service. ``BACKEND_DB_CONNECTION``
denotes the Pithos+ database (where the Image files are stored). So we set that
to point to our Pithos+ database. ``BACKEND_BLOCK_PATH`` denotes the actual
Pithos+ data location.

Edit ``/etc/synnefo/20-snf-cyclades-app-queues.conf``:

.. code-block:: console

   RABBIT_HOST = "node1.example.com:5672"
   RABBIT_USERNAME = "synnefo"
   RABBIT_PASSWORD = "example_rabbitmq_passw0rd"

The above settings denote the Message Queue. Those settings should have the same
values as in ``/etc/synnefo/10-snf-cyclades-gtools-backend.conf`` file, and
reflect our :ref:`Message Queue setup <rabbitmq-setup>`.

Edit ``/etc/synnefo/20-snf-cyclades-app-ui.conf``:

.. code-block:: console

   UI_MEDIA_URL = '/static/ui/static/snf/'
   UI_LOGIN_URL = "https://node1.example.com/im/login"
   UI_LOGOUT_URL = "https://node1.example.com/im/logout"

``UI_MEDIA_URL`` denotes the location of the UI's static files.

The ``UI_LOGIN_URL`` option tells the Cyclades Web UI where to redirect users,
if they are not logged in. We point that to Astakos.

The ``UI_LOGOUT_URL`` option tells the Cyclades Web UI where to redirect the
user when he/she logs out. We point that to Astakos, too.

We have now finished with the basic Cyclades and Plankton configuration.

Database Initialization
-----------------------

Once Cyclades is configured, we sync the database:

.. code-block:: console

   $ snf-manage syncdb
   $ snf-manage migrate

and load the initial server flavors:

.. code-block:: console

   $ snf-manage loaddata flavors

If everything returns successfully, our database is ready.

Servers restart
---------------

We also need to restart gunicorn on node1:

.. code-block:: console

   # /etc/init.d/gunicorn restart

Now let's do the final connections of Cyclades with Ganeti.

``snf-dispatcher`` initialization
---------------------------------

``snf-dispatcher`` dispatches all messages published to the Message Queue and
manages the Cyclades database accordingly. It also initializes all exchanges. By
default it is not enabled during installation of Cyclades, so let's enable it in
its configuration file ``/etc/default/snf-dispatcher``:

.. code-block:: console

   SNF_DSPTCH_ENABLE=true

and start the daemon:

.. code-block:: console

   # /etc/init.d/snf-dispatcher start

You can see that everything works correctly by tailing its log file
``/var/log/synnefo/dispatcher.log``.

``snf-ganeti-eventd`` on GANETI MASTER
--------------------------------------

The last step of the Cyclades setup is enabling the ``snf-ganeti-eventd``
daemon (part of the :ref:`Cyclades Ganeti tools <cyclades-gtools>` package).
The daemon is already installed on the GANETI MASTER (node1 in our case).
``snf-ganeti-eventd`` is disabled by default during the ``snf-cyclades-gtools``
installation, so we enable it in its configuration file
``/etc/default/snf-ganeti-eventd``:

.. code-block:: console

   SNF_EVENTD_ENABLE=true

and start the daemon:

.. code-block:: console

   # /etc/init.d/snf-ganeti-eventd start

.. warning:: Make sure you start ``snf-ganeti-eventd`` *ONLY* on GANETI MASTER

If all the above return successfully, then you have finished with the Cyclades
and Plankton installation and setup. Let's test our installation now.


Testing of Cyclades (and Plankton)
==================================


General Testing
===============


Notes
=====
