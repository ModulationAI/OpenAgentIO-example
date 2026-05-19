import React, { useState } from "react";
import { motion } from "framer-motion";
import { Play, Pause, RotateCcw, MessageSquare, Globe, RadioTower, HardDrive, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

// 国际化语言包
const translations = {
  zh: {
    scenario: "场景3：Pub/Sub 事件驱动模式",
    pause: "暂停",
    play: "播放",
    replay: "重放",
    mainAgentSubtitle: "发布者 / 事件源",
    topicSubtitle: "事件主题 / 广播层",
    queueSubtitle: "扇出 / 广播到所有订阅者",
    queueDescription: "事件复制多份，同时投递给所有Worker",
    workerSubtitle: "订阅者 / 事件处理方",
    steps: [
      "MainAgent 发布事件到主题",
      "Topic 接收事件准备扇出",
      "事件分裂为多份副本",
      "广播到所有订阅Worker",
      "所有Worker同时处理事件",
    ]
  },
  en: {
    scenario: "Scenario 3: Pub/Sub Event-Driven Pattern",
    pause: "Pause",
    play: "Play",
    replay: "Replay",
    mainAgentSubtitle: "Publisher / Event Source",
    topicSubtitle: "Event Topic / Broadcast Layer",
    queueSubtitle: "Fan-out / Broadcast to all subscribers",
    queueDescription: "Event is replicated and delivered to all Workers simultaneously",
    workerSubtitle: "Subscriber / Event Handler",
    steps: [
      "MainAgent publishes event to topic",
      "Topic receives event for fan-out",
      "Event splits into multiple copies",
      "Broadcast to all subscriber Workers",
      "All Workers process event simultaneously",
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

function WorkerCard({ title, index, playing, delay }: { title: string; index: number; playing: boolean; delay: number }) {
  // 三个Worker不同的颜色主题
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
      className={`w-40 z-10`}
    >
      <Card className={`rounded-2xl border ${theme.border} bg-white/80 shadow-lg backdrop-blur-xl`}>
        <CardContent className="p-2.5 !pt-2.5 h-full flex flex-col items-center justify-center">
          <div className="flex items-center gap-1.5 mb-1.5">
            <HardDrive className={`h-4.5 w-4.5 ${theme.icon}`} />
            <div className="text-sm font-semibold text-slate-900">{title}</div>
          </div>
          <motion.div
            animate={playing ? { opacity: [0, 1, 1, 0], scale: [0.95, 1.05, 1, 0.95] } : { opacity: 0 }}
            transition={{ duration: 3.2, repeat: Infinity, delay }}
            className={`text-[11px] font-medium px-2 py-0.5 rounded-full border ${theme.statusBg} ${theme.statusBorder} ${theme.statusText}`}
          >
            {index === 0 ? "SubAgent1" : index === 1 ? "SubAgent2" : "SubAgentN"}
          </motion.div>
        </CardContent>
      </Card>
    </motion.div>
  );
}


export default function OpenAgentIOPubSubAnimation() {
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

  // 三个Worker的投递路径，根据语言模式动态调整终点位置
  const workerPaths = language === 'en' ? [
    "M 500 140 C 460 220, 360 260, 270 325", // Worker 1 英文模式下终点上移
    "M 500 140 C 540 220, 460 260, 500 310", // Worker 2 英文模式下终点上移
    "M 500 140 C 540 220, 640 260, 730 325"  // Worker 3 英文模式下终点上移
  ] : [
    "M 500 140 C 460 220, 360 260, 270 340", // Worker 1 中文模式
    "M 500 140 C 540 220, 460 260, 500 325", // Worker 2 中文模式
    "M 500 140 C 540 220, 640 260, 730 340"  // Worker 3 中文模式
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

          {/* 顶部节点 - 优化布局更舒展 */}
          <AgentCard title="MainAgent" subtitle={t.mainAgentSubtitle} icon={MessageSquare} className="left-20 top-16" />

          {/* Topic用纯文字显示，保留图标 */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="absolute left-1/2 -translate-x-1/2 top-16 z-10 flex items-center gap-3"
          >
            <div className="rounded-2xl border border-cyan-100 bg-gradient-to-br from-cyan-50 to-blue-50 p-3 shadow-inner flex items-center justify-center">
              <RadioTower className="h-7 w-7 text-cyan-700" />
            </div>
            <div className="text-xl font-bold text-slate-900">agent.events.task</div>
          </motion.div>

          {/* 扇出层 - 缩小并右移，英文模式下自动缩小上移 */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className={`absolute right-10 ${language === 'en' ? 'top-[175px]' : 'top-[190px]'} z-10`}
          >
            <Card className={`rounded-2xl border border-cyan-100 bg-gradient-to-r from-cyan-50 to-blue-50 shadow-lg backdrop-blur-xl ${language === 'en' ? 'w-[330px]' : 'w-[360px]'}`}>
              <CardContent className={`${language === 'en' ? 'p-3 !pt-3' : 'p-3.5 !pt-3.5'} flex flex-col items-center`}>
                <div className="flex items-center gap-2 mb-1">
                  <Users className={`${language === 'en' ? 'h-4.5 w-4.5' : 'h-5 w-5'} text-cyan-700`} />
                  <div className={`${language === 'en' ? 'text-base' : 'text-lg'} font-semibold text-slate-900`}>{t.queueSubtitle}</div>
                </div>
                <div className={`${language === 'en' ? 'text-xs' : 'text-sm'} text-slate-600`}>{t.queueDescription}</div>
              </CardContent>
            </Card>
          </motion.div>

          {/* 底部Worker节点 - 根据语言模式动态上移，避免被STEP卡片遮挡 */}
          <div className={`absolute ${language === 'en' ? 'bottom-32' : 'bottom-28'} left-1/2 -translate-x-1/2 flex gap-20 z-10`}>
            <WorkerCard title="Worker-1" index={0} playing={playing} delay={1.4} />
            <WorkerCard title="Worker-2" index={1} playing={playing} delay={1.4} />
            <WorkerCard title="Worker-N" index={2} playing={playing} delay={1.4} />
          </div>

          <svg className="absolute inset-0 h-full w-full z-[15]" viewBox="0 0 1000 520">
            <defs>
              <linearGradient id="publishGradient" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#06b6d4" />
                <stop offset="55%" stopColor="#38bdf8" />
                <stop offset="100%" stopColor="#2563eb" />
              </linearGradient>
              <linearGradient id="fanoutGradient1" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#a855f7" />
                <stop offset="100%" stopColor="#7e22ce" />
              </linearGradient>
              <linearGradient id="fanoutGradient2" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#a855f7" />
                <stop offset="100%" stopColor="#7e22ce" />
              </linearGradient>
              <linearGradient id="fanoutGradient3" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#a855f7" />
                <stop offset="100%" stopColor="#7e22ce" />
              </linearGradient>
              <filter id="softGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="6" result="coloredBlur" />
                <feMerge>
                  <feMergeNode in="coloredBlur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
              <marker id="arrowPublish" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
                <path d="M0,0 L0,6 L9,3 z" fill="#2563eb" />
              </marker>
              <marker id="arrowFanout1" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
                <path d="M0,0 L0,6 L9,3 z" fill="#7e22ce" />
              </marker>
              <marker id="arrowFanout2" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
                <path d="M0,0 L0,6 L9,3 z" fill="#7e22ce" />
              </marker>
              <marker id="arrowFanout3" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
                <path d="M0,0 L0,6 L9,3 z" fill="#7e22ce" />
              </marker>
            </defs>

            {/* 发布路径：MainAgent -> Topic - 连接两个卡片的带箭头连接线 */}
            <path
              d="M 272 90 L 480 90"
              fill="none"
              stroke="rgba(6, 182, 212, 0.9)"
              strokeWidth="4"
              strokeLinecap="round"
              strokeDasharray="12 8"
              markerEnd="url(#arrowPublish)"
              filter="drop-shadow(0 0 8px rgba(6, 182, 212, 0.6))"
            />


            {/* 扇出路径：Topic -> 三个Worker - 优化路径曲率 */}
            <motion.path
              d={workerPaths[0]}
              fill="none"
              stroke="url(#fanoutGradient1)"
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeDasharray="7 9"
              markerEnd="url(#arrowFanout1)"
              filter="url(#softGlow)"
              animate={playing ? { pathLength: [0.2, 1, 0.2], opacity: [0, 1, 0] } : { pathLength: 1, opacity: 0 }}
              transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut", delay: 1.2 }}
            />
            <motion.path
              d={workerPaths[1]}
              fill="none"
              stroke="url(#fanoutGradient2)"
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeDasharray="7 9"
              markerEnd="url(#arrowFanout2)"
              filter="url(#softGlow)"
              animate={playing ? { pathLength: [0.2, 1, 0.2], opacity: [0, 1, 0] } : { pathLength: 1, opacity: 0 }}
              transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut", delay: 1.2 }}
            />
            <motion.path
              d={workerPaths[2]}
              fill="none"
              stroke="url(#fanoutGradient3)"
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeDasharray="7 9"
              markerEnd="url(#arrowFanout3)"
              filter="url(#softGlow)"
              animate={playing ? { pathLength: [0.2, 1, 0.2], opacity: [0, 1, 0] } : { pathLength: 1, opacity: 0 }}
              transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut", delay: 1.2 }}
            />

            {/* 文字标注 - 调整位置更清晰 */}
            <text x="356" y="68" fontSize="18" fontWeight="700" fill="#0891b2" textAnchor="middle">publish</text>


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
