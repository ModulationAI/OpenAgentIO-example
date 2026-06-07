// publisher_agent publishes an event that subscriber-agent can receive.
//
// Run:
//
//	go run ./scenarios/pub_sub/publisher_agent
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"

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
	agentId := "publisher-agent"
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

	msg := Message{
		From: "publisher-agent",
		Text: "hello from OpenAgentIO pub/sub",
	}
	payload, err := json.Marshal(msg)
	if err != nil {
		fmt.Fprintf(os.Stderr, "encode payload: %v\n", err)
		os.Exit(1)
	}

	env := event.New(messageEvent)
	env.From = msg.From
	env.Payload = payload

	fmt.Printf("[publisher-agent] publishing %q\n", messageEvent)
	fmt.Printf("[publisher-agent] payload: %s\n", payload)

	if err := b.Publish(ctx, env); err != nil {
		fmt.Fprintf(os.Stderr, "publish failed: %v\n", err)
		os.Exit(1)
	}
	if err := example_internal.WaitForDemoTransport(tp); err != nil {
		fmt.Fprintf(os.Stderr, "wait for publish: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("[publisher-agent] message published")
}
