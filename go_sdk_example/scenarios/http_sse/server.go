//go:build server

package main

// server starts an OpenAgentIO Bus with the HTTP/SSE adapter enabled.
// It is mainly used by the browser chat demo in ts_sdk_example/scenarios/sse_client.
// Three targets are registered:
//
//   - echo      : POST /v1/agents/echo/invoke      returns the request payload as-is.
//   - count     : POST /v1/agents/count/stream     emits started + N deltas + final.
//   - assistant : POST /v1/agents/assistant/stream emits text deltas for a chat UI.
//
// Start the server:
//
//	go run -tags=server .

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	nethttp "net/http"
	"os"
	"os/signal"
	"strings"
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

	// Echo returns the request payload as-is.
	if err := b.HandleInvoke("echo", func(_ context.Context, e *event.Envelope) (any, error) {
		logger.Info("echo invoked", "payload", string(e.Payload))
		return json.RawMessage(e.Payload), nil
	}); err != nil {
		fmt.Fprintf(os.Stderr, "register echo: %v\n", err)
		os.Exit(1)
	}

	// Count streams structured frames for low-level SSE checks.
	if err := b.HandleStream("count", func(ctx context.Context, e *event.Envelope, w bus.StreamWriter) error {
		var args struct {
			N       int `json:"n"`
			DelayMS int `json:"delay_ms"`
		}
		if len(e.Payload) > 0 {
			_ = json.Unmarshal(e.Payload, &args)
		}
		if args.N <= 0 {
			args.N = 5
		}
		if args.DelayMS <= 0 {
			args.DelayMS = 600
		}
		if err := w.Started(event.StartedPayload{Meta: map[string]any{
			"model":    "demo-llm",
			"n":        args.N,
			"delay_ms": args.DelayMS,
		}}); err != nil {
			return err
		}
		delay := time.Duration(args.DelayMS) * time.Millisecond
		for i := 0; i < args.N; i++ {
			if err := w.Delta(event.DeltaPayload{Data: map[string]any{"i": i}}); err != nil {
				return err
			}
			select {
			case <-time.After(delay):
			case <-ctx.Done():
				return ctx.Err()
			}
		}
		return w.Final(event.FinalPayload{Result: map[string]any{"total": args.N}})
	}); err != nil {
		fmt.Fprintf(os.Stderr, "register count: %v\n", err)
		os.Exit(1)
	}

	// Assistant streams text chunks for the browser chat demo.
	if err := b.HandleStream("assistant", func(ctx context.Context, e *event.Envelope, w bus.StreamWriter) error {
		var args struct {
			Message string `json:"message"`
			DelayMS int    `json:"delay_ms"`
		}
		if len(e.Payload) > 0 {
			_ = json.Unmarshal(e.Payload, &args)
		}
		if strings.TrimSpace(args.Message) == "" {
			args.Message = "How does OpenAgentIO streaming work?"
		}
		if args.DelayMS <= 0 {
			args.DelayMS = 140
		}

		reply := fmt.Sprintf(
			"OpenAgentIO streams this reply over Server-Sent Events. Your message was: %q. Each chunk arrives as an agent.response.delta frame, so the browser can render the answer as it is generated.",
			args.Message,
		)
		chunks := chunkWords(reply, 3)

		if err := w.Started(event.StartedPayload{Meta: map[string]any{
			"agent":    "assistant",
			"delay_ms": args.DelayMS,
		}}); err != nil {
			return err
		}

		delay := time.Duration(args.DelayMS) * time.Millisecond
		for _, chunk := range chunks {
			if err := w.Delta(event.DeltaPayload{Delta: chunk}); err != nil {
				return err
			}
			select {
			case <-time.After(delay):
			case <-ctx.Done():
				return ctx.Err()
			}
		}

		return w.Final(event.FinalPayload{Result: map[string]any{"text": reply}})
	}); err != nil {
		fmt.Fprintf(os.Stderr, "register assistant: %v\n", err)
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

func chunkWords(text string, size int) []string {
	words := strings.Fields(text)
	if len(words) == 0 {
		return nil
	}
	if size <= 0 {
		size = 1
	}

	chunks := make([]string, 0, (len(words)+size-1)/size)
	for i := 0; i < len(words); i += size {
		end := i + size
		if end > len(words) {
			end = len(words)
		}
		chunk := strings.Join(words[i:end], " ")
		if end < len(words) {
			chunk += " "
		}
		chunks = append(chunks, chunk)
	}
	return chunks
}
