import { useEffect } from 'react'
import useStore from '@/store/useStore'
import LoginScreen from '@/components/LoginScreen'
import LeftPanel from '@/components/LeftPanel'
import ChatPanel from '@/components/ChatPanel'
import RightPanel from '@/components/RightPanel'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import { ModeToggle } from '@/components/ModeToggle'
import { logout as apiLogout } from '@/api/client'
import { LogOut, Radio } from 'lucide-react'

function AppShell() {
  const paramedic = useStore(s => s.paramedic)
  const sessionId = useStore(s => s.sessionId)
  const doLogout  = useStore(s => s.logout)

  const handleLogout = async () => {
    await apiLogout(sessionId).catch(() => {})
    doLogout()
  }

  return (
    <div className="flex flex-col h-screen bg-background overflow-hidden">
      {/* Navbar */}
      <header className="flex items-center justify-between px-5 py-3 bg-card shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center">
            <Radio className="w-3.5 h-3.5 text-primary" />
          </div>
          <span className="font-bold tracking-wide text-sm text-foreground">ARIA</span>
          <span className="text-muted-foreground text-xs hidden sm:block">· EMS Administrative Assistant</span>
        </div>
        <div className="flex items-center gap-3">
          {paramedic && (
            <span className="text-xs text-muted-foreground hidden sm:block">
              {paramedic.first_name} {paramedic.last_name}
              <span className="text-muted-foreground/50 ml-1">· {paramedic.station}</span>
            </span>
          )}
          <ModeToggle />
          <Button variant="ghost" size="sm" onClick={handleLogout} className="text-muted-foreground hover:text-destructive h-7 px-2 gap-1.5">
            <LogOut className="w-3.5 h-3.5" />
            <span className="text-xs hidden sm:block">Sign out</span>
          </Button>
        </div>
      </header>
      <Separator />

      {/* 3-panel layout */}
      <div className="flex flex-1 overflow-hidden">
        <aside className="w-56 shrink-0 overflow-hidden hidden md:flex flex-col">
          <LeftPanel />
        </aside>
        <main className="flex-1 overflow-hidden flex flex-col min-w-0">
          <ChatPanel />
        </main>
        <aside className="w-64 shrink-0 overflow-hidden hidden lg:flex flex-col">
          <RightPanel />
        </aside>
      </div>
    </div>
  )
}

export default function App() {
  const sessionId = useStore(s => s.sessionId)
  return sessionId ? <AppShell /> : <LoginScreen />
}
