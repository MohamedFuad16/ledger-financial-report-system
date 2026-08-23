import { motion } from 'framer-motion'

/*
 * Adapted for the Ledger upload control from Rare UI's open-source Folder
 * component by Swami Malode:
 * https://github.com/swamimalode07/rare-ui/tree/main/components/ui
 */

const BASE_WIDTH = 321
const BASE_HEIGHT = 270

// One folder color per strategy page: 1 blue, 2 red, 3 violet.
export type FolderTone = 'blue' | 'red' | 'violet'
const TONES: Record<FolderTone, { back: string; flap: string; stroke: string; shadow: string }> = {
  blue: { back: '#50b1fd', flap: '#3a9ae8', stroke: '#7ec8ff', shadow: 'rgba(37, 99, 235, .18)' },
  red: { back: '#fb7185', flap: '#e8536e', stroke: '#ffb3c0', shadow: 'rgba(225, 29, 72, .18)' },
  violet: { back: '#a78bfa', flap: '#8b5cf6', stroke: '#d4c2ff', shadow: 'rgba(124, 58, 237, .18)' },
}
const FLAP_PATH = 'M0 25C0 11.1929 11.1929 0 25 0H136.084C143.044 0 149.689 2.90139 154.42 8.00608L178.08 33.5343C182.811 38.639 189.456 41.5404 196.416 41.5404H296C309.807 41.5404 321 52.7333 321 66.5404V216C321 229.807 309.807 241 296 241H25C11.1929 241 0 229.807 0 216V25Z'

function DocumentCard({ id }: { id: number }) {
  return (
    <svg className="rare-folder-document" width="164" height="214" viewBox="0 0 164 214" fill="none" aria-hidden="true">
      <g filter={`url(#rare-card-shadow-${id})`}>
        <rect width="163.078" height="213.262" rx="20" fill="#fff" />
      </g>
      <rect x=".5" y=".5" width="162.078" height="212.262" rx="19.5" stroke="#dfe5ec" />
      <rect x="14.12" y="31.21" width="134.84" height="11.89" rx="5.94" fill="#bfdbfe" />
      {Array.from({ length: 9 }, (_, row) => (
        <g key={row}>
          <rect x="14.83" y={60.99 + row * 14.12} width="64.52" height="5.88" rx="2.94" fill="#d9dee6" />
          <rect x="84.43" y={60.99 + row * 14.12} width="64.52" height="5.88" rx="2.94" fill="#d9dee6" />
        </g>
      ))}
      <defs>
        <filter id={`rare-card-shadow-${id}`} x="0" y="0" width="167" height="219" filterUnits="userSpaceOnUse">
          <feDropShadow dx="3" dy="5" stdDeviation="3" floodOpacity=".15" />
        </filter>
      </defs>
    </svg>
  )
}

export function FolderUpload({ active = false, open = false, tone = 'blue' }: { active?: boolean; open?: boolean; tone?: FolderTone }) {
  const expanded = open || active
  const colors = TONES[tone]
  const cards = [
    { id: 1, x: open ? 70 : 40, y: open ? -160 : active ? -30 : -10, rotate: open ? 18 : active ? 14 : 10, delay: .1 },
    { id: 2, x: open ? 0 : 3, y: open ? -180 : active ? -35 : -20, rotate: open ? -3 : active ? -1 : 2, delay: .05 },
    { id: 3, x: open ? -65 : -40, y: open ? -170 : active ? -44 : -22, rotate: open ? -14 : active ? -9 : -5, delay: 0 },
  ]

  return (
    <div className="rare-folder" aria-hidden="true">
      <div className="rare-folder-stage" style={{ width: BASE_WIDTH, height: BASE_HEIGHT }}>
        <div className="rare-folder-back" style={{ background: colors.back, boxShadow: `inset 0 0 6px 2px rgba(255, 255, 255, .35), 0 16px 36px ${colors.shadow}` }} />
        <div className="rare-folder-documents">
          {cards.map((card) => (
            <motion.div
              className="rare-folder-card"
              key={card.id}
              animate={{ x: card.x, y: card.y, rotate: card.rotate }}
              transition={{ type: 'spring', stiffness: 120, damping: 13, delay: expanded ? card.delay : 0 }}
            >
              <DocumentCard id={card.id} />
            </motion.div>
          ))}
        </div>
        <motion.div
          className="rare-folder-flap"
          animate={{ rotateX: open ? -55 : active ? -45 : -15 }}
          transition={{ type: 'spring', stiffness: 120, damping: 14 }}
        >
          <svg width="321" height="241" viewBox="0 0 321 241" fill="none">
            <path d={FLAP_PATH} fill={colors.flap} fillOpacity=".46" stroke={colors.stroke} />
          </svg>
        </motion.div>
      </div>
    </div>
  )
}
