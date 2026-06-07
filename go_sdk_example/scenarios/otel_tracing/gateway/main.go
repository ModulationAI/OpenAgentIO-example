// gateway-agent receives calculation requests and delegates to backend-agent.
//
// Run:
//
//	go run ./scenarios/otel_tracing/gateway
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
	otelmiddleware "github.com/ModulationAI/openagentio/pkg/middleware/otel"
	transportdial "github.com/ModulationAI/openagentio/pkg/transport/dial"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.27.0"
	"go.opentelemetry.io/otel/trace"

	example_internal "openagentio-example/internal"
)

type CalcRequest struct {
	A  int    `json:"a"`
	B  int    `json:"b"`
	Op string `json:"op"`
}

type CalcResponse struct {
	Result int    `json:"result"`
	Agent  string `json:"agent"`
}

func main() {
	shutdown := initTracer("gateway-agent")
	defer shutdown()

	ctx := context.Background()

	agentId := "gateway-agent"
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
			otelmiddleware.Trace(),
		),
		bus.WithEnvelopePreparer(
			otelmiddleware.EnvelopePreparer(),
		),
	)
	if err != nil {
		fmt.Fprintf(os.Stderr, "bus: %v\n", err)
		os.Exit(1)
	}
	defer b.Close()

	if err := b.HandleInvoke("gateway-agent", func(ctx context.Context, e *event.Envelope) (any, error) {
		return handleGateway(ctx, b, e)
	}); err != nil {
		fmt.Fprintf(os.Stderr, "register gateway-agent: %v\n", err)
		os.Exit(1)
	}

	if err := example_internal.WaitForDemoTransport(tp); err != nil {
		fmt.Fprintf(os.Stderr, "wait for handlers: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("[gateway-agent] listening for calculation requests")
	fmt.Println("[gateway-agent] will delegate to backend-agent")
	fmt.Println("[gateway-agent] press Ctrl+C to exit")

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt, syscall.SIGTERM)
	<-sig
	fmt.Println("[gateway-agent] shutting down")
}

func handleGateway(ctx context.Context, b bus.Bus, e *event.Envelope) (any, error) {
	var req CalcRequest
	if err := json.Unmarshal(e.Payload, &req); err != nil {
		return nil, fmt.Errorf("decode request: %w", err)
	}

	// Create a child span for the delegation work.
	ctx, span := otel.Tracer("gateway-agent").Start(ctx, "gateway.delegate",
		trace.WithAttributes(
			attribute.Int("calc.a", req.A),
			attribute.Int("calc.b", req.B),
			attribute.String("calc.op", req.Op),
		))
	defer span.End()

	fmt.Printf("[gateway-agent] delegating %d %s %d to backend-agent\n", req.A, req.Op, req.B)

	resp, err := b.Invoke(ctx, "backend-agent", req, bus.WithTimeout(5*time.Second))
	if err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		return nil, fmt.Errorf("delegate to backend-agent failed: %w", err)
	}

	var result CalcResponse
	if err := json.Unmarshal(resp.Payload, &result); err != nil {
		return nil, fmt.Errorf("decode backend response: %w", err)
	}

	result.Agent = "gateway-agent -> " + result.Agent
	return result, nil
}

func initTracer(serviceName string) func() {
	ctx := context.Background()

	endpoint := os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
	if endpoint == "" {
		endpoint = "localhost:4317"
	}

	exp, err := otlptracegrpc.New(ctx,
		otlptracegrpc.WithEndpoint(endpoint),
		otlptracegrpc.WithInsecure(),
	)
	if err != nil {
		panic(fmt.Sprintf("failed to create OTLP exporter: %v", err))
	}

	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exp),
		sdktrace.WithResource(resource.NewWithAttributes(
			semconv.SchemaURL,
			semconv.ServiceNameKey.String(serviceName),
		)),
	)

	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.TraceContext{})

	return func() {
		_ = tp.Shutdown(ctx)
	}
}
