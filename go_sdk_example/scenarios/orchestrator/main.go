// orchestrator runs all agents in a single process using an in-memory transport.
//
// This is a convenience entrypoint for local zero-dependency testing.
// In production / distributed deployments, each agent runs as an independent
// process (see cmd/echo_agent, cmd/stream_agent, cmd/main_agent,
// cmd/access_layer) and connects to a shared NATS cluster.
//
// Run:
//
//	go run ./examples/scene_example/cmd/orchestrator
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/ModulationAI/openagentio/pkg/bus"
	"github.com/ModulationAI/openagentio/pkg/event"
	"github.com/ModulationAI/openagentio/pkg/middleware"
	"github.com/ModulationAI/openagentio/pkg/transport/inmem"

	internal "openagentio-example/internal"
)

func main() {
	// In single-process mode, all agents share the same in-memory driver
	// so they can communicate without an external message broker.
	driver := inmem.New()

	// Echo Agent
	echoBus, err := bus.New(
		bus.WithAgentID("echo-agent"),
		bus.WithTransport(driver),
		bus.WithMiddleware(middleware.Recover(), middleware.Trace()),
	)
	if err != nil {
		fmt.Fprintf(os.Stderr, "echo bus: %v\n", err)
		os.Exit(1)
	}
	defer echoBus.Close()
	if err := echoBus.HandleInvoke("echo", func(_ context.Context, e *event.Envelope) (any, error) {
		var req struct{ Content string `json:"content"` }
		if len(e.Payload) > 0 {
			_ = json.Unmarshal(e.Payload, &req)
		}
		fmt.Printf("  [EchoAgent] received request: trace_id=%s session_id=%s content=%q\n",
			e.TraceID, e.SessionID, req.Content)
		return map[string]string{"reply": "Echo: " + req.Content}, nil
	}); err != nil {
		fmt.Fprintf(os.Stderr, "register echo: %v\n", err)
		os.Exit(1)
	}

	// Stream Agent
	streamBus, err := bus.New(
		bus.WithAgentID("stream-agent"),
		bus.WithTransport(driver),
		bus.WithMiddleware(middleware.Recover(), middleware.Trace()),
	)
	if err != nil {
		fmt.Fprintf(os.Stderr, "stream bus: %v\n", err)
		os.Exit(1)
	}
	defer streamBus.Close()
	if err := streamBus.HandleStream("stream", func(ctx context.Context, e *event.Envelope, w bus.StreamWriter) error {
		fmt.Printf("  [StreamAgent] received stream request: trace_id=%s session_id=%s\n",
			e.TraceID, e.SessionID)

		var req struct{ Content string `json:"content"` }
		if len(e.Payload) > 0 {
			_ = json.Unmarshal(e.Payload, &req)
		}
		if req.Content == "" {
			req.Content = "Hello, world!"
		}

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
		fmt.Fprintf(os.Stderr, "register stream: %v\n", err)
		os.Exit(1)
	}

	// Main Agent
	mainBus, err := bus.New(
		bus.WithAgentID("main-agent"),
		bus.WithTransport(driver),
		bus.WithMiddleware(middleware.Recover(), middleware.Trace()),
	)
	if err != nil {
		fmt.Fprintf(os.Stderr, "main bus: %v\n", err)
		os.Exit(1)
	}
	defer mainBus.Close()

	if err := mainBus.HandleInvoke("main-agent", func(ctx context.Context, e *event.Envelope) (any, error) {
		fmt.Println("  [MainAgent] received invoke request")
		internal.PrintEnvelopeContext("MainAgent", e)
		fmt.Println("  [MainAgent] forwarding to echo-agent...")
		resp, err := mainBus.Invoke(ctx, "echo", e)
		if err != nil {
			return nil, err
		}
		fmt.Println("  [MainAgent] received response from echo-agent")
		internal.PrintEnvelopeContext("MainAgent<-echo", resp)
		return resp, nil
	}); err != nil {
		fmt.Fprintf(os.Stderr, "register main invoke: %v\n", err)
		os.Exit(1)
	}

	if err := mainBus.HandleStream("main-agent-stream", func(ctx context.Context, e *event.Envelope, w bus.StreamWriter) error {
		fmt.Println("  [MainAgent] received stream request")
		internal.PrintEnvelopeContext("MainAgent", e)
		fmt.Println("  [MainAgent] forwarding to stream-agent...")
		stream, err := mainBus.StreamInvoke(ctx, "stream", e)
		if err != nil {
			return err
		}
		defer stream.Close()

		fmt.Println("  [MainAgent] proxying stream frames from stream-agent...")
		for frame, err := range stream.Events() {
			if err != nil {
				return err
			}
			switch frame.EventType {
			case event.ResponseStarted:
				var meta map[string]any
				if len(frame.Payload) > 0 {
					_ = json.Unmarshal(frame.Payload, &meta)
				}
				if err := w.Started(meta); err != nil {
					return err
				}
			case event.ResponseDelta:
				var chunk map[string]string
				if len(frame.Payload) > 0 {
					_ = json.Unmarshal(frame.Payload, &chunk)
				}
				if err := w.Delta(chunk); err != nil {
					return err
				}
			case event.ResponseFinal:
				var result map[string]any
				if len(frame.Payload) > 0 {
					_ = json.Unmarshal(frame.Payload, &result)
				}
				return w.Final(result)
			case event.ResponseError:
				var ep event.ErrorPayload
				if len(frame.Payload) > 0 {
					_ = json.Unmarshal(frame.Payload, &ep)
				}
				return w.Error(fmt.Errorf("%s: %s", ep.Code, ep.Message))
			}
		}
		return nil
	}); err != nil {
		fmt.Fprintf(os.Stderr, "register main stream: %v\n", err)
		os.Exit(1)
	}

	// Access Layer
	accessBus, err := bus.New(
		bus.WithAgentID("access-layer"),
		bus.WithTransport(driver),
		bus.WithMiddleware(middleware.Recover(), middleware.Trace()),
	)
	if err != nil {
		fmt.Fprintf(os.Stderr, "access bus: %v\n", err)
		os.Exit(1)
	}
	defer accessBus.Close()

	msg := internal.DingTalkMessage{
		Sender:             "user_12345",
		ThreadID:           "thread_abc",
		OpenConversationID: "conv_67890",
		RunID:              "run_001",
		ConversationToken:  "token_xyz789",
		Content:            "Hello, Agentic World!",
	}

	// Scenario 1: Request-Reply
	fmt.Println("========================================")
	fmt.Println("Scenario 1: Request-Reply (sync invoke)")
	fmt.Println("========================================")
	fmt.Printf("\n[AccessLayer] invoking main-agent\n")
	fmt.Printf("  [AccessLayer] dingtalk content: %q\n", msg.Content)

	resp, err := accessBus.Invoke(context.Background(), "main-agent", msg.ToEnvelope(), bus.WithTimeout(10*time.Second))
	if err != nil {
		fmt.Fprintf(os.Stderr, "scenario 1 failed: %v\n", err)
		os.Exit(1)
	}
	fmt.Println("\n[AccessLayer] received final response")
	internal.PrintEnvelopeContext("AccessLayer", resp)
	fmt.Printf("  [AccessLayer] response payload: %s\n", string(resp.Payload))

	// Scenario 2: Streaming
	fmt.Println("\n========================================")
	fmt.Println("Scenario 2: Streaming (token-by-token)")
	fmt.Println("========================================")
	fmt.Printf("\n[AccessLayer] stream-invoking main-agent-stream\n")
	fmt.Printf("  [AccessLayer] dingtalk content: %q\n", msg.Content)

	stream, err := accessBus.StreamInvoke(context.Background(), "main-agent-stream", msg.ToEnvelope(),
		bus.WithTimeout(30*time.Second),
		bus.WithIdleTimeout(2*time.Second),
	)
	if err != nil {
		fmt.Fprintf(os.Stderr, "scenario 2 failed: %v\n", err)
		os.Exit(1)
	}
	defer stream.Close()

	fmt.Println("\n[AccessLayer] consuming stream frames...")
	for frame, err := range stream.Events() {
		if err != nil {
			fmt.Fprintf(os.Stderr, "scenario 2 failed: %v\n", err)
			os.Exit(1)
		}
		fmt.Printf("  [AccessLayer] frame Seq=%d Type=%s IsFinal=%v Payload=%s\n",
			frame.Seq, frame.EventType, frame.IsFinal, string(frame.Payload))
	}
	fmt.Println("[AccessLayer] stream closed")

	fmt.Println("\nAll scenarios completed successfully.")
}
