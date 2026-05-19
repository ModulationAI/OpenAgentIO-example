import React, { useState } from "react";
import { motion } from "framer-motion";
import { Play, Pause, RotateCcw, MessageSquare, Server, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

// 国际化语言包
const translations = {
  zh: {
    scenario: "场景2：Streaming 流式输出调用",
    pause: "暂停",
    play: "播放",
    replay: "重放",
    mainAgentSubtitle: "调用方 / 路由入口",
    subAgentSubtitle: "被调用方 / 流能力 Agent",
    steps: [
      "MainAgent 构造 A2A Protocol",
      "通过 OpenAgentIO stream_invoke 发送请求",
      "SubAgent(Stream) 处理请求并流式返回",
      "连续多个 delta 数据包依次返回",
      "MainAgent 接收完整流式结果",
    ]
  },
  en: {
    scenario: "Scenario 2: Streaming Output Call",
    pause: "Pause",
    play: "Play",
    replay: "Replay",
    mainAgentSubtitle: "Caller / Routing Entry",
    subAgentSubtitle: "Callee / Stream Capability Agent",
    steps: [
      "MainAgent constructs A2A Protocol",
      "Sends request via OpenAgentIO stream_invoke",
      "SubAgent(Stream) processes and streams response",
      "Multiple delta packets return sequentially",
      "MainAgent receives complete stream result",
    ]
  }
} as const;

function AgentCard({ title, subtitle, icon: Icon, side }: { title: string; subtitle: string; icon: React.ElementType; side: "left" | "right" }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: side === "left" ? 0.1 : 0.2 }}
      className={`absolute ${side === "left" ? "left-8" : "right-8"} top-32 w-64 z-10`}
    >
      <Card className="rounded-3xl border border-cyan-100 bg-white/80 shadow-[0_24px_80px_rgba(15,118,110,0.15)] backdrop-blur-xl transition-all duration-300 hover:shadow-[0_32px_100px_rgba(15,118,110,0.2)] hover:-translate-y-1">
        <CardContent className="p-5 !pt-5 h-full flex items-center justify-center">
          <div className="flex items-center justify-center gap-3">
            <div className="rounded-2xl border border-cyan-100 bg-gradient-to-br from-cyan-50 to-blue-50 p-3 shadow-inner flex items-center justify-center">
              <Icon className="h-7 w-7 text-cyan-700" />
            </div>
            <div className="text-center">
              <div className="text-lg font-semibold text-slate-900">{title}</div>
              <div className="text-sm text-slate-500">{subtitle}</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

function MovingA2AProt({ playing, reverse = false, delay = 0, isDelta = false }: { playing: boolean; reverse?: boolean; delay?: number; isDelta?: boolean }) {
  const path = reverse ? "M 760 210 C 620 340, 380 340, 240 210" : "M 240 170 C 380 40, 620 40, 760 170";
  const dotClass = reverse ? "text-emerald-500" : "text-cyan-500";
  const labelClass = reverse ? "text-emerald-700" : "text-cyan-700";
  const dotSize = isDelta ? "6" : "10";
  const fontSize = isDelta ? "11" : "13";
  const label = isDelta ? "delta" : "A2A Prot";

  return (
    <motion.g
      initial={{ opacity: 0 }}
      animate={{ opacity: playing ? 1 : 0.42 }}
      transition={{ delay }}
    >
      <motion.circle
        r={dotSize}
        fill="currentColor"
        className={dotClass}
        style={{
          offsetPath: `path('${path}')`,
          offsetRotate: "0deg",
          filter: isDelta ? "drop-shadow(0 0 8px rgba(16, 185, 129, 0.5))" : "drop-shadow(0 0 14px rgba(34, 211, 238, 0.55))",
        }}
        animate={playing ? { offsetDistance: ["0%", "100%"] } : { offsetDistance: reverse ? "100%" : "0%" }}
        transition={playing ? { duration: isDelta ? 1.8 : 2.4, repeat: Infinity, ease: "easeInOut", delay } : { duration: 0 }}
      />
      <motion.text
        fontSize={fontSize}
        fill="currentColor"
        className={`${labelClass} font-semibold`}
        style={{ offsetPath: `path('${path}')`, offsetRotate: "0deg", transform: isDelta ? "translate(10px, -8px)" : "translate(14px, -12px)" }}
        animate={playing ? { offsetDistance: ["0%", "100%"] } : { offsetDistance: reverse ? "100%" : "0%" }}
        transition={playing ? { duration: isDelta ? 1.8 : 2.4, repeat: Infinity, ease: "easeInOut", delay } : { duration: 0 }}
      >
        {label}
      </motion.text>
    </motion.g>
  );
}

