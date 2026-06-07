// stream_requester sends a streaming request to stream-responder.
//
// Run:
//
//	go run ./scenarios/stream/stream_requester
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"time"

	"github.com/ModulationAI/openagentio/pkg/bus"
	"github.com/ModulationAI/openagentio/pkg/event"
	"github.com/ModulationAI/openagentio/pkg/middleware"
	"github.com/ModulationAI/openagentio/pkg/transport/dial"
)

type Prompt struct {
	Text string `json:"text"`
}

func main() {
	agentId := "stream-requester"
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

	prompt := Prompt{Text: "stream a short greeting"}

	fmt.Println("[stream-requester] invoking stream-responder")
	fmt.Printf("[stream-requester] prompt: %s\n", prompt.Text)

	stream, err := b.StreamInvoke(ctx, "stream-responder", prompt,
		bus.WithTimeout(15*time.Second),
		bus.WithIdleTimeout(3*time.Second),
	)
	if err != nil {
		fmt.Fprintf(os.Stderr, "stream invoke failed: %v\n", err)
		os.Exit(1)
	}
	defer stream.Close()

	fmt.Print("[stream-requester] response: ")
	for frame, err := range stream.Events() {
		if err != nil {
			fmt.Fprintf(os.Stderr, "\nstream error: %v\n", err)
			os.Exit(1)
		}

		switch frame.EventType {
		case event.ResponseDelta:
			var payload event.DeltaPayload
			if err := json.Unmarshal(frame.Payload, &payload); err != nil {
				fmt.Fprintf(os.Stderr, "\ndecode delta: %v\n", err)
				os.Exit(1)
			}
			fmt.Print(payload.Delta)
		case event.ResponseFinal:
			fmt.Println()
			fmt.Printf("[stream-requester] final payload: %s\n", frame.Payload)
		}
	}
}
