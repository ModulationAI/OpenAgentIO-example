// sub_agent is the server that receives stream requests from main_agent.
//
// It registers a HandleStream on "sub-agent-stream" and produces
// token-by-token output directly (simulating an LLM). No further
// delegation to downstream agents.
//
// Run:
//
//	go run ./examples/scene_example/demo/stream/sub_agent
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/ModulationAI/openagentio/pkg/bus"
	"github.com/ModulationAI/openagentio/pkg/transport/dial"
	"github.com/ModulationAI/openagentio/pkg/event"
	"github.com/ModulationAI/openagentio/pkg/middleware"

	internal "openagentio-example/internal"
)

func main() {
	agentName := "subAgent"
	tp, err := transportdial.Dial(context.Background(), transportdial.WithNATSName(agentName))
	if err != nil {
		fmt.Fprintf(os.Stderr, "transport: %v\n", err)
		os.Exit(1)
	}

	b, err := bus.New(
		bus.WithAgentID(agentName),
		bus.WithTransport(tp),
		bus.WithMiddleware(
			middleware.Recover(),
			middleware.Trace(),
		),
	)
	if err != nil {
		fmt.Fprintf(os.Stderr, "bus: %v\n", err)
		os.Exit(1)
	}
	defer b.Close()

	if err := b.HandleStream("sub-agent-stream", func(ctx context.Context, e *event.Envelope, w bus.StreamWriter) error {
		fmt.Printf("[SubAgent] received stream request: trace_id=%s session_id=%s\n",
			e.TraceID, e.SessionID)
		internal.PrintEnvelopeContext("SubAgent", e)

		// Parse request content.
		var req struct{ Content string `json:"content"` }
		if len(e.Payload) > 0 {
			_ = json.Unmarshal(e.Payload, &req)
		}
		if req.Content == "" {
			req.Content = "Hello, world!"
		}

		fmt.Printf("[SubAgent] generating stream response for content=%q\n", req.Content)

		// Simulate LLM: Started → Delta tokens → Final.
		if err := w.Started(map[string]any{"model": "fake-llm-v1", "prompt": req.Content}); err != nil {
			return err
		}

		tokens := strings.Split("The quick brown fox jumps over the lazy dog .", " ")
		for _, tok := range tokens {
			select {
			case <-ctx.Done():
				return ctx.Err()
			default:
			}
			if err := w.Delta(map[string]string{"token": tok + " "}); err != nil {
				return err
			}
			time.Sleep(50 * time.Millisecond)
		}

		return w.Final(map[string]any{
			"text":  strings.Join(tokens, " ") + " ",
			"usage": map[string]int{"tokens": len(tokens)},
		})
	}); err != nil {
		fmt.Fprintf(os.Stderr, "register stream handler: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("[SubAgent] running... target=sub-agent-stream")
	fmt.Println("[SubAgent] press Ctrl+C to exit")

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt, syscall.SIGTERM)
	<-sig
	fmt.Println("[SubAgent] shutting down...")
}
