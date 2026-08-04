package main

import (
	"net/http/httptest"
	"testing"
)

func TestAgentRequestAuthorized(t *testing.T) {
	previous := authToken
	authToken = "test-agent-token"
	t.Cleanup(func() { authToken = previous })

	tests := []struct {
		name   string
		header string
		want   bool
	}{
		{name: "missing", want: false},
		{name: "wrong scheme", header: "Basic test-agent-token", want: false},
		{name: "wrong token", header: "Bearer wrong", want: false},
		{name: "valid", header: "Bearer test-agent-token", want: true},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			req := httptest.NewRequest("POST", "/serial/write", nil)
			if tc.header != "" {
				req.Header.Set("Authorization", tc.header)
			}
			if got := agentRequestAuthorized(req); got != tc.want {
				t.Fatalf("agentRequestAuthorized() = %v, want %v", got, tc.want)
			}
		})
	}
}
