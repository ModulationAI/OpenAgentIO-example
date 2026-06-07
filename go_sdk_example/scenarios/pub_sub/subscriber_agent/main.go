// subscriber_agent subscribes to events from publisher-agent.
//
// Run:
//
//	go run ./scenarios/pub_sub/subscriber_agent
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

const messageEvent = "agent.message.created"

type Message struct {
	From string `json:"from"`
	Text string `json:"text"`
}

func main() {
	agentId := "subscriber-agent"
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

	sub, err := b.Subscribe(ctx, messageEvent, handleMessage)
	if err != nil {
		fmt.Fprintf(os.Stderr, "subscribe: %v\n", err)
		os.Exit(1)
	}
	defer sub.Unsubscribe()

	if err := example_internal.WaitForDemoTransport(tp); err != nil {
		fmt.Fprintf(os.Stderr, "wait for subscription: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("[subscriber-agent] subscribed to %q\n", messageEvent)
	fmt.Println("[subscriber-agent] start the publisher in another terminal:")
	fmt.Println("  go run ./scenarios/pub_sub/publisher_agent")
	fmt.Println("[subscriber-agent] press Ctrl+C to exit")

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt, syscall.SIGTERM)
	<-sig
	fmt.Println("[subscriber-agent] shutting down")
}

func handleMessage(_ context.Context, e *event.Envelope) error {
	var msg Message
	if err := json.Unmarshal(e.Payload, &msg); err != nil {
		return fmt.Errorf("decode payload: %w", err)
	}

	fmt.Printf("\n[subscriber-agent] received %q\n", e.EventType)
	fmt.Printf("[subscriber-agent] event_id=%s trace_id=%s\n", e.EventID, e.TraceID)
	fmt.Printf("[subscriber-agent] message from %s: %s\n", msg.From, msg.Text)
	return nil
}
