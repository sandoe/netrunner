package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

func TestAuthenticate(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/auth/me" || r.Header.Get("Authorization") != "Bearer valid" {
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}
		_ = json.NewEncoder(w).Encode(AuthUser{Username: "teacher", Role: "analyst"})
	}))
	defer server.Close()

	old := os.Getenv("BACKEND_HOST")
	t.Cleanup(func() { _ = os.Setenv("BACKEND_HOST", old) })
	_ = os.Setenv("BACKEND_HOST", server.URL)

	if _, err := authenticate(""); err == nil {
		t.Fatal("missing token must be rejected")
	}
	if _, err := authenticate("bad"); err == nil {
		t.Fatal("invalid token must be rejected")
	}
	user, err := authenticate("valid")
	if err != nil {
		t.Fatalf("valid token rejected: %v", err)
	}
	if user.Username != "teacher" || user.Role != "analyst" {
		t.Fatalf("unexpected user: %#v", user)
	}
}

func TestStudentCannotUseTerminal(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_ = json.NewEncoder(w).Encode(AuthUser{Username: "student", Role: "student"})
	}))
	defer server.Close()

	old := os.Getenv("BACKEND_HOST")
	t.Cleanup(func() { _ = os.Setenv("BACKEND_HOST", old) })
	_ = os.Setenv("BACKEND_HOST", server.URL)

	if _, err := authenticate("student-token"); err == nil {
		t.Fatal("student terminal access must be rejected")
	}
}
