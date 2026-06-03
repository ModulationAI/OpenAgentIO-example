//go:build server

package main

// server starts an OpenAgentIO Bus + HTTP/SSE adapter so external clients can
// drive agents over REST and SSE. Two handlers are registered:
//
//   - echo  : POST /v1/agents/echo/invoke   returns the request payload as-is.
//   - count : POST /v1/agents/count/stream  emits started + N deltas + final.
//
// Start the server:  go run -tags=server .
//
// curl -sS -X POST localhost:8080/v1/agents/echo/invoke \
//      -H 'Content-Type: application/json' \
//      -d '{"msg":"hi"}'
//
// curl -sN -X POST localhost:8080/v1/agents/count/stream \
//      -H 'Content-Type: application/json' \
//      -d '{"n":3}'

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	nethttp "net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	httpadapter "github.com/ModulationAI/openagentio/pkg/adapter/http"
	"github.com/ModulationAI/openagentio/pkg/bus"
	"github.com/ModulationAI/openagentio/pkg/event"
	"github.com/ModulationAI/openagentio/pkg/middleware"
	"github.com/ModulationAI/openagentio/pkg/transport/inmem"
)

func main() {
	logger := slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))

	b, err := bus.New(
		bus.WithAgentID("sse-server"),
		bus.WithTransport(inmem.New()),
		bus.WithLogger(logger),
		bus.WithMiddleware(
			middleware.Recover(),
			middleware.Trace(),
			middleware.Logging(logger),
		),
	)
	if err != nil {
		fmt.Fprintf(os.Stderr, "bus init failed: %v\n", err)
		os.Exit(1)
	}
	defer b.Close()

	// Echo handler — synchronous invoke returns payload as-is.
	if err := b.HandleInvoke("echo", func(_ context.Context, e *event.Envelope) (any, error) {
		logger.Info("echo invoked", "payload", string(e.Payload))
		return json.RawMessage(e.Payload), nil
	}); err != nil {
		fmt.Fprintf(os.Stderr, "register echo: %v\n", err)
		os.Exit(1)
	}

	// Count handler — streaming with started/delta/final frames.
	if err := b.HandleStream("count", func(ctx context.Context, e *event.Envelope, w bus.StreamWriter) error {
		var args struct {
			N int `json:"n"`
		}
		if len(e.Payload) > 0 {
			_ = json.Unmarshal(e.Payload, &args)
		}
		if args.N <= 0 {
			args.N = 5
		}
		if err := w.Started(event.StartedPayload{Meta: map[string]any{"model": "demo-llm", "n": args.N}}); err != nil {
			return err
		}
		for i := 0; i < args.N; i++ {
			if err := w.Delta(event.DeltaPayload{Data: map[string]any{"i": i}}); err != nil {
				return err
			}
			select {
			case <-time.After(150 * time.Millisecond):
			case <-ctx.Done():
				return ctx.Err()
			}
		}
		return w.Final(event.FinalPayload{Result: map[string]any{"total": args.N}})
	}); err != nil {
		fmt.Fprintf(os.Stderr, "register count: %v\n", err)
		os.Exit(1)
	}

	adapter := httpadapter.New(b,
		httpadapter.WithLogger(logger),
		httpadapter.WithTimeout(30*time.Second),
		httpadapter.WithIdleTimeout(10*time.Second),
		httpadapter.WithMiddleware(
			httpadapter.Recover(logger),
			httpadapter.Logging(logger),
		),
	)

	addr := ":9080"
	if v := os.Getenv("ADDR"); v != "" {
		addr = v
	}
	srv := &nethttp.Server{
		Addr:              addr,
		Handler:           adapter,
		ReadHeaderTimeout: 5 * time.Second,
	}

	idleConnsClosed := make(chan struct{})
	go func() {
		sig := make(chan os.Signal, 1)
		signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)
		<-sig
		logger.Info("shutting down")
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = srv.Shutdown(shutdownCtx)
		close(idleConnsClosed)
	}()

	logger.Info("sse-server listening", "addr", addr)
	if err := srv.ListenAndServe(); err != nil && err != nethttp.ErrServerClosed {
		fmt.Fprintf(os.Stderr, "listen: %v\n", err)
		os.Exit(1)
	}
	<-idleConnsClosed
}