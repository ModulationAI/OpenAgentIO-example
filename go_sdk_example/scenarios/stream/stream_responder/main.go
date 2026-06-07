// stream_responder handles streaming requests and sends response chunks.
//
// Run:
//
//	go run ./scenarios/stream/stream_responder
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/ModulationAI/openagentio/pkg/bus"
	"github.com/ModulationAI/openagentio/pkg/event"
	"github.com/ModulationAI/openagentio/pkg/middleware"
	"github.com/ModulationAI/openagentio/pkg/transport/dial"

	example_internal "openagentio-example/internal"
)

type Prompt struct {
	Text string `json:"text"`
}

func main() {
	agentId := "stream-responder"
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

	if err := b.HandleStream("stream-responder", handlePrompt); err != nil {
		fmt.Fprintf(os.Stderr, "register stream handler: %v\n", err)
		os.Exit(1)
	}
	if err := example_internal.WaitForDemoTransport(tp); err != nil {
		fmt.Fprintf(os.Stderr, "wait for handler: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("[stream-responder] listening for streaming calls")
	fmt.Println("[stream-responder] start the requester in another terminal:")
	fmt.Println("  go run ./scenarios/stream/stream_requester")
	fmt.Println("[stream-responder] press Ctrl+C to exit")

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt, syscall.SIGTERM)
	<-sig
	fmt.Println("[stream-responder] shutting down")
}

func handlePrompt(ctx context.Context, e *event.Envelope, w bus.StreamWriter) error {
	var prompt Prompt
	if err := json.Unmarshal(e.Payload, &prompt); err != nil {
		return fmt.Errorf("decode prompt: %w", err)
	}

	fmt.Printf("\n[stream-responder] prompt from %s: %s\n", e.From, prompt.Text)

	if err := w.Started(event.StartedPayload{Meta: map[string]any{"agent": "stream-responder"}}); err != nil {
		return err
	}

	chunks := []string{"hello ", "from ", "stream-responder"}
	for _, chunk := range chunks {
		if err := ctx.Err(); err != nil {
			return err
		}
		if err := w.Delta(event.DeltaPayload{Delta: chunk}); err != nil {
			return err
		}
		time.Sleep(200 * time.Millisecond)
	}

	return w.Final(event.FinalPayload{Result: map[string]any{
		"text": "hello from stream-responder",
	}})
}
