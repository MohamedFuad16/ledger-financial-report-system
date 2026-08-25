// Canonical English display names for corpus companies.
// Mirrors corpus/company_names.py — regenerate from it when companies change.
export const englishCompanyNames: Record<string, string> = {
  'AppBank株式会社': 'AppBank Inc.',
  'Byside株式会社': 'Byside Inc.',
  'JR九州エンジニアリング株式会社': 'JR Kyushu Engineering Co., Ltd.',
  'JUKI産機テクノロジー株式会社': 'JUKI Industrial Equipment Technology Corp.',
  'note株式会社': 'note inc.',
  'キャディ株式会社': 'CADDi Inc.',
  'クラスター株式会社': 'Cluster, Inc.',
  'ハコベル株式会社': 'Hacobell Inc.',
  'ファインディ株式会社': 'Findy Inc.',
  'メディフォン株式会社': 'MediPhone, Inc.',
  'ラクスル株式会社': 'Raksul Inc.',
  'リソルホールディングス株式会社': 'RESOL Holdings Co., Ltd.',
  '吉田海運株式会社': 'Yoshida Kaiun Co., Ltd.',
  '大西運輸株式会社': 'Onishi Transport Co., Ltd.',
  '日本テーマパーク開発株式会社': 'Japan Theme Park Development, Inc.',
  '株式会社FLUX': 'FLUX Inc.',
  '株式会社Morght': 'Morght Inc.',
  '株式会社PIGNUS（ピグナス）': 'PIGNUS Inc.',
  '株式会社SANU': 'SANU Inc.',
  '株式会社iCARE': 'iCARE Co., Ltd.',
  '株式会社mov': 'mov inc.',
  '株式会社with': 'with Inc.',
  '株式会社アップガレージグループ': 'UP GARAGE GROUP Co., Ltd.',
  '株式会社キズキ': 'Kizuki Co., Ltd.',
  '株式会社キッズコーポレーション': 'Kids Corporation Inc.',
  '株式会社グッドパッチ': 'Goodpatch Inc.',
  '株式会社トーエネック': 'TOENEC Corporation',
  '株式会社ナレッジワーク': 'Knowledge Work Inc.',
  '株式会社ハッピートラベル': 'Happy Travel Co., Ltd.',
  '株式会社ベルク': 'Belc CO., LTD.',
  '株式会社レスタス': 'Lestas Inc.',
  '株式会社伊豆シャボテン公園': 'Izu Shaboten Resort Co., Ltd.',
  '株式会社帝国ホテル': 'Imperial Hotel, Ltd.',
  '西尾レントオール株式会社': 'Nishio Rent All Co., Ltd.',
}

export function companyDisplayName(company: string, locale: 'en' | 'ja'): string {
  if (locale === 'ja') return company
  return englishCompanyNames[company] || company
}
// Curated official domains for the corpus-page logo showcase. Only companies
// with a real, working brand site belong here; everyone else gets a monogram.
export const showcaseDomains: Record<string, string> = {
  '3M': '3m.com',
  'AppBank株式会社': 'appbank.co.jp',
  'note株式会社': 'note.jp',
  'ラクスル株式会社': 'corp.raksul.com',
  'キャディ株式会社': 'caddi.com',
  '株式会社グッドパッチ': 'goodpatch.com',
  '株式会社帝国ホテル': 'imperialhotel.co.jp',
  '株式会社ベルク': 'belc.jp',
  'ファインディ株式会社': 'findy.co.jp',
  '西尾レントオール株式会社': 'nishio-rent.co.jp',
  'リソルホールディングス株式会社': 'resol.jp',
  'クラスター株式会社': 'cluster.mu',
}
