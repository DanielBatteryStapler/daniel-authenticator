# Daniel-Authenticator

Daniel-Authenticator is a self-hosted LDAP authentication server with a
a web interface for both administration and user self-service. It is targeted for home servers that
need a way for different services to authenticate, using LDAP, against a single list of users with
strict per-user-per-service access controls. While it can fulfill some of the same roles as something
like FreeIPA or OpenLDAP, it is much simplier and does only what it needs to -- perfect for
self-hosting.

It also supports using a declarative database, which is perfect for using as a test server for
LDAP clients.

It is built on top of nmcclain's excellent [ldap library](https://github.com/nmcclain/ldap) which
provides all of the LDAP protocol functionality.

## Installation

The easiest way to use is as a docker container, it is available on dockerhub as
``danielbatterystapler/daniel-authenticator:latest``. An example ``docker-compose.yml`` file is available
in the repo.

In declarative database more you can setup all users, services, and groups w or use normal databse mode with the CLI interface to
create the initial admin user and use that account for user management.
The example file uses a declarative database.

## Environment Variables

Necessary:
 * ``DANIEL_AUTHENTICATOR_SECRET_KEY`` Used by python flask for the web interface, must be
set to a secret, random series of characters.

Optional:
 * ``DANIEL_AUTHENTICATOR_DECLARATIVE_DATABASE`` set to a multi-line string of commands to specify the data
within the database. Further modification of the database is disabled when
this variable is set. See ``docker-compose.yml`` for an example.


## Build from Source

The project is configured as two guix packages, one that depends on the other. The main package is
``package-web.scm`` and can be built using guix: ``guix build -f package-web.scm``.
The docker container expects to consume the build binaries in the form of a "pack". This pack
can be created and automatically copied to the correct location using ``./makePack.sh``.
You can also run it without docker using guix, an example is in the ``./run.sh`` file.

## LDAP

Daniel-Authenticator is not a full LDAP database. From the LDAP side it is read-only and all
modification requests will be denied. All data is stored in a SQLite database and is only translated
into LDAP objects on request. LDAP queries are meant to be made by different "services" and each
service has its own service "user" -- separate from regular users. Each service has its own view of
the user and group list, only seeing the users and groups that are a part of that service.
If a user or group is not in that service, then to that service that user or group does not exist.

Ports: ``3389``(unencrypted) or ``6636``(self-signed cert)
Bind DNs and search bases are listed in that service's page in the admin web interface;
each service has a different search base so that it only sees its sub-set of users.
Anonymous searchs are not permitted.

Users have type "user" and groups have type "group". Services are never returned as LDAP objects.

## CLI

Daniel-Authenticator comes with a cli interface for doing basic user manipulation -- perfect for
making your initial admin user or resetting your admin user's password.
It can be envoked using ``daniel-authenticator-cli`` within the docker container.
Here is the output of ``daniel-authenticator-cli help``
```
Usage: daniel-authenticator-cli SUBCOMMAND [ARGUMENT]...

Valid subcommands:
	create_user USERNAME FULLNAME EMAIL PASSWORD
	set_user_password USERNAME PASSWORD
	set_user_password_using_freeipa_hash USERNAME PASSWORD_HASH
	unlock USERNAME
	superuser USERNAME
	set_user_uuid USERNAME UUID
	
	create_service SERVICE_USERNAME FULLNAME HYPERLINK PASSWORD
	set_service_password_using_freeipa_hash SERVICE_USERNAME PASSWORD_HASH
	
	create_group GROUP_USERNAME FULLNAME
	set_group_uuid GROUP_USERNAME UUID
	
	add_user_to_service USERNAME SERVICE_USERNAME
	add_user_to_group USERNAME GROUP_USERNAME
	add_group_to_service GROUP_USERNAME SERVICE_USERNAME
```

These same subcommands are also used for declarative database mode.

## Declarative Database

Daniel-Authenticator supports using a "declarative database" i.e. all of the users, groups, and
services are set once on startup -- completely wiping any previous data -- and then never modified.
This is done by setting the ``DANIEL_AUTHENTICATOR_DECLARATIVE_DATABASE`` environment variables to a 
list of subcommands. See ``docker-compose.yml`` file for an example of this mode
