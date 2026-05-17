// main_agent is the consumer that subscribes to GOC incident events
// and simulates sending DingTalk interactive cards.
//
// It demonstrates the SubAgent → MainAgent reverse event flow:
//   GOC publishes "goc.incident.created" → MainAgent subscribes and handles.
//
// Run:
//
//	go run ./examples/scene_example/demo/pub_sub/main_agent
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
	"github.com/ModulationAI/openagentio/pkg/transport/dial"
	"github.com/ModulationAI/openagentio/pkg/event"
	"github.com/ModulationAI/openagentio/pkg/middleware"

	internal "openagentio-example/internal"
)

// GOCIncidentPayload mirrors the struct published by the GOC sub_agent.
type GOCIncidentPayload struct {
	IncidentID   string       `json:"incident_id"`
	Severity     string       `json:"severity"`
	Title        string       `json:"title"`
	Description  string       `json:"description"`
	Service      string       `json:"service"`
	Environment  string       `json:"environment"`
	DashboardURL string       `json:"dashboard_url"`
	Actions      []CardAction `json:"actions"`
}

type CardAction struct {
	ActionID string `json:"action_id"`
	Text     string `json:"text"`
	Type     string `json:"type"`
}

func main() {
	appName := "main_agent"
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

	ctx := context.Background()

	// Subscribe to GOC incident events with a queue group for load-balancing.
	sub, err := b.Subscribe(ctx, "goc.incident.created", handleIncident, bus.WithQueue("main-workers"))
	if err != nil {
		fmt.Fprintf(os.Stderr, "subscribe: %v\n", err)
		os.Exit(1)
	}
	defer sub.Unsubscribe()

	fmt.Println("[MainAgent] subscribed to goc.incident.created")
	fmt.Println("[MainAgent] queue group: main-workers")
	fmt.Println("[MainAgent] press Ctrl+C to exit")

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt, syscall.SIGTERM)
	<-sig
	fmt.Println("[MainAgent] shutting down...")
}

func handleIncident(ctx context.Context, e *event.Envelope) error {
	fmt.Printf("\n[MainAgent] received event: %s event_id=%s\n", e.EventType, e.EventID)
	internal.PrintEnvelopeContext("MainAgent", e)

	// Parse incident payload.
	var incident GOCIncidentPayload
	if len(e.Payload) > 0 {
		_ = json.Unmarshal(e.Payload, &incident)
	}

	fmt.Printf("[MainAgent] incident: %s [%s] %s\n", incident.IncidentID, incident.Severity, incident.Title)
	fmt.Printf("[MainAgent] service=%s env=%s\n", incident.Service, incident.Environment)

	// Simulate enrichment / decision making.
	fmt.Println("[MainAgent] enriching incident context...")
	time.Sleep(300 * time.Millisecond)

	// Simulate sending a DingTalk interactive card.
	simulateDingTalkCard(e, incident)

	fmt.Println("[MainAgent] incident handling completed")
	return nil
}

func simulateDingTalkCard(e *event.Envelope, incident GOCIncidentPayload) {
	token := ""
	if e.Metadata != nil {
		if v, ok := e.Metadata["dingtalk.conversation_token"].(string); ok {
			token = v
		}
	}

	// Build an interactive card payload (simplified).
	card := map[string]any{
		"msgtype": "interactive",
		"interactive": map[string]any{
			"title": map[string]string{"content": fmt.Sprintf("[%s] %s", incident.Severity, incident.Title)},
			"text":  map[string]string{"content": incident.Description},
			"callbackURL": "https://your-bot.example.com/callback",
		},
	}
	cardJSON, _ := json.MarshalIndent(card, "", "  ")

	fmt.Println("[MainAgent] ┌─────────────────────────────────────┐")
	fmt.Println("[MainAgent] │  Simulating: DingTalk Card Push     │")
	fmt.Println("[MainAgent] └─────────────────────────────────────┘")
	fmt.Printf("[MainAgent] POST /v1.0/im/chat/messages/send\n")
	fmt.Printf("[MainAgent] Authorization: Bearer %s\n", token)
	fmt.Printf("[MainAgent] Body:\n%s\n", string(cardJSON))
	fmt.Println("[MainAgent] DingTalk API response: 200 OK (simulated)")
}
