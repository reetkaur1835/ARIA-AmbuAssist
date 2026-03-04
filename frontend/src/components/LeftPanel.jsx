import { useEffect } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Card } from '@/components/ui/card'
import { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { getStatus, getShifts } from '@/api/client'
import useStore from '@/store/useStore'
import { CheckCircle2, XCircle, Calendar, Clock3, MapPin } from 'lucide-react'

export default function LeftPanel() {
  const sessionId    = useStore(s => s.sessionId)
  const statusItems  = useStore(s => s.statusItems)
  const shifts       = useStore(s => s.shifts)
  const setStatusItems = useStore(s => s.setStatusItems)
  const setShifts    = useStore(s => s.setShifts)

  useEffect(() => {
    if (!sessionId) return
    getStatus(sessionId).then(r => setStatusItems(r.data.status_items)).catch(() => {})
    getShifts(sessionId).then(r => setShifts(r.data.shifts)).catch(() => {})
  }, [sessionId])

  const badItems  = statusItems.filter(i => i.status === 'BAD')
  const goodItems = statusItems.filter(i => i.status === 'GOOD')

  return (
    <TooltipProvider>
      <div className="flex flex-col h-full bg-card border-r border-border">

        {/* Header */}
        <div className="px-4 py-4">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3">
            Compliance
          </p>
          <div className="flex gap-2">
            <Badge variant="outline" className="text-destructive border-destructive/40 bg-destructive/10 text-xs">
              {badItems.length} outstanding
            </Badge>
            <Badge variant="outline" className="text-green-400 border-green-500/30 bg-green-500/10 text-xs">
              {goodItems.length} cleared
            </Badge>
          </div>
        </div>
        <Separator />

        <ScrollArea className="flex-1 px-3 py-2">

          {/* Outstanding items */}
          {badItems.length > 0 && (
            <div className="space-y-1 mb-3">
              {badItems.map(item => (
                <Tooltip key={item.item_code}>
                  <TooltipTrigger asChild>
                    <Card className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg border-destructive/20 bg-destructive/5 cursor-default">
                      <XCircle className="w-4 h-4 text-destructive shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground truncate">{item.item_type}</p>
                        {item.issue_count > 0 && (
                          <p className="text-xs text-destructive">{item.issue_count} outstanding</p>
                        )}
                      </div>
                    </Card>
                  </TooltipTrigger>
                  <TooltipContent side="right">{item.item_type} — action required</TooltipContent>
                </Tooltip>
              ))}
            </div>
          )}

          {/* Cleared items */}
          {goodItems.length > 0 && (
            <div className="space-y-1 mb-3">
              {goodItems.map(item => (
                <Card key={item.item_code} className="flex items-center gap-2.5 px-3 py-2 rounded-lg border-border bg-card cursor-default">
                  <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0" />
                  <p className="text-sm text-muted-foreground truncate flex-1">{item.item_type}</p>
                </Card>
              ))}
            </div>
          )}

          {statusItems.length === 0 && (
            <p className="text-xs text-muted-foreground text-center py-6">Loading status…</p>
          )}

          <Separator className="my-3" />

          {/* Upcoming Shifts */}
          <div className="flex items-center gap-1.5 mb-2">
            <Calendar className="w-3.5 h-3.5 text-muted-foreground" />
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
              Upcoming Shifts
            </p>
          </div>

          {shifts.length === 0 && (
            <p className="text-xs text-muted-foreground text-center py-3">No upcoming shifts</p>
          )}

          <div className="space-y-1.5">
            {shifts.map((shift, i) => (
              <Card key={i} className="px-3 py-2.5 rounded-lg border-border">
                <p className="text-sm font-semibold text-foreground">{shift.date}</p>
                <div className="flex items-center gap-1 mt-1">
                  <Clock3 className="w-3 h-3 text-muted-foreground" />
                  <p className="text-xs text-muted-foreground">{shift.start_time} – {shift.end_time}</p>
                </div>
                {shift.station && (
                  <div className="flex items-center gap-1 mt-0.5">
                    <MapPin className="w-3 h-3 text-muted-foreground" />
                    <p className="text-xs text-muted-foreground">{shift.station}</p>
                  </div>
                )}
              </Card>
            ))}
          </div>

        </ScrollArea>
      </div>
    </TooltipProvider>
  )
}
