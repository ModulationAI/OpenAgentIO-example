import { useState } from 'react'
import RequestReply from './scenes/RequestReply'
import Streaming from './scenes/Streaming'
import PubSub from './scenes/PubSub'
import ParallelExecution from './scenes/ParallelExecution'
import { Button } from '@/components/ui/button'
import { Layers } from 'lucide-react'
import './App.css'

type Scene = 'request-reply' | 'streaming' | 'pubsub' | 'parallel'

function App() {
  const [currentScene, setCurrentScene] = useState<Scene>('request-reply')

  return (
    <div className="relative">
      {/* 场景内容 */}
      {currentScene === 'request-reply' && <RequestReply />}
      {currentScene === 'streaming' && <Streaming />}
      {currentScene === 'pubsub' && <PubSub />}
      {currentScene === 'parallel' && <ParallelExecution />}

      {/* 场景切换栏 - 放在大卡片下方 */}
      <div className="max-w-6xl mx-auto mt-4 flex justify-center">
        <div className="bg-white/90 backdrop-blur-xl rounded-2xl shadow-lg border border-cyan-100 p-1.5 flex gap-1.5">
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
        </div>
      </div>
    </div>
  )
}

export default App
