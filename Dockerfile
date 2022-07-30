FROM alpine

COPY Daniel-Authenticator-Web-tarball-pack.tar.gz /tmp/
RUN tar -xf /tmp/Daniel-Authenticator-Web-tarball-pack.tar.gz && rm /tmp/Daniel-Authenticator-Web-tarball-pack.tar.gz

WORKDIR /
ENV PATH="/guix-profile/bin/:${PATH}"
ENV LD_LIBRARY_PATH="/guix-profile/lib/:${LD_LIBRARY_PATH}"
CMD ["/guix-profile/bin/daniel-authenticator-connector"]

# HTTP port
EXPOSE 8080

# LDAP port
EXPOSE 3389

# LDAPS port
EXPOSE 6636

