package main

import (
	"log"
	"net"
	"sync"
	"crypto/sha256"
	"fmt"
	"net/http"
	"net/url"
	"io/ioutil"
	"encoding/json"
	"strconv"
	"errors"

	"github.com/nmcclain/ldap"
)

/////////////
// Sample searches you can try against this simple LDAP server:
//
// ldapsearch -H ldap://localhost:3389 -x -b 'dn=test,dn=com'
// ldapsearch -H ldap://localhost:3389 -x -b 'dn=test,dn=com' 'cn=ned'
// ldapsearch -H ldap://localhost:3389 -x -b 'dn=test,dn=com' 'uidnumber=5000'
/////////////

///////////// Run a simple LDAP server
func main() {
	

	go func(){
		s := ldap.NewServer()

		handler := ldapHandler{sessions: make(map[string]session), nextSessionNumber: new(int), lock: &sync.Mutex{}}
		*handler.nextSessionNumber = 1
		s.BindFunc("", handler)
		s.SearchFunc("", handler)
		s.CloseFunc("", handler)
		s.EnforceLDAP = true
		
		listen := "0.0.0.0:3389"
		log.Printf("Starting LDAP server on %s", listen)
		if err := s.ListenAndServe(listen); err != nil {
			log.Fatalf("LDAP Server Failed: %s", err.Error())
		}
	}()
	
	s := ldap.NewServer()
	
	handler := ldapHandler{sessions: make(map[string]session), nextSessionNumber: new(int), lock: &sync.Mutex{}}
	*handler.nextSessionNumber = -1
	s.BindFunc("", handler)
	s.SearchFunc("", handler)
	s.CloseFunc("", handler)
	s.EnforceLDAP = true
	
	listen_tls := "0.0.0.0:6636"
	log.Printf("Starting LDAPS server on %s", listen_tls)
	if err := s.ListenAndServeTLS(listen_tls, "./data/certificate.pem", "./data/key.pem"); err != nil {
		log.Fatalf("LDAPS Server Failed: %s", err.Error())
	}
}

type ldapHandler struct {
	sessions   map[string]session
	nextSessionNumber *int
	lock       *sync.Mutex
}

type session struct {
	id   		string
	conn 		net.Conn
	number	 int
	boundDN  *string
	strand  *string
}

func (h ldapHandler) getSession(conn net.Conn) (session, error) {
	id := connID(conn)
	s, ok := h.sessions[id]
	if !ok {
		s = session{id: id, conn: conn, number: *h.nextSessionNumber, boundDN: new(string), strand: new(string)}
		*s.boundDN = ""
		if *h.nextSessionNumber > 0 {
			*h.nextSessionNumber = *h.nextSessionNumber + 1
		} else {
			*h.nextSessionNumber = *h.nextSessionNumber - 1
		}
		*s.strand = "open[" + strconv.Itoa(s.number) + "] -> "
		h.sessions[s.id] = s
	}
	return s, nil
}


type BindResult struct {
	Result bool `json:"Result"`
	Strand string `json:"Strand"`
}
///////////// Allow anonymous binds only
func (h ldapHandler) Bind(bindDN, bindSimplePw string, conn net.Conn) (ldap.LDAPResultCode, error) {
	h.lock.Lock()
	defer h.lock.Unlock()
	
	s, err := h.getSession(conn)
	if err != nil {
		return ldap.LDAPResultOperationsError, err
	}
	
	//log.Printf("Connection %d binding with bindDN=%s and bindSimplePw=%s", s.number, bindDN, bindSimplePw)
	
	resp, err := http.PostForm("http://localhost:25565/bind", url.Values{
		"connectionNumber": {strconv.Itoa(s.number)},
		"strand": {*s.strand},
		"bindDN": {bindDN},
		"bindSimplePw": {bindSimplePw},
		"boundDN": {*s.boundDN}})
	if err != nil {
		return ldap.LDAPResultOperationsError, err
	}
	defer resp.Body.Close()
	
	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return ldap.LDAPResultOperationsError, err
	}
	
	var result BindResult
	json.Unmarshal(body, &result)
	
	*s.strand = result.Strand
	
	if(result.Result){
		*s.boundDN = bindDN
		return ldap.LDAPResultSuccess, nil
	}
	return ldap.LDAPResultInvalidCredentials, nil
}

func (h ldapHandler) Delete(boundDN, deleteDN string, conn net.Conn) (ldap.LDAPResultCode, error) {
	return ldap.LDAPResultSuccess, nil
}

type Entity struct {
	DN string 											`json:"DN"`
	Attributes map[string][]string	`json:"Attributes"`
}

type SearchResult struct {
	Result bool 			`json:"Result"`
	Entities []Entity `json:"Entities"`
	Strand string `json:"Strand"`
}
///////////// Return some hardcoded search results - we'll respond to any baseDN for testing
func (h ldapHandler) Search(boundDN string, searchReq ldap.SearchRequest, conn net.Conn) (ldap.ServerSearchResult, error) {
	h.lock.Lock()
	defer h.lock.Unlock()
	
	s, err := h.getSession(conn)
	if err != nil {
		return ldap.ServerSearchResult{ResultCode: ldap.LDAPResultOperationsError}, nil
	}
	
	//log.Printf("Connection %d searching with boundDN=%s searchReq.BaseDN=%s searchReq.Filter=%s searchReq.Scope=%d", s.number, boundDN, searchReq.BaseDN, searchReq.Filter, searchReq.Scope)
	
	resp, err := http.PostForm("http://localhost:25565/search", url.Values{
		"connectionNumber": {strconv.Itoa(s.number)},
		"strand": {*s.strand},
		"boundDN": {boundDN},
		"BaseDN": {searchReq.BaseDN}})
	if err != nil {
		return ldap.ServerSearchResult{ResultCode: ldap.LDAPResultOperationsError}, err
	}
	defer resp.Body.Close()
	
	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return ldap.ServerSearchResult{ResultCode: ldap.LDAPResultOperationsError}, err
	}
	
	var result SearchResult
	json.Unmarshal(body, &result)
	
	*s.strand = result.Strand
	
	if(result.Result){
		entries := []*ldap.Entry{}
		for _, entity := range result.Entities {
			attributes := []*ldap.EntryAttribute{}
			for key, value := range entity.Attributes {
				attributes = append(attributes, &ldap.EntryAttribute{key, value})
			}
			entries = append(entries, &ldap.Entry{entity.DN, attributes})
		}
		return ldap.ServerSearchResult{entries, []string{}, []ldap.Control{}, ldap.LDAPResultSuccess}, nil
	}
	
	return ldap.ServerSearchResult{ResultCode: ldap.LDAPResultOther}, errors.New("Search failed")
}

func (h ldapHandler) Close(boundDN string, conn net.Conn) error {
	h.lock.Lock()
	defer h.lock.Unlock()
	
	s, err := h.getSession(conn)
	if err != nil {
		return err
	}
	
	*s.strand = *s.strand + "close"
	log.Printf("%s", *s.strand)
	//log.Printf("Connection %d closing with boundDN=%s", s.number, boundDN)
	
	conn.Close() // close connection to the server when then client is closed
	delete(h.sessions, s.id)
	return nil
}

func connID(conn net.Conn) string {
	h := sha256.New()
	h.Write([]byte(conn.LocalAddr().String() + conn.RemoteAddr().String()))
	sha := fmt.Sprintf("% x", h.Sum(nil))
	return string(sha)
}
