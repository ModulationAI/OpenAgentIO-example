import React, { useState } from "react";
import { motion } from "framer-motion";
import { Play, Pause, RotateCcw, MessageSquare, Server, Globe, Wrench, Bot, FileCode } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const translations = {
  zh: {
    scenario: "场景8：A2A 函数调用模式",
    pause: "暂停",
    play: "播放",
    replay: "重放",
    callerSubtitle: "caller-agent / 调用方",
    toolSubtitle: "tool-agent / 工具分发",
    llmTitle: "LLM Planner",
    llmSubtitle: "可选：选择函数名与参数",
    registryTitle: "远程能力注册表",
    registrySubtitle: "函数元数据",
    requestLabel: "FunctionCall",
    responseLabel: "FunctionResult",
    tools: [
      { name: "函数签名", args: "name + typed arguments", result: "schema" },
      { name: "Prompt 描述", args: "什么时候调用这个远程能力", result: "intent" },
    ],
    steps: [
      "用户意图进入 caller-agent",
      "LLM 选择远程函数能力",
      "OpenAgentIO 发送结构化调用",
      "tool-agent 远程执行能力",
      "结构化结果返回调用方",
    ],
  },
  en: {
    scenario: "Scenario 8: A2A Function Invocation Pattern",
    pause: "Pause",
    play: "Play",
    replay: "Replay",
    callerSubtitle: "caller-agent / Caller",
    toolSubtitle: "tool-agent / Tool Dispatcher",
    llmTitle: "LLM Planner",
    llmSubtitle: "Optional: chooses name and arguments",
    registryTitle: "Remote Capability Registry",
    registrySubtitle: "Function metadata",
    requestLabel: "FunctionCall",
    responseLabel: "FunctionResult",
    tools: [
      { name: "Function signature", args: "name + typed arguments", result: "schema" },
      { name: "Prompt description", args: "when to call this remote capability", result: "intent" },
    ],
    steps: [
      "User intent enters caller-agent",
      "LLM selects a remote function capability",
      "OpenAgentIO sends a structured call",
      "tool-agent executes the remote capability",
      "Structured result returns to caller",
    ],
  },
} as const;

function AgentCard({ title, subtitle, icon: Icon, side }: { title: string; subtitle: string; icon: React.ElementType; side: "left" | "right" }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: side === "left" ? 0.1 : 0.2 }}
      className={`absolute ${side === "left" ? "left-12" : "right-12"} top-28 w-64 z-10`}
    >
      <Card className="rounded-3xl border border-cyan-100 bg-white/80 shadow-[0_24px_80px_rgba(15,118,110,0.15)] backdrop-blur-xl transition-all duration-300 hover:shadow-[0_32px_100px_rgba(15,118,110,0.2)] hover:-translate-y-1">
        <CardContent className="p-5 !pt-5 h-full flex items-center justify-center">
          <div className="flex items-center justify-center gap-3">
            <div className="rounded-2xl border border-cyan-100 bg-gradient-to-br from-cyan-50 to-blue-50 p-3 shadow-inner flex items-center justify-center">
              <Icon className="h-7 w-7 text-cyan-700" />
            </div>
            <div className="text-center min-w-0 overflow-hidden">
              <div className="text-lg font-semibold text-slate-900 whitespace-nowrap overflow-hidden text-ellipsis">{title}</div>
              <div className="text-sm text-slate-500 whitespace-nowrap overflow-hidden text-ellipsis">{subtitle}</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

