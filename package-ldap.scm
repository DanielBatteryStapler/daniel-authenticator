(use-modules (guix packages)
	(guix gexp)
	((guix licenses) #:prefix license:)
	(guix build-system go)
	(guix git-download))

(define-public go-github-com-nmcclain-asn1-ber
  (package
    (name "go-github-com-nmcclain-asn1-ber")
    (version "0.0.0-20170104154839-2661553a0484")
    (source
      (origin
        (method git-fetch)
        (uri (git-reference
               (url "https://github.com/nmcclain/asn1-ber")
               (commit (go-version->git-ref version))))
        (file-name (git-file-name name version))
        (sha256
          (base32 "1p7lbkhb08nmwwbkbcq6hfnndad6aajj55h5fil245d3fa9wd7yd"))))
    (build-system go-build-system)
    (arguments '(#:import-path "github.com/nmcclain/asn1-ber"))
    (home-page "https://github.com/nmcclain/asn1-ber")
    (synopsis #f)
    (description #f)
    (license license:bsd-3)))

(define-public go-github-com-nmcclain-ldap
  (package
    (name "go-github-com-nmcclain-ldap")
    (version "0.0.0-20210720162743-7f8d1e44eeba")
    (source
      (origin
        (method git-fetch)
        (uri (git-reference
               (url "https://github.com/nmcclain/ldap")
               (commit (go-version->git-ref version))))
        (file-name (git-file-name name version))
        (sha256
          (base32 "0y8fb4biw7df26yfkf7hnk0ccmxyxc1qbnbakdkidkdg7d09za39"))))
    (build-system go-build-system)
    (arguments '(#:import-path "github.com/nmcclain/ldap"
                  #:tests? #f))
    (propagated-inputs
      `(("go-github-com-nmcclain-asn1-ber" ,go-github-com-nmcclain-asn1-ber)))
    (home-page "https://github.com/nmcclain/ldap")
    (synopsis "LDAP for Golang")
    (description
      "This library provides basic LDAP v3 functionality for the GO programming language.")
    (license license:bsd-3)))

(package
	(name "Daniel-Authenticator-LDAP")
	(version "0.0")
	(inputs '())
	(native-inputs '())
	(propagated-inputs `(("go-github-com-nmcclain-ldap" ,go-github-com-nmcclain-ldap)))
	(source (local-file "./src-ldap" #:recursive? #t))
	(build-system go-build-system)
    (arguments '(#:import-path "daniel-authenticator-ldap"))
	(synopsis "Daniel-Authenticator: simple LDAP authenticator for home-servers")
	(description
		"Daniel-Authenticator allows you to manage user authentication for all services over LDAP.")
	(home-page "https://github.com/DanielBatteryStapler/daniel-authenticator")
	(license license:agpl3+))

