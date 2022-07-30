#!/bin/sh

(guix pack -S /guix-profile=. -m manifest.scm | xargs -i cp {} ./Daniel-Authenticator-Web-tarball-pack.tar.gz) && chmod +w ./Daniel-Authenticator-Web-tarball-pack.tar.gz