function ToolRegistry({ playing, title, subtitle, tools }: { playing: boolean; title: string; subtitle: string; tools: readonly { name: string; args: string; result: string }[] }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.25 }}
      className="absolute right-8 top-56 z-20 w-72"
    >
      <Card className="overflow-hidden rounded-2xl border border-teal-100 bg-white/85 shadow-[0_18px_52px_rgba(20,184,166,0.14)] backdrop-blur-xl">
        <CardContent className="p-3 !pt-3">
          <div className="mb-2.5 flex items-center gap-2.5">
            <div className="rounded-xl border border-teal-100 bg-teal-50 p-2 shadow-inner">
              <Wrench className="h-4 w-4 text-teal-700" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-semibold text-slate-900">{title}</div>
              <div className="truncate text-[11px] font-medium text-slate-500">{subtitle}</div>
            </div>
          </div>
          <div className="grid gap-1.5">
            {tools.map((tool, index) => {
              const Icon = index === 0 ? FileCode : MessageSquare;
              return (
                <motion.div
                  key={tool.name}
                  animate={playing ? { borderColor: ["#ccfbf1", "#14b8a6", "#ccfbf1"], backgroundColor: ["rgba(255,255,255,0.8)", "rgba(240,253,250,0.95)", "rgba(255,255,255,0.8)"] } : {}}
                  transition={playing ? { duration: 2.8, repeat: Infinity, delay: 0.7 + index * 1.15, ease: "easeInOut" } : { duration: 0 }}
                  className="overflow-hidden rounded-xl border border-teal-100 bg-white/80 px-2.5 py-1.5 shadow-sm"
                >
                  <div className="flex min-w-0 items-center gap-2 overflow-hidden">
                    <Icon className="h-3.5 w-3.5 shrink-0 text-teal-700" />
                    <div className="min-w-0 flex-1 overflow-hidden leading-tight">
                      <div className="block max-w-full truncate text-xs font-semibold text-slate-900">{tool.name}</div>
                      <div className="truncate text-[10px] text-slate-500">{tool.args}</div>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

function LlmPlanner({ playing, title, subtitle }: { playing: boolean; title: string; subtitle: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
      className="absolute left-16 top-56 z-20 w-56"
    >
      <motion.div
        animate={playing ? { y: [0, -4, 0], boxShadow: ["0 10px 28px rgba(37,99,235,0.12)", "0 18px 44px rgba(37,99,235,0.2)", "0 10px 28px rgba(37,99,235,0.12)"] } : { y: 0 }}
        transition={playing ? { duration: 3.1, repeat: Infinity, ease: "easeInOut" } : { duration: 0 }}
        className="rounded-2xl border border-blue-100 bg-white/85 px-3.5 py-3 backdrop-blur-xl"
      >
        <div className="flex items-center gap-2.5">
          <div className="rounded-xl border border-blue-100 bg-blue-50 p-2 shadow-inner">
            <Bot className="h-4 w-4 text-blue-700" />
          </div>
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold text-slate-900">{title}</div>
            <div className="truncate text-xs font-medium text-slate-500">{subtitle}</div>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}

function MovingPacket({ path, label, delay, playing, colorClass }: { path: string; label: string; delay: number; playing: boolean; colorClass: string }) {
  return (
    <motion.g initial={{ opacity: 0 }} animate={{ opacity: playing ? 1 : 0.45 }} transition={{ delay }}>
      <motion.circle
        r="10"
        fill="currentColor"
        className={colorClass}
        style={{
          offsetPath: `path('${path}')`,
          offsetRotate: "0deg",
          filter: "drop-shadow(0 0 14px rgba(20, 184, 166, 0.55))",
        }}
        animate={playing ? { offsetDistance: ["0%", "100%"] } : { offsetDistance: "0%" }}
        transition={playing ? { duration: 2.6, repeat: Infinity, ease: "easeInOut", delay } : { duration: 0 }}
      />
      <motion.text
        fontSize="13"
        fill="currentColor"
        className="font-semibold text-slate-700"
        style={{ offsetPath: `path('${path}')`, offsetRotate: "0deg", transform: "translate(14px, -12px)" }}
        animate={playing ? { offsetDistance: ["0%", "100%"] } : { offsetDistance: "0%" }}
        transition={playing ? { duration: 2.6, repeat: Infinity, ease: "easeInOut", delay } : { duration: 0 }}
      >
        {label}
      </motion.text>
    </motion.g>
  );
}

export default function FunctionCallingAnimation() {
  const [playing, setPlaying] = useState(true);
  const [key, setKey] = useState(0);
  const [language, setLanguage] = useState<'zh' | 'en'>('zh');

  const toggleLanguage = () => {
    setLanguage(prev => prev === 'zh' ? 'en' : 'zh');
  };

  const t = translations[language];
  const requestPath = "M 260 155 C 365 35, 635 35, 740 155";
  const dispatchPath = "M 740 205 C 625 330, 375 330, 260 205";

  return (
    <div
      className="min-h-screen w-full p-8 text-slate-900"
      style={{
        background:
          "radial-gradient(circle at 50% 18%, rgba(255,255,255,0.98) 0%, rgba(241,250,252,0.96) 38%, rgba(232,244,248,0.94) 72%, rgba(221,235,241,0.92) 100%)",
      }}
    >
      <div className="pointer-events-none fixed inset-0 opacity-[0.55]" style={{ backgroundImage: "radial-gradient(rgba(14, 165, 233, 0.12) 1px, transparent 1px)", backgroundSize: "32px 32px" }} />

      <div className="relative mx-auto max-w-6xl">
        <div className="mb-6 flex items-center justify-between gap-4">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="text-sm font-medium uppercase tracking-widest text-cyan-700">OpenAgentIO · A2A Communication Base</div>
            <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-950">{t.scenario}</h1>
          </motion.div>
          <motion.div
            className="flex gap-2"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <Button onClick={() => setPlaying(!playing)} className="rounded-2xl">
              {playing ? <Pause className="mr-2 h-4 w-4" /> : <Play className="mr-2 h-4 w-4" />}
              {playing ? t.pause : t.play}
            </Button>
            <Button variant="outline" onClick={() => setKey(key + 1)} className="rounded-2xl">
              <RotateCcw className="mr-2 h-4 w-4" />{t.replay}
            </Button>
            <Button variant="outline" onClick={toggleLanguage} className="rounded-2xl">
              <Globe className="mr-2 h-4 w-4" />
              {language === 'zh' ? 'EN' : '中'}
            </Button>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="relative h-[520px] overflow-hidden rounded-[2rem] border border-white/80 shadow-[0_28px_100px_rgba(15,118,110,0.18)] backdrop-blur-xl"
          style={{
            background:
              "radial-gradient(circle at 50% 28%, rgba(255,255,255,0.96) 0%, rgba(248,253,255,0.9) 42%, rgba(235,248,252,0.82) 100%)",
          }}
          key={key}
        >
          <div className="absolute -left-20 top-16 h-72 w-72 rounded-full bg-cyan-200/20 blur-3xl" />
          <div className="absolute -right-20 top-20 h-72 w-72 rounded-full bg-blue-200/20 blur-3xl" />
          <div className="absolute bottom-10 left-1/2 h-56 w-96 -translate-x-1/2 rounded-full bg-teal-100/30 blur-3xl" />

          <AgentCard side="left" title="caller-agent" subtitle={t.callerSubtitle} icon={MessageSquare} />
          <AgentCard side="right" title="tool-agent" subtitle={t.toolSubtitle} icon={Server} />
          <LlmPlanner playing={playing} title={t.llmTitle} subtitle={t.llmSubtitle} />
          <ToolRegistry playing={playing} title={t.registryTitle} subtitle={t.registrySubtitle} tools={t.tools} />

          <svg className="absolute inset-0 h-full w-full z-[15]" viewBox="0 0 1000 520">
            <defs>
              <linearGradient id="functionCallGradient" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#06b6d4" />
                <stop offset="55%" stopColor="#38bdf8" />
                <stop offset="100%" stopColor="#2563eb" />
              </linearGradient>
              <linearGradient id="functionResultGradient" x1="1" y1="0" x2="0" y2="0">
                <stop offset="0%" stopColor="#10b981" />
                <stop offset="55%" stopColor="#2dd4bf" />
                <stop offset="100%" stopColor="#0d9488" />
              </linearGradient>
              <filter id="functionSoftGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="5" result="coloredBlur" />
                <feMerge>
                  <feMergeNode in="coloredBlur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              <marker id="functionCallArrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
                <path d="M0,0 L0,6 L9,3 z" fill="#2563eb" />
              </marker>
              <marker id="functionResultArrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
                <path d="M0,0 L0,6 L9,3 z" fill="#0d9488" />
              </marker>
            </defs>

            <motion.path
              d={requestPath}
              fill="none"
              stroke="url(#functionCallGradient)"
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeDasharray="9 10"
              markerEnd="url(#functionCallArrow)"
              filter="url(#functionSoftGlow)"
              animate={playing ? { pathLength: [0.2, 1, 0.2], opacity: [0.45, 1, 0.45] } : { pathLength: 1, opacity: 0.75 }}
              transition={playing ? { duration: 2.6, repeat: Infinity, ease: "easeInOut" } : { duration: 0 }}
            />
            <motion.path
              d={dispatchPath}
              fill="none"
              stroke="url(#functionResultGradient)"
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeDasharray="9 10"
              markerEnd="url(#functionResultArrow)"
              filter="url(#functionSoftGlow)"
              animate={playing ? { pathLength: [0.2, 1, 0.2], opacity: [0.45, 1, 0.45] } : { pathLength: 1, opacity: 0.75 }}
              transition={playing ? { duration: 2.6, repeat: Infinity, ease: "easeInOut", delay: 1.3 } : { duration: 0 }}
            />

            <text x="455" y="58" fontSize="18" fontWeight="700" fill="#0891b2" textAnchor="middle">
              {language === 'zh' ? '结构化函数调用' : 'structured function call'}
            </text>
            <text x="505" y="350" fontSize="18" fontWeight="700" fill="#0f766e" textAnchor="middle">
              {language === 'zh' ? '远程执行结果' : 'remote execution result'}
            </text>

            <MovingPacket path={requestPath} label="call #1" delay={0} playing={playing} colorClass="text-cyan-500" />
            <MovingPacket path={requestPath} label="call #2" delay={1.3} playing={playing} colorClass="text-blue-500" />
            <MovingPacket path={dispatchPath} label={t.responseLabel} delay={1.3} playing={playing} colorClass="text-teal-500" />
            <MovingPacket path={dispatchPath} label="result: 12" delay={2.6} playing={playing} colorClass="text-emerald-500" />
          </svg>

          <div className="absolute bottom-6 left-8 right-8 grid grid-cols-5 gap-3 z-10">
            {t.steps.map((step, index) => (
              <motion.div
                key={`${language}-${index}`}
                initial={{ opacity: 0, y: 16 }}
                animate={playing ?
                  { y: [0, -6, 0], opacity: [0.7, 1, 0.7], scale: [1, 1.02, 1] } :
                  { y: 0, opacity: 0.9, scale: 1 }
                }
                transition={playing ?
                  { duration: 3.2, repeat: Infinity, delay: 0.35 + index * 0.35, ease: "easeInOut" } :
                  { duration: 0.5, delay: 0.4 + index * 0.1 }
                }
                className="rounded-2xl border border-cyan-100 bg-white/75 p-3 text-sm shadow-[0_12px_40px_rgba(14,165,233,0.1)] backdrop-blur transition-all duration-200 hover:shadow-[0_16px_50px_rgba(14,165,233,0.15)] hover:-translate-y-1"
              >
                <div className="mb-1 text-xs font-semibold text-cyan-700">STEP {index + 1}</div>
                <div className="font-medium text-slate-800">{step}</div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </div>
  );
}
