// responder_agent handles request/reply calls from requester-agent.
//
// Run:
//
//	go run ./scenarios/request_reply/responder_agent
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/ModulationAI/openagentio/pkg/bus"
	"github.com/ModulationAI/openagentio/pkg/event"
	"github.com/ModulationAI/openagentio/pkg/middleware"
	"github.com/ModulationAI/openagentio/pkg/transport/dial"

	example_internal "openagentio-example/internal"
)

type Question struct {
	Text string `json:"text"`
}

type Answer struct {
	Text string `json:"text"`
}

func main() {
	agentId := "responder-agent"
	ctx := context.Background()

	tp, err := transportdial.Dial(ctx, transportdial.WithNATSName(agentId))
	if err != nil {
		fmt.Fprintf(os.Stderr, "transport: %v\n", err)
		os.Exit(1)
	}

	b, err := bus.New(
		bus.WithAgentID(agentId),
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

	if err := b.HandleInvoke("responder-agent", handleQuestion); err != nil {
		fmt.Fprintf(os.Stderr, "register invoke handler: %v\n", err)
		os.Exit(1)
	}
	if err := example_internal.WaitForDemoTransport(tp); err != nil {
		fmt.Fprintf(os.Stderr, "wait for handler: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("[responder-agent] listening for request/reply calls")
	fmt.Println("[responder-agent] start the requester in another terminal:")
	fmt.Println("  go run ./scenarios/request_reply/requester_agent")
	fmt.Println("[responder-agent] press Ctrl+C to exit")

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt, syscall.SIGTERM)
	<-sig
	fmt.Println("[responder-agent] shutting down")
}

func handleQuestion(_ context.Context, e *event.Envelope) (any, error) {
	var question Question
	if err := json.Unmarshal(e.Payload, &question); err != nil {
		return nil, fmt.Errorf("decode request: %w", err)
	}

	fmt.Printf("\n[responder-agent] request from %s: %s\n", e.From, question.Text)

	return Answer{
		Text: "hello from responder-agent",
	}, nil
}
