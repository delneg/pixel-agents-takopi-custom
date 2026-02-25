/**
 * Chat input for sending prompts to agents in webapp mode.
 * Appears at the bottom of the screen when an agent is selected.
 */

import { useState, useRef, useEffect } from 'react'
import { vscode } from '../vscodeApi.js'

interface ChatInputProps {
  selectedAgent: number | null
  agentStatuses: Record<number, string>
  lastAnswers: Record<number, string>
}

const containerStyle: React.CSSProperties = {
  position: 'absolute',
  bottom: 10,
  left: '50%',
  transform: 'translateX(-50%)',
  zIndex: 'var(--pixel-controls-z)',
  display: 'flex',
  flexDirection: 'column',
  gap: 4,
  background: 'var(--pixel-bg)',
  border: '2px solid var(--pixel-border)',
  borderRadius: 0,
  padding: '6px 8px',
  boxShadow: 'var(--pixel-shadow)',
  minWidth: 400,
  maxWidth: '60vw',
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '6px 8px',
  fontSize: '22px',
  background: 'rgba(255, 255, 255, 0.05)',
  color: 'var(--pixel-text)',
  border: '2px solid var(--pixel-border)',
  borderRadius: 0,
  outline: 'none',
  boxSizing: 'border-box',
}

const sendBtnStyle: React.CSSProperties = {
  padding: '6px 14px',
  fontSize: '22px',
  background: 'var(--pixel-agent-bg)',
  color: 'var(--pixel-agent-text)',
  border: '2px solid var(--pixel-agent-border)',
  borderRadius: 0,
  cursor: 'pointer',
  flexShrink: 0,
}

const sendBtnDisabled: React.CSSProperties = {
  ...sendBtnStyle,
  opacity: 0.4,
  cursor: 'default',
}

const answerStyle: React.CSSProperties = {
  fontSize: '20px',
  color: 'rgba(255, 255, 255, 0.7)',
  maxHeight: 120,
  overflowY: 'auto',
  padding: '4px 6px',
  background: 'rgba(255, 255, 255, 0.03)',
  border: '1px solid var(--pixel-border)',
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
}

export function ChatInput({ selectedAgent, agentStatuses, lastAnswers }: ChatInputProps) {
  const [text, setText] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const isRunning = selectedAgent !== null && agentStatuses[selectedAgent] !== 'waiting' && agentStatuses[selectedAgent] !== undefined
  // Agent is idle if it's waiting or has no status (just created)
  const canSend = selectedAgent !== null && text.trim() !== '' && !isRunning

  const handleSend = () => {
    if (!canSend) return
    vscode.postMessage({ type: 'sendPrompt', id: selectedAgent, text: text.trim() })
    setText('')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // Auto-focus when selected agent changes
  useEffect(() => {
    if (selectedAgent !== null) {
      inputRef.current?.focus()
    }
  }, [selectedAgent])

  if (selectedAgent === null) return null

  const lastAnswer = lastAnswers[selectedAgent]

  return (
    <div style={containerStyle}>
      {lastAnswer && (
        <div style={answerStyle}>
          {lastAnswer.length > 500 ? lastAnswer.slice(0, 500) + '...' : lastAnswer}
        </div>
      )}
      <div style={{ display: 'flex', gap: 4 }}>
        <input
          ref={inputRef}
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isRunning ? 'Agent is working...' : `Message agent #${selectedAgent}...`}
          disabled={isRunning}
          style={{
            ...inputStyle,
            opacity: isRunning ? 0.5 : 1,
          }}
        />
        <button
          onClick={handleSend}
          style={canSend ? sendBtnStyle : sendBtnDisabled}
          disabled={!canSend}
        >
          Send
        </button>
      </div>
    </div>
  )
}
