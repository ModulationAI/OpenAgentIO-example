import { useState } from 'react'
import RequestReply from './scenes/RequestReply'
import Streaming from './scenes/Streaming'
import PubSub from './scenes/PubSub'
import ParallelExecution from './scenes/ParallelExecution'
import AgentHandoff from './scenes/AgentHandoff'
import AsyncTask from './scenes/AsyncTask'
import HttpSse from './scenes/HttpSse'
import FunctionCalling from './scenes/FunctionCalling'
import { Button } from '@/components/ui/button'
import { Layers } from 'lucide-react'
import './App.css'

type Scene = 'request-reply' | 'streaming' | 'pubsub' | 'parallel' | 'handoff' | 'async-task' | 'http-sse' | 'function-calling'

function App() {
  const [currentScene, setCurrentScene] = useState<Scene>('request-reply')

  return (
    <div className="relative">
      {/* 场景内容 */}
      {currentScene === 'request-reply' && <RequestReply />}
      {currentScene === 'streaming' && <Streaming />}
      {currentScene === 'pubsub' && <PubSub />}
      {currentScene === 'parallel' && <ParallelExecution />}
      {currentScene === 'handoff' && <AgentHandoff />}
      {currentScene === 'async-task' && <AsyncTask />}
      {currentScene === 'http-sse' && <HttpSse />}
      {currentScene === 'function-calling' && <FunctionCalling />}

      {/* 场景切换栏 - 放在大卡片下方 */}
      <div className="max-w-6xl mx-auto mt-4 flex justify-center px-4">
        <div className="bg-white/90 backdrop-blur-xl rounded-2xl shadow-lg border border-cyan-100 p-1.5 flex flex-wrap justify-center gap-1.5">
          <div className="flex items-center gap-2 px-3 text-sm font-semibold text-cyan-700">
            <Layers className="h-4 w-4" />
            <span>场景</span>
          </div>
          <Button
            variant={currentScene === 'request-reply' ? 'default' : 'ghost'}
            onClick={() => setCurrentScene('request-reply')}
            className="rounded-xl text-sm"
          >
            Request-Reply
          </Button>
          <Button
            variant={currentScene === 'streaming' ? 'default' : 'ghost'}
            onClick={() => setCurrentScene('streaming')}
            className="rounded-xl text-sm"
          >
            Streaming
          </Button>
          <Button
            variant={currentScene === 'pubsub' ? 'default' : 'ghost'}
            onClick={() => setCurrentScene('pubsub')}
            className="rounded-xl text-sm"
          >
            Pub/Sub
          </Button>
          <Button
            variant={currentScene === 'parallel' ? 'default' : 'ghost'}
            onClick={() => setCurrentScene('parallel')}
            className="rounded-xl text-sm"
          >
            Parallel
          </Button>
          <Button
            variant={currentScene === 'handoff' ? 'default' : 'ghost'}
            onClick={() => setCurrentScene('handoff')}
            className="rounded-xl text-sm"
          >
            Handoff
          </Button>
          <Button
            variant={currentScene === 'async-task' ? 'default' : 'ghost'}
            onClick={() => setCurrentScene('async-task')}
            className="rounded-xl text-sm"
          >
            Async Task
          </Button>
          <Button
            variant={currentScene === 'http-sse' ? 'default' : 'ghost'}
            onClick={() => setCurrentScene('http-sse')}
            className="rounded-xl text-sm"
          >
            HTTP/SSE
          </Button>
          <Button
            variant={currentScene === 'function-calling' ? 'default' : 'ghost'}
            onClick={() => setCurrentScene('function-calling')}
            className="rounded-xl text-sm"
          >
            Function Calling
          </Button>
        </div>
      </div>
    </div>
  )
}

export default App
