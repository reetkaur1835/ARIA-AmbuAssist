import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { ModeToggle } from '@/components/ModeToggle'
import { login } from '@/api/client'
import useStore from '@/store/useStore'
import { Radio, KeyRound, User } from 'lucide-react'

export default function LoginScreen() {
  const [username, setUsername] = useState('')
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const doLogin = useStore(s => s.login)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await login(username, pin)
      doLogin(res.data.session_id, res.data.paramedic)
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      {/* Theme toggle — top right corner */}
      <div className="fixed top-4 right-4">
        <ModeToggle />
      </div>

      <div className="w-full max-w-sm space-y-6">

        {/* Branding */}
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 border border-primary/30 mx-auto">
            <Radio className="w-7 h-7 text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground tracking-wide">ARIA</h1>
            <p className="text-muted-foreground text-sm mt-1">Ambulance Response Intelligence Assistant</p>
          </div>
        </div>

        {/* Login Card */}
        <Card className="border-border">
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-foreground">Paramedic Sign In</CardTitle>
          </CardHeader>
          <Separator />
          <CardContent className="pt-5">
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Badge / Username
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                    placeholder="e.g. Team02"
                    className="pl-9"
                    required
                    autoFocus
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  PIN
                </label>
                <div className="relative">
                  <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    type="password"
                    value={pin}
                    onChange={e => setPin(e.target.value)}
                    placeholder="••••"
                    className="pl-9"
                    required
                  />
                </div>
              </div>

              {error && (
                <div className="text-destructive text-sm bg-destructive/10 border border-destructive/30 rounded-md px-3 py-2">
                  {error}
                </div>
              )}

              <Button type="submit" disabled={loading} className="w-full mt-1">
                {loading ? 'Signing in...' : 'Sign In'}
              </Button>
            </form>
          </CardContent>
        </Card>

        <p className="text-center text-muted-foreground text-xs">
          ARIA v1.0 · EMS Administrative Assistant
        </p>
      </div>
    </div>
  )
}
