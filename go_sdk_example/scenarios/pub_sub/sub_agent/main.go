// sub_agent simulates a GOC (Incident Response) system that proactively
// publishes incident events to the bus.
//
// In production, GOC would be a long-running monitor that detects anomalies
// and fires alerts. Here we simulate a single incident publish for demo.
//
// Run:
//
//	go run ./examples/scene_example/demo/pub_sub/sub_agent
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"

	"github.com/ModulationAI/openagentio/pkg/bus"
	"github.com/ModulationAI/openagentio/pkg/transport/dial"
	"github.com/ModulationAI/openagentio/pkg/event"
	"github.com/ModulationAI/openagentio/pkg/middleware"
)

// GOCIncidentPayload represents an incident alert from the GOC system.
type GOCIncidentPayload struct {
	IncidentID   string       `json:"incident_id"`
	Severity     string       `json:"severity"`     // P0 / P1 / P2
	Title        string       `json:"title"`
	Description  string       `json:"description"`
	Service      string       `json:"service"`
	Environment  string       `json:"environment"`
	DashboardURL string       `json:"dashboard_url"`
	Actions      []CardAction `json:"actions"`
}

// CardAction represents an interactive button on the DingTalk card.
type CardAction struct {
	ActionID string `json:"action_id"`
	Text     string `json:"text"`
	Type     string `json:"type"` // primary / default
}

func main() {
	agentName := "goc"
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

	// Simulate a GOC incident detection.
	incident := GOCIncidentPayload{
		IncidentID:   "P0-20240517-001",
		Severity:     "P0",
		Title:        "服务 CPU 飙高",
		Description:  "过去5分钟 order-service CPU 使用率 > 90%，错误率上升至 5%",
		Service:      "order-service",
		Environment:  "production",
		DashboardURL: "https://grafana.example.com/d/order-service",
		Actions: []CardAction{
			{ActionID: "claim", Text: "认领处理", Type: "primary"},
			{ActionID: "escalate", Text: "升级", Type: "default"},
			{ActionID: "ignore", Text: "忽略", Type: "default"},
		},
	}

	payload, _ := json.Marshal(incident)

	// Build the event envelope.
	// In production, conversation_token would be injected by Main Agent when
	// assigning monitoring tasks, or looked up from a config store.
	env := event.New("goc.incident.created")
	env.SessionID = incident.IncidentID
	env.TraceID = incident.IncidentID
	env.Metadata = map[string]any{
		"source_system":               "goc",
		"dingtalk.conversation_token": "token_xyz789",
		"dingtalk.sender":             "goc-bot",
		"service":                     incident.Service,
		"severity":                    incident.Severity,
	}
	env.Payload = payload

	fmt.Println("========================================")
	fmt.Println("Demo: SubAgent (GOC) --Publish--> MainAgent")
	fmt.Println("========================================")
	fmt.Printf("\n[GOC] detected incident: %s\n", incident.IncidentID)
	fmt.Printf("  [GOC] severity=%s service=%s\n", incident.Severity, incident.Service)
	fmt.Printf("  [GOC] publishing event: %s\n", env.EventType)

	if err := b.Publish(context.Background(), env); err != nil {
		fmt.Fprintf(os.Stderr, "publish failed: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("  [GOC] incident published successfully (fire-and-forget)")
	fmt.Println("  [GOC] no response expected from MainAgent")
	fmt.Println("\n[GOC] done.")
}
