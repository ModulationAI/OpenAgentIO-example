package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/ModulationAI/openagentio/pkg/bus"
	"github.com/ModulationAI/openagentio/pkg/transport/dial"
	"github.com/ModulationAI/openagentio/pkg/event"
	"github.com/ModulationAI/openagentio/pkg/middleware"

	internal "openagentio-example/internal"
)

func main() {
	appName := "subAgent"
	tp, err := transportdial.Dial(context.Background(), transportdial.WithNATSName(appName))
	if err != nil {
		fmt.Fprintf(os.Stderr, "transport: %v\n", err)
		os.Exit(1)
	}

	b, err := bus.New(
		bus.WithAgentID(appName),
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

	// Invoke handler: proxies to echo-agent by target name.
	if err := b.HandleInvoke("mainAgent", func(ctx context.Context, e *event.Envelope) (any, error) {
		fmt.Printf("[MainAgent] received invoke request: trace_id=%s session_id=%s\n",
			e.TraceID, e.SessionID)
		internal.PrintEnvelopeContext("mainAgent", e)

		fmt.Println("[MainAgent] forwarding to echo-agent...")
		resp, err := b.Invoke(ctx, "echo", e)
		if err != nil {
			return nil, err
		}

		fmt.Println("[MainAgent] received response from echo-agent")
		internal.PrintEnvelopeContext("MainAgent<-echo", resp)
		return resp, nil
	}); err != nil {
		fmt.Fprintf(os.Stderr, "register invoke handler: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("[MainAgent] running... targets=main-agent, main-agent-stream")
	fmt.Println("[MainAgent] press Ctrl+C to exit")

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt, syscall.SIGTERM)
	<-sig
	fmt.Println("[MainAgent] shutting down...")
}
