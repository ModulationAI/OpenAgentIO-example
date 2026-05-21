import React, { useState } from "react";
import { motion } from "framer-motion";
import { Play, Pause, RotateCcw, MessageSquare, Server, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

// 国际化语言包
const translations = {
  zh: {
    scenario: "场景5：Agent Handoff 转交调用模式",
    pause: "暂停",
    play: "播放",
    replay: "重放",
    mainAgentSubtitle: "调用方 / 任务发起",
    subAgentASubtitle: "被调用方 / 无法处理",
    subAgentBSubtitle: "被调用方 / 实际处理",
    steps: [
      "MainAgent 构造请求并调用 SubAgent A",
      "SubAgent A 收到请求但无法处理",
      "SubAgent A 转交给 SubAgent B 处理",
      "SubAgent B 完成处理并返回结果",
      "最终结果返回给 MainAgent",
    ]
  },
  en: {
    scenario: "Scenario 5: Agent Handoff Pattern",
    pause: "Pause",
    play: "Play",
    replay: "Replay",
    mainAgentSubtitle: "Caller / Task Initiator",
    subAgentASubtitle: "Callee / Cannot Handle",
    subAgentBSubtitle: "Callee / Actual Processor",
    steps: [
      "MainAgent constructs request and calls SubAgent A",
      "SubAgent A receives request but cannot handle",
      "SubAgent A hands off to SubAgent B for processing",
      "SubAgent B completes processing and returns result",
      "Final result returned to MainAgent",
    ]
  }
} as const;

function AgentCard({ title, subtitle, icon: Icon, className = "" }: { title: string; subtitle: string; icon: React.ElementType; className?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.1 }}
      className={`absolute ${className} z-10`}
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

export default function AgentHandoffAnimation() {
  const [playing, setPlaying] = useState(true);
  const [key, setKey] = useState(0);
  const [language, setLanguage] = useState<'zh' | 'en'>('zh');

  // 切换语言
  const toggleLanguage = () => {
    setLanguage(prev => prev === 'zh' ? 'en' : 'zh');
  };

  // 获取当前语言的文本
  const t = translations[language];

  // 路径定义（viewBox 0 0 1000 520）
  // MainAgent(左上中) -> SubAgent A(右上)
  const requestPath1 = "M 300 190 C 440 130, 580 120, 720 140";
  // SubAgent A(右上) -> SubAgent B(右下)
  const requestPath2 = "M 760 150 C 720 190, 720 230, 760 270";
  // SubAgent B(右下) -> MainAgent(左上中)
  const responsePath = "M 760 330 C 600 400, 440 360, 300 240";

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

          {/* MainAgent - 左侧偏上，处于上下居中位置 */}
          <AgentCard title="MainAgent" subtitle={t.mainAgentSubtitle} icon={MessageSquare} className="left-16 top-40 w-64" />

          {/* SubAgent A - 右上 */}
          <AgentCard title="SubAgent A" subtitle={t.subAgentASubtitle} icon={Server} className="right-16 top-16 w-60" />

          {/* SubAgent B - 右下 */}
          <AgentCard title="SubAgent B" subtitle={t.subAgentBSubtitle} icon={Server} className="right-16 top-64 w-60" />

          <svg className="absolute inset-0 h-full w-full z-[15]" viewBox="0 0 1000 520">
            <defs>
              <linearGradient id="handoffRequestGradient" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#06b6d4" />
                <stop offset="55%" stopColor="#38bdf8" />
                <stop offset="100%" stopColor="#2563eb" />
              </linearGradient>
              <linearGradient id="handoffResponseGradient" x1="1" y1="0" x2="0" y2="0">
                <stop offset="0%" stopColor="#10b981" />
                <stop offset="55%" stopColor="#34d399" />
                <stop offset="100%" stopColor="#059669" />
              </linearGradient>
              <filter id="handoffSoftGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="5" result="coloredBlur" />
                <feMerge>
                  <feMergeNode in="coloredBlur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              <marker id="handoffArrowRequest" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
                <path d="M0,0 L0,6 L9,3 z" fill="#2563eb" />
              </marker>
              <marker id="handoffArrowResponse" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
                <path d="M0,0 L0,6 L9,3 z" fill="#059669" />
              </marker>
            </defs>

            {/* MainAgent -> SubAgent A */}
            <motion.path
              d={requestPath1}
              fill="none"
              stroke="url(#handoffRequestGradient)"
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeDasharray="9 10"
              markerEnd="url(#handoffArrowRequest)"
              filter="url(#handoffSoftGlow)"
              animate={playing ? { strokeDashoffset: [0, -19] } : { strokeDashoffset: 0 }}
              transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
            />

            {/* SubAgent A -> SubAgent B */}
            <motion.path
              d={requestPath2}
              fill="none"
              stroke="url(#handoffRequestGradient)"
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeDasharray="9 10"
              markerEnd="url(#handoffArrowRequest)"
              filter="url(#handoffSoftGlow)"
              animate={playing ? { strokeDashoffset: [0, -19] } : { strokeDashoffset: 0 }}
              transition={{ duration: 1.5, repeat: Infinity, ease: "linear", delay: 0.3 }}
            />

            {/* SubAgent B -> MainAgent */}
            <motion.path
              d={responsePath}
              fill="none"
              stroke="url(#handoffResponseGradient)"
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeDasharray="9 10"
              markerEnd="url(#handoffArrowResponse)"
              filter="url(#handoffSoftGlow)"
              opacity={0.8}
              animate={playing ? { strokeDashoffset: [0, -19] } : { strokeDashoffset: 0 }}
              transition={{ duration: 1.5, repeat: Infinity, ease: "linear", delay: 0.6 }}
            />

            {/* 文字标注 */}
            <text x="480" y="80" fontSize="18" fontWeight="700" fill="#0891b2" textAnchor="middle">
              {language === 'zh' ? 'invoke(请求)' : 'invoke(request)'}
            </text>
            <text x="650" y="210" fontSize="18" fontWeight="700" fill="#0891b2" textAnchor="middle">
              {language === 'zh' ? 'invoke(转交)' : 'invoke(handoff)'}
            </text>
            <text x="420" y="380" fontSize="18" fontWeight="700" fill="#059669" textAnchor="middle">
              {language === 'zh' ? 'return(结果)' : 'return(response)'}
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
                className="rounded-2xl border border-cyan-100 bg-white/75 p-3.5 text-sm shadow-[0_12px_40px_rgba(14,165,233,0.1)] backdrop-blur transition-all duration-200 hover:shadow-[0_16px_50px_rgba(14,165,233,0.15)] hover:-translate-y-1"
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
