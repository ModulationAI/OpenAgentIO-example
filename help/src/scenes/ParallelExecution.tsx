import React, { useState } from "react";
import { motion } from "framer-motion";
import { Play, Pause, RotateCcw, MessageSquare, Server, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

// 国际化语言包
const translations = {
  zh: {
    scenario: "场景4：Parallel Execution 并行调用模式",
    pause: "暂停",
    play: "播放",
    replay: "重放",
    mainAgentSubtitle: "调用方 / 协程调度入口",
    subAgentSubtitle: "被调用方 / 并行执行单元",
    aggregateSubtitle: "结果聚合 / 统一返回",
    steps: [
      "MainAgent 构造并行调用请求",
      "同时发起三个异步invoke调用",
      "多个SubAgent并行独立处理",
      "所有调用完成后收集结果",
      "聚合响应返回给调用方",
    ]
  },
  en: {
    scenario: "Scenario 4: Parallel Execution Pattern",
    pause: "Pause",
    play: "Play",
    replay: "Replay",
    mainAgentSubtitle: "Caller / Coroutine Scheduler",
    subAgentSubtitle: "Callee / Parallel Execution Unit",
    aggregateSubtitle: "Result Aggregation / Unified Return",
    steps: [
      "MainAgent constructs parallel call requests",
      "Initiates three async invoke calls simultaneously",
      "Multiple SubAgents process independently in parallel",
      "Collect results after all calls complete",
      "Aggregate response returns to caller",
    ]
  }
} as const;

function AgentCard({ title, subtitle, icon: Icon, className = "" }: { title: string; subtitle: string; icon: React.ElementType; className?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.1 }}
      className={`absolute ${className} w-64 z-10`}
    >
      <Card className="rounded-3xl border border-cyan-100 bg-white/80 shadow-[0_24px_80px rgba(15,118,110,0.15)] backdrop-blur-xl transition-all duration-300 hover:shadow-[0_32px_100px rgba(15,118,110,0.2)] hover:-translate-y-1">
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

function SubAgentCard({ title, subtitle, index, playing }: { title: string; subtitle: string; index: number; playing: boolean }) {
  // 三个SubAgent不同的颜色主题，保持和整体色调协调
  const colorThemes = [
    {
      icon: "text-cyan-600",
      border: "border-cyan-300",
      statusBg: "bg-cyan-50",
      statusBorder: "border-cyan-200",
      statusText: "text-cyan-700",
      glow: "0 0 25px rgba(6, 182, 212, 0.45)"
    },
    {
      icon: "text-emerald-600",
      border: "border-emerald-300",
      statusBg: "bg-emerald-50",
      statusBorder: "border-emerald-200",
      statusText: "text-emerald-700",
      glow: "0 0 25px rgba(16, 185, 129, 0.45)"
    },
    {
      icon: "text-purple-600",
      border: "border-purple-300",
      statusBg: "bg-purple-50",
      statusBorder: "border-purple-200",
      statusText: "text-purple-700",
      glow: "0 0 25px rgba(168, 85, 247, 0.45)"
    }
  ];

  const theme = colorThemes[index];

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{
        opacity: 1,
        y: 0,
        scale: playing ? [1, 1.08, 1.02, 1] : 1,
        boxShadow: playing ? ["none", theme.glow, theme.glow, "none"] : "none"
      }}
      transition={{ duration: 3.2, delay: 0.2 + index * 0.1 }}
      className={`w-60 z-10`}
    >
      <Card className={`rounded-2xl border ${theme.border} bg-white/80 shadow-lg backdrop-blur-xl`}>
        <CardContent className="p-4 !pt-4 h-full flex items-center justify-center">
          <div className="flex items-center gap-2.5">
            <div className="rounded-xl border border-cyan-100 bg-gradient-to-br from-cyan-50 to-blue-50 p-2 shadow-inner flex items-center justify-center">
              <Server className={`h-5 w-5 ${theme.icon}`} />
            </div>
            <div className="text-center w-full">
              <div className="text-base font-semibold text-slate-900 whitespace-nowrap">{title}</div>
              <div className="text-xs text-slate-500 whitespace-nowrap overflow-hidden text-ellipsis">{subtitle}</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}


