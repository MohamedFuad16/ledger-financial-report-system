import { describe, expect, it } from 'vitest'
import { experimentForStrategyPage, extractionJobBelongsToStrategyPage, groupExperimentStats, groupParserStats, matchedParserCohort, parserMetricLeaders } from './format'
import type { RunSummary } from '../types'

const run = (strategy: string, file: string, accuracy: number, seconds = 1, experiment: 'no_ocr' | 'ocr' = 'no_ocr', identity: Partial<RunSummary> = {}): RunSummary => ({
  run_id: `${strategy}-${file}-${accuracy}`,
  strategy,
  experiment,
  pdf_file: file,
  fiscal_year: file.match(/\d{4}/)?.[0] || '2022',
  accuracy,
  coverage: accuracy,
  extract_seconds: seconds,
  company: '3M',
  ...identity,
})

describe('strategy page identity', () => {
  it('keeps numbering, experiment arms, and durable job scopes aligned', () => {
    expect(experimentForStrategyPage('s1')).toBe('no_ocr')
    expect(experimentForStrategyPage('s2')).toBe('ocr')
    expect(experimentForStrategyPage('s3')).toBe('intelligent_scan')
    expect(extractionJobBelongsToStrategyPage('s1', 's1')).toBe(true)
    expect(extractionJobBelongsToStrategyPage('s2', 's1')).toBe(false)
  })
})

describe('matched historical parser cohort', () => {
  it('reduces the dashboard comparison to one no-OCR mean and one OCR mean', () => {
    const runs = [
      { ...run('s1', '3M_annual_report_2022.pdf', 80, 10), total_seconds: 100 },
      { ...run('s1', '3M_annual_report_2022.pdf', 100, 10), total_seconds: 200 },
      { ...run('s1-pymupdf', '3M_annual_report_2022.pdf', 100, 10), total_seconds: 50 },
      { ...run('s2-pypdf', '3M_annual_report_2022.pdf', 90, 10, 'ocr'), total_seconds: 90 },
      { ...run('s2', '3M_annual_report_2022.pdf', 100, 10, 'ocr'), total_seconds: 110 },
    ]
    const stats = groupExperimentStats(runs)
    expect(stats).toHaveLength(2)
    expect(stats[0]).toMatchObject({ key: 'no_ocr', passes: 2, totalSeconds: 100, accuracy: 95 })
    expect(stats[1]).toMatchObject({ key: 'ocr', passes: 2, totalSeconds: 100, accuracy: 95 })
  })

  it('excludes a report until every represented parser completed it', () => {
    const runs = [
      run('s1', '3M_annual_report_2022.pdf', 80),
      run('s1-pymupdf', '3M_annual_report_2022.pdf', 90),
      run('s1-inspector', '3M_annual_report_2022.pdf', 70),
      run('s1-docling', '3M_annual_report_2022.pdf', 60),
      run('s1', '3M_annual_report_2023.pdf', 100),
    ]
    expect(matchedParserCohort(runs)).toHaveLength(4)
    const stats = groupParserStats(runs).filter((entry) => entry.runs)
    expect(stats.map((entry) => [entry.key, entry.accuracy])).toEqual([
      ['s1', 80],
      ['s1-pymupdf', 90],
      ['s1-inspector', 70],
      ['s1-docling', 60],
    ])
  })

  it('weights reports equally when one parser was rerun', () => {
    const runs = [
      run('s1', '3M_annual_report_2022.pdf', 60),
      run('s1', '3M_annual_report_2022.pdf', 100),
      run('s1-pymupdf', '3M_annual_report_2022.pdf', 90),
      run('s1-inspector', '3M_annual_report_2022.pdf', 80),
      run('s1-docling', '3M_annual_report_2022.pdf', 70),
      run('s1', '3M_annual_report_2023.pdf', 40),
      run('s1-pymupdf', '3M_annual_report_2023.pdf', 70),
      run('s1-inspector', '3M_annual_report_2023.pdf', 60),
      run('s1-docling', '3M_annual_report_2023.pdf', 50),
    ]
    const stats = groupParserStats(runs)
    expect(stats.find((entry) => entry.key === 's1')?.accuracy).toBe(60)
    expect(stats.find((entry) => entry.key === 's1-pymupdf')?.accuracy).toBe(80)
  })

  it('reports every parser tied at the displayed one-decimal precision', () => {
    const stats = groupParserStats([
      run('s1', '3M_annual_report_2022.pdf', 40.76),
      run('s1-pymupdf', '3M_annual_report_2022.pdf', 40.1),
      run('s1-inspector', '3M_annual_report_2022.pdf', 40.84),
      run('s1-docling', '3M_annual_report_2022.pdf', 39.9),
    ]).filter((entry) => entry.runs)
    expect(parserMetricLeaders(stats, 'accuracy').map((entry) => entry.key)).toEqual(['s1', 's1-inspector'])
  })

  it('never mixes no-OCR and OCR observations', () => {
    const runs = [
      run('s1', '3M_annual_report_2022.pdf', 10),
      run('s1-pymupdf', '3M_annual_report_2022.pdf', 20),
      run('s1-inspector', '3M_annual_report_2022.pdf', 30),
      run('s1-docling', '3M_annual_report_2022.pdf', 40),
      run('s2-pypdf', '3M_annual_report_2022.pdf', 50, 1, 'ocr'),
      run('s2', '3M_annual_report_2022.pdf', 60, 1, 'ocr'),
      run('s2-inspector', '3M_annual_report_2022.pdf', 70, 1, 'ocr'),
      run('s2-docling', '3M_annual_report_2022.pdf', 80, 1, 'ocr'),
    ]
    expect(groupParserStats(runs, 'no_ocr').find((entry) => entry.key === 's1')?.accuracy).toBe(10)
    expect(groupParserStats(runs, 'ocr').find((entry) => entry.key === 's2-pypdf')?.accuracy).toBe(50)
  })

  it('never matches different companies or different source hashes as one report', () => {
    const runs = [
      run('s1', 'annual_report_2022.pdf', 80, 1, 'no_ocr', { company: '3M', source_pdf_sha256: 'aaa' }),
      run('s1-pymupdf', 'annual_report_2022.pdf', 90, 1, 'no_ocr', { company: '3M', source_pdf_sha256: 'aaa' }),
      run('s1-inspector', 'annual_report_2022.pdf', 70, 1, 'no_ocr', { company: 'Other Co', source_pdf_sha256: 'aaa' }),
      run('s1-docling', 'annual_report_2022.pdf', 60, 1, 'no_ocr', { company: '3M', source_pdf_sha256: 'bbb' }),
    ]
    expect(matchedParserCohort(runs)).toEqual([])
  })
})
