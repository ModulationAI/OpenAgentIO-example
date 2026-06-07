// backend-agent performs the actual calculation.
//
// Run:
//
//	go run ./scenarios/otel_tracing/backend
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
	otelmiddleware "github.com/ModulationAI/openagentio/pkg/middleware/otel"
	transportdial "github.com/ModulationAI/openagentio/pkg/transport/dial"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
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
	shutdown := initTracer("backend-agent")
	defer shutdown()

	ctx := context.Background()

	agentId := "backend-agent"
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

	if err := b.HandleInvoke("backend-agent", handleCalc); err != nil {
		fmt.Fprintf(os.Stderr, "register backend-agent: %v\n", err)
		os.Exit(1)
	}

	if err := example_internal.WaitForDemoTransport(tp); err != nil {
		fmt.Fprintf(os.Stderr, "wait for handlers: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("[backend-agent] listening for calculation requests")
	fmt.Println("[backend-agent] press Ctrl+C to exit")

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt, syscall.SIGTERM)
	<-sig
	fmt.Println("[backend-agent] shutting down")
}

func handleCalc(ctx context.Context, e *event.Envelope) (any, error) {
	var req CalcRequest
	if err := json.Unmarshal(e.Payload, &req); err != nil {
		return nil, fmt.Errorf("decode request: %w", err)
	}

	tr := otel.Tracer("backend-agent")
	_, span := tr.Start(ctx, "backend.calculate",
		trace.WithAttributes(
			attribute.Int("calc.a", req.A),
			attribute.Int("calc.b", req.B),
			attribute.String("calc.op", req.Op),
		))
	defer span.End()

	var result int
	switch req.Op {
	case "add":
		result = req.A + req.B
	case "mul":
		result = req.A * req.B
	default:
		return nil, fmt.Errorf("unsupported op: %s", req.Op)
	}

	fmt.Printf("[backend-agent] calculated %d %s %d = %d\n", req.A, req.Op, req.B, result)

	return CalcResponse{
		Result: result,
		Agent:  "backend-agent",
	}, nil
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
