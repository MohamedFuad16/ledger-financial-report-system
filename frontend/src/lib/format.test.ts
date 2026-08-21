import { describe, expect, it } from 'vitest'
import { groupParserStats, matchedParserCohort, parserMetricLeaders } from './format'
import type { RunSummary } from '../types'

const run = (strategy: string, file: string, accuracy: number, seconds = 1): RunSummary => ({
  run_id: `${strategy}-${file}-${accuracy}`,
  strategy,
  pdf_file: file,
  fiscal_year: file.match(/\d{4}/)?.[0] || '2022',
  accuracy,
  coverage: accuracy,
  extract_seconds: seconds,
})

describe('matched historical parser cohort', () => {
  it('excludes a report until every represented parser completed it', () => {
    const runs = [
      run('s1', '3M_annual_report_2022.pdf', 80),
      run('s2', '3M_annual_report_2022.pdf', 90),
      run('s1', '3M_annual_report_2023.pdf', 100),
    ]
    expect(matchedParserCohort(runs)).toHaveLength(2)
    const stats = groupParserStats(runs).filter((entry) => entry.runs)
    expect(stats.map((entry) => [entry.key, entry.accuracy])).toEqual([
      ['s1', 80],
      ['s2', 90],
    ])
  })

  it('weights reports equally when one parser was rerun', () => {
    const runs = [
      run('s1', '3M_annual_report_2022.pdf', 60),
      run('s1', '3M_annual_report_2022.pdf', 100),
      run('s2', '3M_annual_report_2022.pdf', 90),
      run('s1', '3M_annual_report_2023.pdf', 40),
      run('s2', '3M_annual_report_2023.pdf', 70),
    ]
    const stats = groupParserStats(runs)
    expect(stats.find((entry) => entry.key === 's1')?.accuracy).toBe(60)
    expect(stats.find((entry) => entry.key === 's2')?.accuracy).toBe(80)
  })

  it('reports every parser tied at the displayed one-decimal precision', () => {
    const stats = groupParserStats([
      run('s1', '3M_annual_report_2022.pdf', 40.76),
      run('s2-inspector', '3M_annual_report_2022.pdf', 40.84),
    ]).filter((entry) => entry.runs)
    expect(parserMetricLeaders(stats, 'accuracy').map((entry) => entry.key)).toEqual(['s1', 's2-inspector'])
  })
})