export default function OpenAgentIOStreamingAnimation() {
  const [playing, setPlaying] = useState(true);
  const [key, setKey] = useState(0);
  const [language, setLanguage] = useState<'zh' | 'en'>('zh');

  // 切换语言
  const toggleLanguage = () => {
    setLanguage(prev => prev === 'zh' ? 'en' : 'zh');
  };

  // 获取当前语言的文本
  const t = translations[language];

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
          <div className="absolute -right-20 top-20 h-72 w-72 rounded-full bg-emerald-200/20 blur-3xl" />
          <div className="absolute bottom-10 left-1/2 h-56 w-96 -translate-x-1/2 rounded-full bg-teal-100/30 blur-3xl" />

          <AgentCard side="left" title="MainAgent" subtitle={t.mainAgentSubtitle} icon={MessageSquare} />
          <AgentCard side="right" title="SubAgent(Stream)" subtitle={t.subAgentSubtitle} icon={Server} />


          <svg className="absolute inset-0 h-full w-full z-[15]" viewBox="0 0 1000 520">
            <defs>
              <linearGradient id="requestGradient" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#06b6d4" />
                <stop offset="55%" stopColor="#38bdf8" />
                <stop offset="100%" stopColor="#2563eb" />
              </linearGradient>
              <linearGradient id="streamGradient" x1="1" y1="0" x2="0" y2="0">
                <stop offset="0%" stopColor="#10b981" />
                <stop offset="55%" stopColor="#34d399" />
                <stop offset="100%" stopColor="#059669" />
              </linearGradient>
              <filter id="softGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="5" result="coloredBlur" />
                <feMerge>
                  <feMergeNode in="coloredBlur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              <marker id="arrowRequest" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
                <path d="M0,0 L0,6 L9,3 z" fill="#2563eb" />
              </marker>
              <marker id="arrowStream" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
                <path d="M0,0 L0,6 L9,3 z" fill="#059669" />
              </marker>
            </defs>

            <motion.path
              d="M 240 170 C 380 40, 620 40, 760 170"
              fill="none"
              stroke="url(#requestGradient)"
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeDasharray="9 10"
              markerEnd="url(#arrowRequest)"
              filter="url(#softGlow)"
              animate={playing ? { pathLength: [0.2, 1, 0.2] } : { pathLength: 1 }}
              transition={playing ? { duration: 2.4, repeat: Infinity, ease: "easeInOut" } : { duration: 0 }}
            />
            <motion.path
              d="M 760 210 C 620 340, 380 340, 240 210"
              fill="none"
              stroke="url(#streamGradient)"
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeDasharray="9 10"
              markerEnd="url(#arrowStream)"
              filter="url(#softGlow)"
              animate={playing ? { pathLength: [0.2, 1, 0.2] } : { pathLength: 1 }}
              transition={playing ? { duration: 1.8, repeat: Infinity, ease: "easeInOut", delay: 2.0 } : { duration: 0 }}
            />

            <text x="420" y="62" fontSize="18" fontWeight="700" fill="#0891b2" textAnchor="middle">stream_invoke(request)</text>
            <text x="495" y="344" fontSize="18" fontWeight="700" fill="#047857" textAnchor="middle">stream(delta...)</text>

            {/* 请求数据包 */}
            <MovingA2AProt playing={playing} delay={0} />

            {/* 流式delta数据包，多个依次返回 */}
            <MovingA2AProt playing={playing} reverse delay={2.0} isDelta />
            <MovingA2AProt playing={playing} reverse delay={2.4} isDelta />
            <MovingA2AProt playing={playing} reverse delay={2.8} isDelta />
            <MovingA2AProt playing={playing} reverse delay={3.2} isDelta />
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
                  { duration: 2.4, repeat: Infinity, delay: 0.4 + index * 0.4, ease: "easeInOut" } :
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
