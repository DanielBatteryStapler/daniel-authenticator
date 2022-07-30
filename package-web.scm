(use-modules (guix packages)
	(guix gexp)
	((guix licenses) #:prefix license:)
	(guix build-system python)
	(gnu packages python-web)
	(gnu packages python-crypto)
	(gnu packages tls))

(package
	(name "Daniel-Authenticator-Web")
	(version "0.0")
	(inputs
		(list python-passlib python-flask-wtf))
	(native-inputs '())
	(propagated-inputs
		(list python-flask gunicorn openssl (load "./package-ldap.scm")))
	(source (local-file "./src-web" #:recursive? #t))
	(build-system python-build-system)
	(arguments `(#:phases
		(modify-phases %standard-phases
			(replace 'check
				(lambda _
					(invoke "python3" "-m" "unittest" "discover" "-v"))))))
	(synopsis "Daniel-Authenticator: simple LDAP authenticator for home-servesr")
	(description
		"Daniel-Authenticator allows you to manage user authentication for all services over LDAP.")
	(home-page "https://github.com/DanielBatteryStapler/daniel-authenticator")
	(license license:agpl3+))

