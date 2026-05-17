// Package internal provides shared utilities for the scene_example demos.
package example_internal

import (
	"encoding/json"
	"fmt"

	"github.com/ModulationAI/openagentio/pkg/event"
)

// DingTalkMessage represents a message received from the DingTalk AI assistant.
type DingTalkMessage struct {
	Sender             string `json:"sender"`
	ThreadID           string `json:"threadId"`
	OpenConversationID string `json:"openConversationId"`
	RunID              string `json:"runId"`
	ConversationToken  string `json:"conversationToken"`
	Content            string `json:"content"`
}

// ToEnvelope converts a DingTalkMessage into an ACP Envelope with proper
// field mapping:
//   - sender       -> UserID + metadata["dingtalk.sender"]
//   - threadId     -> SessionID
//   - openConversationId -> ConversationID + metadata["dingtalk.chat_id"]
//   - runId        -> TraceID
//   - conversationToken -> metadata["dingtalk.conversation_token"]
//   - content      -> Payload
func (m DingTalkMessage) ToEnvelope() *event.Envelope {
	env := event.New(event.MessageReceived)
	env.UserID = m.Sender
	env.SessionID = m.ThreadID
	env.ConversationID = m.OpenConversationID
	env.TraceID = m.RunID
	env.Metadata = map[string]any{
		"dingtalk.sender":             m.Sender,
		"dingtalk.chat_id":            m.OpenConversationID,
		"dingtalk.conversation_token": m.ConversationToken,
	}
	if m.Content != "" {
		payload, _ := json.Marshal(map[string]string{"content": m.Content})
		env.Payload = payload
	}
	return env
}

// PrintEnvelopeContext prints trace/session/correlation metadata for observability.
func PrintEnvelopeContext(label string, e *event.Envelope) {
	fmt.Printf("  [%s] EventType=%s EventID=%s\n", label, e.EventType, e.EventID)
	fmt.Printf("  [%s] TraceID=%s SessionID=%s CorrelationID=%s\n", label, e.TraceID, e.SessionID, e.CorrelationID)
	if e.UserID != "" {
		fmt.Printf("  [%s] UserID=%s\n", label, e.UserID)
	}
	if e.ConversationID != "" {
		fmt.Printf("  [%s] ConversationID=%s\n", label, e.ConversationID)
	}
	if len(e.Metadata) > 0 {
		fmt.Printf("  [%s] Metadata=%v\n", label, e.Metadata)
	}
}
