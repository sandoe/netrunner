FROM golang:1.24-alpine AS builder

WORKDIR /app

# Install git for fetching dependencies
RUN apk add --no-cache git

COPY go.mod ./
# If there were a go.sum, we would copy it here
RUN go mod download

COPY . .
RUN go mod tidy
RUN go test ./... && CGO_ENABLED=0 GOOS=linux go build -o /terminal-mux .

FROM alpine:3.22

WORKDIR /app
COPY --from=builder /terminal-mux /terminal-mux

EXPOSE 8081

CMD ["/terminal-mux"]
