import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { FileText, Heart, RefreshCw, LayoutList } from 'lucide-react'
import useStore from '@/store/useStore'

const FORM_META = {
  occurrence_report: {
    icon: FileText,
    label: 'Occurrence Report',
    badgeClass: 'text-orange-400 border-orange-500/30 bg-orange-500/10',
    fields: {
      occurrence_type:   'Type',
      brief_description: 'Description',
      vehicle_number:    'Unit #',
      requested_by:      'Requested By',
      date:              'Date',
      time:              'Time',
      report_creator:    'Reporter',
      call_number:       'Call #',
      action_taken:      'Action Taken',
      target_email:      'Send To',
    },
  },
  teddy_bear: {
    icon: Heart,
    label: 'Teddy Bear Program',
    badgeClass: 'text-pink-400 border-pink-500/30 bg-pink-500/10',
    fields: {
      recipient_age:      'Age',
      recipient_gender:   'Gender',
      recipient_type:     'Recipient Type',
      primary_medic_first:'Medic First',
      primary_medic_last: 'Medic Last',
      target_email:       'Send To',
    },
  },
  shift_change: {
    icon: RefreshCw,
    label: 'Shift Change Request',
    badgeClass: 'text-blue-400 border-blue-500/30 bg-blue-500/10',
    fields: {
      shift_date:       'Date',
      shift_start:      'Start',
      shift_end:        'End',
      requested_action: 'Action',
      notes:            'Notes',
    },
  },
}

export default function RightPanel() {
  const activeForm          = useStore(s => s.activeForm)
  const formData            = useStore(s => s.formData)
  const confirmationPending = useStore(s => s.confirmationPending)
  const submitted           = useStore(s => s.submitted)

  if (!activeForm || !FORM_META[activeForm]) {
    return (
      <div className="flex flex-col h-full bg-card border-l border-border items-center justify-center">
        <div className="text-center px-6 space-y-3">
          <div className="w-12 h-12 rounded-full bg-secondary flex items-center justify-center mx-auto">
            <LayoutList className="w-5 h-5 text-muted-foreground" />
          </div>
          <p className="text-muted-foreground text-sm">No active form</p>
          <p className="text-muted-foreground/50 text-xs">Start a conversation to fill a form</p>
        </div>
      </div>
    )
  }

  const meta = FORM_META[activeForm]
  const Icon = meta.icon

  return (
    <div className="flex flex-col h-full bg-card border-l border-border">

      {/* Header */}
      <div className="px-4 py-4">
        <div className="flex items-center gap-2 mb-3">
          <Icon className="w-4 h-4 text-muted-foreground" />
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
            {meta.label}
          </p>
        </div>
        {submitted ? (
          <Badge variant="outline" className="text-green-400 border-green-500/30 bg-green-500/10">
            ✓ Submitted
          </Badge>
        ) : confirmationPending ? (
          <Badge variant="outline" className="text-yellow-400 border-yellow-500/30 bg-yellow-500/10 animate-pulse">
            Awaiting confirmation
          </Badge>
        ) : (
          <Badge variant="outline" className={meta.badgeClass}>
            Collecting info…
          </Badge>
        )}
      </div>
      <Separator />

      {/* Fields */}
      <ScrollArea className="flex-1 px-3 py-3">
        <div className="space-y-2">
          {Object.entries(meta.fields).map(([key, label]) => {
            const value = formData[key]
            const filled = value && String(value).trim() !== ''
            return (
              <Card
                key={key}
                className={`px-3 py-2.5 rounded-lg border transition-colors ${
                  filled ? 'border-border bg-secondary/60' : 'border-border/30 bg-card'
                }`}
              >
                <p className="text-xs text-muted-foreground uppercase tracking-wider mb-0.5">{label}</p>
                <p className={`text-sm font-medium ${filled ? 'text-foreground' : 'text-muted-foreground/30'}`}>
                  {filled ? String(value) : '—'}
                </p>
              </Card>
            )
          })}
        </div>
      </ScrollArea>
    </div>
  )
}