export default function OpenAgentIOParallelExecutionAnimation() {
  const [playing, setPlaying] = useState(true);
  const [key, setKey] = useState(0);
  const [language, setLanguage] = useState<'zh' | 'en'>('zh');

  // 切换语言
  const toggleLanguage = () => {
    setLanguage(prev => prev === 'zh' ? 'en' : 'zh');
  };

  // 重放
  const handleReplay = () => {
    setKey(key + 1);
  };

  // 获取当前语言的文本
  const t = translations[language];

  // 三个SubAgent的调用路径（从MainAgent到各个SubAgent）
  const requestPaths = [
    "M 272 160 C 400 100, 550 100, 680 120", // SubAgent A：向上微弯
    "M 272 180 C 400 150, 550 150, 680 180", // SubAgent B：中间向上拱
    "M 272 200 C 400 260, 550 260, 680 240"  // SubAgent C：向下微弯
  ];

  // 三个SubAgent的返回路径：从右侧SubAgent出发，向下弯曲流向左侧MainAgent，箭头在左端
  const responsePaths = [
    "M 680 120 C 550 320, 400 320, 272 260", // SubAgent A 返回：右→左下
    "M 680 180 C 550 320, 400 320, 272 260", // SubAgent B 返回：右→左下
    "M 680 240 C 550 320, 400 320, 272 260"  // SubAgent C 返回：右→左下
  ];

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
            <Button variant="outline" onClick={handleReplay} className="rounded-2xl">
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
          className="relative h-[520px] overflow-hidden rounded-[2rem] border border-white/80 shadow-[0_28px_100px rgba(15,118,110,0.18)] backdrop-blur-xl"
          style={{
            background:
              "radial-gradient(circle at 50% 28%, rgba(255,255,255,0.96) 0%, rgba(248,253,255,0.9) 42%, rgba(235,248,252,0.82) 100%)",
          }}
          key={key}
        >
          <div className="absolute -left-20 top-16 h-72 w-72 rounded-full bg-cyan-200/20 blur-3xl" />
          <div className="absolute -right-20 top-20 h-72 w-72 rounded-full bg-blue-200/20 blur-3xl" />
          <div className="absolute bottom-10 left-1/2 h-56 w-96 -translate-x-1/2 rounded-full bg-teal-100/30 blur-3xl" />

          {/* 左侧 MainAgent */}
          <AgentCard title="MainAgent" subtitle={t.mainAgentSubtitle} icon={MessageSquare} className="left-20 top-32" />

          {/* 右侧三个 SubAgent，垂直排列 */}
          <div className="absolute right-20 top-[60px] flex flex-col gap-4 z-10">
            <SubAgentCard title="SubAgent A" subtitle={t.subAgentSubtitle} index={0} playing={playing} />
            <SubAgentCard title="SubAgent B" subtitle={t.subAgentSubtitle} index={1} playing={playing} />
            <SubAgentCard title="SubAgent C" subtitle={t.subAgentSubtitle} index={2} playing={playing} />
          </div>


          <svg className="absolute inset-0 h-full w-full z-[15]" viewBox="0 0 1000 520">
            <defs>
              <linearGradient id="requestGradient" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#06b6d4" />
                <stop offset="55%" stopColor="#38bdf8" />
                <stop offset="100%" stopColor="#2563eb" />
              </linearGradient>
              <linearGradient id="responseGradient" x1="1" y1="0" x2="0" y2="0">
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
              <marker id="arrowResponse" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
                <path d="M0,0 L0,6 L9,3 z" fill="#059669" />
              </marker>
            </defs>

            {/* 并行请求路径：MainAgent -> 三个SubAgent */}
            {requestPaths.map((path, index) => (
              <motion.path
                key={`request-${index}`}
                d={path}
                fill="none"
                stroke="url(#requestGradient)"
                strokeWidth="3.5"
                strokeLinecap="round"
                strokeDasharray="9 10"
                markerEnd="url(#arrowRequest)"
                filter="url(#softGlow)"
                animate={playing ? { pathLength: [0.2, 1, 0.2], opacity: [0.4, 1, 0.4] } : { pathLength: 1, opacity: 0.4 }}
                transition={{ duration: 2.4, repeat: Infinity, ease: "easeInOut" }}
              />
            ))}

            {/* 结果返回路径：三个SubAgent -> MainAgent（流动式虚线动画） */}
            {responsePaths.map((path, index) => (
              <motion.path
                key={`response-${index}`}
                d={path}
                fill="none"
                stroke="url(#responseGradient)"
                strokeWidth="3.5"
                strokeLinecap="round"
                strokeDasharray="9 10"
                markerEnd="url(#arrowResponse)"
                filter="url(#softGlow)"
                opacity={0.8}
                animate={{ strokeDashoffset: [0, -19] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
              />
            ))}

            {/* 文字标注 */}
            <text x="475" y="60" fontSize="18" fontWeight="700" fill="#0891b2" textAnchor="middle">
              {language === 'zh' ? 'async invoke (并行)' : 'async invoke'}
            </text>
            <text x="475" y="350" fontSize="18" fontWeight="700" fill="#059669" textAnchor="middle">
              {language === 'zh' ? 'aggregate results (聚合)' : 'aggregate results'}
            </text>


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
                  { duration: 3.2, repeat: Infinity, delay: 0.3 + index * 0.4, ease: "easeInOut" } :
                  { duration: 0.5, delay: 0.4 + index * 0.1 }
                }
                className="rounded-2xl border border-cyan-100 bg-white/75 p-3.5 text-sm shadow-[0_12px_40px rgba(14,165,233,0.1)] backdrop-blur transition-all duration-200 hover:shadow-[0_16px_50px rgba(14,165,233,0.15)] hover:-translate-y-1"
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
