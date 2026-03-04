import { useState, useRef, useEffect, useCallback } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { sendMessage, resetConversation, getStatus } from '@/api/client'
import { playAudio, stopAudio } from '@/utils/audio'
import useStore from '@/store/useStore'
import { Send, Mic, MicOff, Loader2, RotateCcw, Radio } from 'lucide-react'

// ── Web Speech API availability check ────────────────────────────────────────
const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition || null

export default function ChatPanel() {
  const [input, setInput]                   = useState('')
  const [isRecording, setIsRecording]       = useState(false)
  const [liveTranscript, setLiveTranscript] = useState('')
  const [noSpeechApi, setNoSpeechApi]       = useState(!SpeechRecognition)
  const bottomRef = useRef(null)
  const inputRef  = useRef(null)

  // ── Stable refs ───────────────────────────────────────────────────────────
  const recognizerRef    = useRef(null)   // SpeechRecognition instance
  const isRecordingRef   = useRef(false)  // mirror of isRecording for closures
  const inputRef2        = useRef('')     // mirror of input text for closures

  // Keep refs in sync with state
  useEffect(() => { isRecordingRef.current = isRecording }, [isRecording])

  // ── Store ─────────────────────────────────────────────────────────────────
  const sessionId      = useStore(s => s.sessionId)
  const messages       = useStore(s => s.messages)
  const isLoading      = useStore(s => s.isLoading)
  const isSpeaking     = useStore(s => s.isSpeaking)
  const addMessage     = useStore(s => s.addMessage)
  const setLoading     = useStore(s => s.setLoading)
  const setSpeaking    = useStore(s => s.setSpeaking)
  const setFormState   = useStore(s => s.setFormState)
  const setStatusItems = useStore(s => s.setStatusItems)

  // Stable store refs for async callbacks
  const sessionIdRef   = useRef(sessionId)
  const addMessageRef  = useRef(addMessage)
  const setLoadingRef  = useRef(setLoading)
  const setSpeakingRef = useRef(setSpeaking)
  const setFormRef     = useRef(setFormState)
  const setStatusRef   = useRef(setStatusItems)
  useEffect(() => { sessionIdRef.current   = sessionId },    [sessionId])
  useEffect(() => { addMessageRef.current  = addMessage },   [addMessage])
  useEffect(() => { setLoadingRef.current  = setLoading },   [setLoading])
  useEffect(() => { setSpeakingRef.current = setSpeaking },  [setSpeaking])
  useEffect(() => { setFormRef.current     = setFormState }, [setFormState])
  useEffect(() => { setStatusRef.current   = setStatusItems },[setStatusItems])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  // ── Core: send text → agent → TTS ─────────────────────────────────────────
  const dispatchMessage = useCallback(async (text) => {
    const msg = text?.trim()
    if (!msg) return
    addMessageRef.current('user', msg)
    setLoadingRef.current(true)
    try {
      const res  = await sendMessage(msg, sessionIdRef.current)
      const data = res.data
      addMessageRef.current('assistant', data.response)
      setFormRef.current({
        activeForm:          data.active_form,
        formData:            data.form_data || {},
        confirmationPending: data.confirmation_pending,
        submitted:           data.submitted,
      })
      if (data.submitted || data.intent === 'update_checklist') {
        getStatus(sessionIdRef.current)
          .then(r => setStatusRef.current(r.data.status_items))
          .catch(() => {})
      }
      if (data.audio_base64 && !isRecordingRef.current) {
        const ctrl = playAudio(
          data.audio_base64,
          () => setSpeakingRef.current(true),
          () => setSpeakingRef.current(false),
        )
        await ctrl.promise
      }
    } catch {
      addMessageRef.current('assistant', 'Something went wrong. Please try again.')
    } finally {
      setLoadingRef.current(false)
      if (!isRecordingRef.current) inputRef.current?.focus()
    }
  }, [])

  // ── Text input send ────────────────────────────────────────────────────────
  const handleSend = useCallback(() => {
    const msg = inputRef2.current.trim()
    if (!msg || isLoading || isRecording) return
    setInput(''); inputRef2.current = ''
    dispatchMessage(msg)
  }, [isLoading, isRecording, dispatchMessage])

  const handleInputChange = (e) => {
    setInput(e.target.value)
    inputRef2.current = e.target.value
  }

  // ── Voice: Web Speech API ─────────────────────────────────────────────────
  const stopRecording = useCallback(() => {
    const r = recognizerRef.current
    if (r) {
      try { r.stop() } catch {}
      recognizerRef.current = null
    }
    setIsRecording(false)
    isRecordingRef.current = false
    setLiveTranscript('')
  }, [])

  const startRecording = useCallback(() => {
    if (isRecordingRef.current) return
    if (!SpeechRecognition) { setNoSpeechApi(true); return }

    // Interrupt any playing TTS immediately
    stopAudio()
    setSpeakingRef.current(false)

    const r = new SpeechRecognition()
    r.continuous      = true   // keep listening until we explicitly stop
    r.interimResults  = true   // fire events as the user speaks
    r.lang            = 'en-US'
    r.maxAlternatives = 1

    let finalBuffer = ''       // accumulates confirmed final segments

    r.onstart = () => {
      setIsRecording(true)
      isRecordingRef.current = true
      setLiveTranscript('')
    }

    r.onresult = (e) => {
      let interim = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const part = e.results[i][0].transcript
        if (e.results[i].isFinal) {
          finalBuffer += part + ' '
        } else {
          interim += part
        }
      }
      // Show interim on top of whatever we've confirmed so far
      setLiveTranscript((finalBuffer + interim).trim())
    }

    // Called when the user stops speaking (natural pause detected by browser)
    r.onspeechend = () => {
      r.stop()   // triggers onend
    }

    r.onend = () => {
      recognizerRef.current = null
      setIsRecording(false)
      isRecordingRef.current = false
      const text = finalBuffer.trim()
      setLiveTranscript('')
      if (text) dispatchMessage(text)
    }

    r.onerror = (e) => {
      // 'no-speech' is normal — user didn't say anything, not a real error
      if (e.error !== 'no-speech') console.error('[speech]', e.error)
      // onend will fire right after, which cleans up state
    }

    recognizerRef.current = r
    r.start()
  }, [dispatchMessage])

  const toggleMic = useCallback(() => {
    if (isRecordingRef.current) {
      stopRecording()
    } else {
      startRecording()
    }
  }, [startRecording, stopRecording])

  // ── Reset ─────────────────────────────────────────────────────────────────
  const handleReset = async () => {
    stopRecording()
    stopAudio()
    setSpeakingRef.current(false)
    await resetConversation(sessionIdRef.current).catch(() => {})
    useStore.setState({ messages: [], activeForm: null, formData: {}, confirmationPending: false, submitted: false })
  }

  useEffect(() => () => { stopRecording(); stopAudio() }, [stopRecording])

  // ── Status indicator ───────────────────────────────────────────────────────
  const statusDot  = isSpeaking  ? 'bg-green-400 animate-pulse'
    : isRecording               ? 'bg-destructive animate-pulse'
    : isLoading                 ? 'bg-yellow-400 animate-pulse'
    :                             'bg-muted-foreground/40'

  const statusText = isSpeaking  ? 'ARIA is speaking…'
    : isRecording                ? (liveTranscript ? `"${liveTranscript}"` : 'Listening…')
    : isLoading                  ? 'Thinking…'
    :                              'Ready'

  const SUGGESTIONS = [
    'What shift am I working today?',
    'What is my compliance status?',
    'I need to file an occurrence report',
    'Request a teddy bear for a patient',
  ]

  return (
    <TooltipProvider>
      <div className="flex flex-col h-full bg-background">

        {/* ── Top bar ───────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-4 py-3 bg-card">
          <div className="flex items-center gap-2 min-w-0">
            <span className={`w-2 h-2 rounded-full shrink-0 ${statusDot}`} />
            <span className="text-xs text-muted-foreground truncate max-w-[220px]">{statusText}</span>
          </div>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="sm" onClick={handleReset} className="h-7 px-2 text-muted-foreground">
                <RotateCcw className="w-3 h-3" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Reset conversation</TooltipContent>
          </Tooltip>
        </div>
        <Separator />

        {/* ── Messages ─────────────────────────────────────────────────── */}
        <ScrollArea className="flex-1 px-4 py-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center pt-16 space-y-4">
              <div className="w-16 h-16 rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center">
                <Radio className="w-7 h-7 text-primary" />
              </div>
              <div>
                <p className="text-foreground font-semibold text-lg">Hi, I'm ARIA</p>
                <p className="text-muted-foreground text-sm mt-1 max-w-xs">
                  Your EMS administrative assistant. Ask me about your schedule, compliance, or start a form.
                </p>
              </div>
              {noSpeechApi && (
                <p className="text-xs text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg px-3 py-2 max-w-xs">
                  Voice input requires Chrome or Edge. Text input works on all browsers.
                </p>
              )}
              <div className="flex flex-wrap gap-2 justify-center pt-2">
                {SUGGESTIONS.map(s => (
                  <Button key={s} variant="outline" size="sm" onClick={() => dispatchMessage(s)}
                    className="text-xs rounded-full h-7 px-3">
                    {s}
                  </Button>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-4">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'assistant' && (
                  <div className="w-7 h-7 rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center mr-2 mt-0.5 shrink-0">
                    <Radio className="w-3.5 h-3.5 text-primary" />
                  </div>
                )}
                <div className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-primary text-primary-foreground rounded-br-sm'
                    : 'bg-secondary text-foreground border border-border rounded-bl-sm'
                }`}>
                  {msg.content}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="w-7 h-7 rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center mr-2 shrink-0">
                  <Radio className="w-3.5 h-3.5 text-primary" />
                </div>
                <div className="bg-secondary border border-border rounded-2xl rounded-bl-sm px-4 py-3">
                  <Loader2 className="w-4 h-4 text-muted-foreground animate-spin" />
                </div>
              </div>
            )}
          </div>
          <div ref={bottomRef} />
        </ScrollArea>

        {/* ── Input bar ────────────────────────────────────────────────── */}
        <Separator />
        <div className="px-4 py-3 bg-card space-y-2">

          {/* Live transcript */}
          {isRecording && (
            <div className="flex items-center gap-2 px-1">
              <span className="w-1.5 h-1.5 rounded-full bg-destructive animate-pulse shrink-0" />
              <p className="text-xs text-muted-foreground italic truncate">
                {liveTranscript || 'Listening…'}
              </p>
            </div>
          )}

          {/* Interruption hint */}
          {isSpeaking && !isRecording && (
            <p className="text-xs text-muted-foreground/70 italic px-1">
              Tap the mic to interrupt ARIA
            </p>
          )}

          <div className="flex gap-2">
            <Input
              ref={inputRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
              placeholder={isRecording ? 'Listening…' : 'Type a message or use the mic…'}
              disabled={isLoading || isRecording}
              className="flex-1"
            />

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  onClick={handleSend}
                  disabled={!input.trim() || isLoading || isRecording}
                  size="icon"
                >
                  <Send className="w-4 h-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Send</TooltipContent>
            </Tooltip>

            {/* Mic — always clickable to interrupt ARIA */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant={isRecording ? 'destructive' : isSpeaking ? 'secondary' : 'outline'}
                  size="icon"
                  onClick={toggleMic}
                  disabled={noSpeechApi}
                  className={isRecording ? 'animate-pulse ring-2 ring-destructive/60' : ''}
                >
                  {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {noSpeechApi
                  ? 'Voice requires Chrome/Edge'
                  : isRecording
                    ? 'Stop recording'
                    : isSpeaking
                      ? 'Interrupt ARIA'
                      : 'Start voice input'}
              </TooltipContent>
            </Tooltip>
          </div>
        </div>
      </div>
    </TooltipProvider>
  )
}
