import { describe, expect, it } from 'vitest'
import { localizeSchemaText } from './i18n'

describe('localizeSchemaText', () => {
  it('translates extracted schema values in Japanese mode', () => {
    expect(localizeSchemaText('Current Assets', 'ja')).toBe('流動資産')
    expect(localizeSchemaText('Cash & Cash Equivalents', 'ja')).toBe('現金及び現金同等物')
  })

  it('preserves the output contract in English mode and unknown text in Japanese mode', () => {
    expect(localizeSchemaText('Current Assets', 'en')).toBe('Current Assets')
    expect(localizeSchemaText('Unmapped source label', 'ja')).toBe('Unmapped source label')
  })

  it('normalizes stored Japanese schema labels when English is selected', () => {
    expect(localizeSchemaText('流動資産', 'en')).toBe('Current Assets')
    expect(localizeSchemaText('現金及び現金同等物', 'en')).toBe('Cash & Cash Equivalents')
  })
})
