import {
  OpenAgentIOClient,
  ResponseDelta,
  type Envelope,
  type JsonValue,
} from '@openagentio/client';
import './style.css';

type ChatRole = 'user' | 'assistant' | 'system';

const client = new OpenAgentIOClient({
  baseUrl: '/api',
});

const chatLog = getElement<HTMLDivElement>('chat-log');
const form = getElement<HTMLFormElement>('chat-form');
const input = getElement<HTMLInputElement>('message-input');
const sendButton = getElement<HTMLButtonElement>('send-button');

form.addEventListener('submit', (event) => {
  event.preventDefault();
  void sendMessage();
});

appendMessage(
  'assistant',
  'Ask me about OpenAgentIO. I will stream the response through SSE.',
);

async function sendMessage() {
  const message = input.value.trim();
  if (!message) {
    return;
  }

  input.value = '';
  setBusy(true);
  appendMessage('user', message);
  const assistantBubble = appendMessage('assistant', '');
  assistantBubble.classList.add('streaming');

  try {
    for await (const envelope of client.streamInvoke<JsonValue>('assistant', {
      message,
      delay_ms: 140,
    })) {
      if (envelope.event_type === ResponseDelta) {
        assistantBubble.textContent += readDelta(envelope);
        scrollToLatest();
      }
    }
  } catch (error) {
    appendMessage('system', formatError(error));
  } finally {
    assistantBubble.classList.remove('streaming');
    setBusy(false);
    input.focus();
  }
}

function appendMessage(role: ChatRole, text: string) {
  const row = document.createElement('div');
  row.className = `message-row ${role}`;

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;

  row.append(bubble);
  chatLog.append(row);
  scrollToLatest();
  return bubble;
}

function readDelta(envelope: Envelope<JsonValue>) {
  const payload = envelope.payload;
  if (isObject(payload) && typeof payload.delta === 'string') {
    return payload.delta;
  }
  return '';
}

function isObject(value: JsonValue | undefined): value is Record<string, JsonValue | undefined> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function setBusy(busy: boolean) {
  sendButton.disabled = busy;
  input.disabled = busy;
  sendButton.textContent = busy ? 'Streaming...' : 'Send';
}

function scrollToLatest() {
  chatLog.scrollTop = chatLog.scrollHeight;
}

function getElement<T extends HTMLElement>(id: string): T {
  const element = document.getElementById(id);
  if (!element) {
    throw new Error(`Missing element #${id}`);
  }
  return element as T;
}

function formatError(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}
